"""Tally-style, read-only ledger statement backed by ERPNext GL Entries."""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from erpnext.accounts.report.general_ledger import general_ledger


def _require_access(company):
	frappe.has_permission("Company", "read", company, throw=True)
	frappe.has_permission("GL Entry", "report", throw=True)
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Select a valid company."))


def _dates(from_date, to_date):
	try:
		from_date, to_date = getdate(from_date), getdate(to_date)
	except Exception:
		frappe.throw(_("Enter valid from and to dates."))
	if from_date > to_date:
		frappe.throw(_("From date must be before to date."))
	return str(from_date), str(to_date)


def _balance(amount):
	return {"amount": abs(float(amount)), "side": "Dr" if amount >= 0 else "Cr"}


@frappe.whitelist()
def get_page_context():
	company = frappe.defaults.get_user_default("Company")
	if not company:
		companies = frappe.get_list("Company", fields=["name"], limit_page_length=2)
		company = companies[0].name if len(companies) == 1 else ""
	if company:
		_require_access(company)

	today = getdate(nowdate())
	fiscal_year = frappe.db.get_value(
		"Fiscal Year",
		{"year_start_date": ["<=", today], "year_end_date": [">=", today], "disabled": 0},
		["year_start_date", "year_end_date"],
		as_dict=True,
	)
	return {
		"company": company,
		"from_date": str(fiscal_year.year_start_date) if fiscal_year else str(today),
		"to_date": str(fiscal_year.year_end_date) if fiscal_year else str(today),
		"actions": {
			"Payment Entry": frappe.has_permission("Payment Entry", "create"),
			"Journal Entry": frappe.has_permission("Journal Entry", "create"),
			"Sales Invoice": frappe.has_permission("Sales Invoice", "create"),
			"Purchase Invoice": frappe.has_permission("Purchase Invoice", "create"),
		},
	}


@frappe.whitelist()
def search_ledgers(company, text=""):
	_require_access(company)
	text = (text or "").strip()
	like = f"%{text}%"
	results = []

	if frappe.has_permission("Account", "read"):
		accounts = frappe.get_list(
			"Account",
			filters={"company": company, "disabled": 0, "is_group": 0},
			or_filters=[["name", "like", like], ["account_name", "like", like]],
			fields=["name", "account_name", "account_type", "root_type"],
			order_by="account_name asc, name asc", limit_page_length=10000,
		)
		for account in accounts:
			kind = account.account_type or account.root_type or "Account"
			results.append({"kind": "Account", "name": account.name, "label": account.account_name, "detail": kind, "is_group": False})

	if frappe.has_permission("Customer", "read"):
		customers = frappe.get_list(
			"Customer",
			filters={"disabled": 0},
			or_filters=[["name", "like", like], ["customer_name", "like", like]],
			fields=["name", "customer_name", "customer_group"],
			order_by="customer_name asc, name asc",
			limit_page_length=10000,
		)
		for customer in customers:
			results.append({
				"kind": "Customer",
				"name": customer.name,
				"label": customer.customer_name or customer.name,
				"detail": _("Debtor"),
				"is_group": False,
			})

	if frappe.has_permission("Supplier", "read"):
		suppliers = frappe.get_list(
			"Supplier",
			filters={"disabled": 0},
			or_filters=[["name", "like", like], ["supplier_name", "like", like]],
			fields=["name", "supplier_name", "supplier_group"],
			order_by="supplier_name asc, name asc",
			limit_page_length=10000,
		)
		for supplier in suppliers:
			results.append({
				"kind": "Supplier",
				"name": supplier.name,
				"label": supplier.supplier_name or supplier.name,
				"detail": _("Creditor"),
				"is_group": False,
			})

	return sorted(results, key=lambda row: (row["label"].casefold(), row["kind"], row["name"]))


@frappe.whitelist()
def get_statement(company, ledger_kind, ledger, from_date, to_date):
	_require_access(company)
	from_date, to_date = _dates(from_date, to_date)
	if ledger_kind not in ("Account", "Customer", "Supplier"):
		frappe.throw(_("Select a valid ledger."))
	frappe.has_permission(ledger_kind, "read", ledger, throw=True)
	if ledger_kind == "Account":
		if not frappe.db.exists("Account", {"name": ledger, "company": company, "disabled": 0, "is_group": 0}):
			frappe.throw(_("Select an active posting account in the selected company."))
	else:
		if not frappe.db.exists(ledger_kind, {"name": ledger, "disabled": 0}):
			frappe.throw(_("Select an active {0}.").format(_(ledger_kind)))

	# Use the standard report so filters, finance books, permissions,
	# opening balances, and voucher consolidation remain identical to General Ledger.
	filters = frappe._dict({
		"company": company,
		"from_date": from_date,
		"to_date": to_date,
		"categorize_by": "Categorize by Voucher (Consolidated)",
		"include_default_book_entries": 1,
	})
	if ledger_kind == "Account":
		filters.account = frappe.as_json([ledger])
	else:
		filters.party_type = ledger_kind
		filters.party = frappe.as_json([ledger])
	_report_columns, report_rows = general_ledger.execute(filters)
	opening_row = next((row for row in report_rows if row.get("account") == "'Opening'"), {})
	total_row = next((row for row in report_rows if row.get("account") == "'Total'"), {})
	closing_row = next((row for row in report_rows if str(row.get("account", "")).startswith("'Closing")), {})
	rows = []
	for row in report_rows:
		if not row.get("posting_date"):
			continue
		rows.append({
			"posting_date": str(row.posting_date),
			"particulars": row.get("against") or row.get("party_name") or row.get("party") or "",
			"voucher_type": row.get("voucher_type") or "",
			"voucher_no": row.get("voucher_no") or "",
			"debit": float(row.get("debit") or 0),
			"credit": float(row.get("credit") or 0),
		})

	company_currency = frappe.db.get_value("Company", company, "default_currency")
	return {
		"currency": company_currency,
		"opening": _balance(float(opening_row.get("debit") or 0) - float(opening_row.get("credit") or 0)),
		"total_debit": float(total_row.get("debit") or 0),
		"total_credit": float(total_row.get("credit") or 0),
		"closing": _balance(float(closing_row.get("debit") or 0) - float(closing_row.get("credit") or 0)),
		"rows": rows,
	}
