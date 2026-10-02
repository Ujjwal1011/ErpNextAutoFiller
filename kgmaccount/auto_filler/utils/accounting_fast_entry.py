"""Shared, guarded creation of standard accounting drafts for fast-entry pages."""

import secrets
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_outstanding_reference_documents
from erpnext.accounts.party import get_party_account


FLOWS = {
	"payment": {"create": "Payment Entry", "source_types": {"Cash", "Bank"}},
	"cash_expense": {"create": "Journal Entry", "source_types": {"Cash"}},
	"supplier_payment": {"create": "Payment Entry", "source_types": {"Cash", "Bank"}},
	"internal_transfer": {"create": "Payment Entry", "source_types": {"Cash", "Bank"}},
	"bank_receipt": {"create": "Payment Entry", "source_types": {"Bank"}},
}


def _money(value):
	try:
		amount = Decimal(str(value))
		if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
			raise ValueError
		return amount
	except (InvalidOperation, TypeError, ValueError):
		frappe.throw(_("Enter an amount greater than zero with at most two decimal places."))


def _flow(flow):
	if flow not in FLOWS:
		frappe.throw(_("Invalid fast-entry flow."), frappe.PermissionError)
	return FLOWS[flow]


def _company(company):
	frappe.has_permission("Company", "read", company, throw=True)
	details = frappe.db.get_value(
		"Company", company, ["default_currency", "default_cash_account", "cost_center"], as_dict=True
	)
	if not details:
		frappe.throw(_("Select a valid company."))
	if details.default_currency != "INR":
		frappe.throw(_("Fast entry currently supports INR companies only."))
	return details


def _account(name, company, currency):
	frappe.has_permission("Account", "read", name, throw=True)
	account = frappe.db.get_value(
		"Account", name,
		["company", "account_type", "account_currency", "root_type", "is_group", "disabled"], as_dict=True,
	)
	if not account or account.company != company or account.is_group or account.disabled:
		frappe.throw(_("Select an active posting account in the chosen company."))
	if account.account_currency != currency:
		frappe.throw(_("Both accounts must use the company currency ({0}).").format(currency))
	return account


def _default_bank(company):
	return frappe.db.get_value(
		"Account", {"company": company, "account_type": "Bank", "is_group": 0, "disabled": 0}, "name"
	)


def _require_create(flow):
	if flow in ("bank_receipt", "payment"):
		if not (frappe.has_permission("Payment Entry", "create") or frappe.has_permission("Journal Entry", "create")):
			frappe.throw(_("You need permission to create Payment Entries or Journal Entries."), frappe.PermissionError)
		return
	frappe.has_permission(_flow(flow)["create"], "create", throw=True)


def order_invoice_rows(rows, voucher_type, newest_first=True):
	"""Order already-permitted open invoices by posting date."""
	if not rows:
		return rows
	direction = "desc" if newest_first else "asc"
	invoices = frappe.db.get_all(
		voucher_type,
		filters={"name": ["in", list({row["invoice"] for row in rows})]},
		fields=["name", "posting_date", "creation"],
		order_by=f"posting_date {direction}, creation {direction}, name {direction}",
	)
	position = {invoice.name: index for index, invoice in enumerate(invoices)}
	return sorted(
		rows,
		key=lambda row: (
			position.get(row["invoice"], len(position)),
			row["due_date"],
			row["payment_term"],
		),
	)


def _open_references(company, account, party_type, party, voucher_type):
	frappe.has_permission("Payment Entry", "create", throw=True)
	frappe.has_permission(party_type, "read", party, throw=True)
	rows = get_outstanding_reference_documents(
		{
			"company": company,
			"party_type": party_type,
			"party": party,
			"party_account": account,
			"get_outstanding_invoices": True,
		},
		validate=True,
	)
	return order_invoice_rows([
		{
			"invoice": row.voucher_no,
			"payment_term": row.get("payment_term") or "",
			"due_date": str(row.get("due_date") or ""),
			"outstanding_amount": float(row.outstanding_amount),
		}
		for row in rows
		if row.voucher_type == voucher_type
		and Decimal(str(row.outstanding_amount)) > 0
		and frappe.has_permission(voucher_type, "read", row.voucher_no)
	], voucher_type)


def _references(company, account, party_type, party, voucher_type, allocations, amount):
	available = {
		(row["invoice"], row["payment_term"]): Decimal(str(row["outstanding_amount"]))
		for row in _open_references(company, account, party_type, party, voucher_type)
	}
	seen, total, references = set(), Decimal("0"), []
	for allocation in allocations:
		if not isinstance(allocation, dict):
			frappe.throw(_("Invalid invoice allocation."))
		key = (allocation.get("invoice"), allocation.get("payment_term") or "")
		if key in seen or key not in available:
			frappe.throw(_("Select an open invoice belonging to this party and account."))
		seen.add(key)
		allocated = _money(allocation.get("amount"))
		if allocated > available[key]:
			frappe.throw(_("An invoice allocation exceeds its outstanding amount."))
		total += allocated
		reference = {"reference_doctype": voucher_type, "reference_name": key[0], "allocated_amount": float(allocated)}
		if key[1]:
			reference["payment_term"] = key[1]
		references.append(reference)
	if total > amount:
		frappe.throw(_("Invoice allocations cannot exceed the payment amount."))
	return references


def _mode(account_type):
	name = "Cash" if account_type == "Cash" else "Bank"
	return name if frappe.db.exists("Mode of Payment", name) else None


@frappe.whitelist()
def get_page_context(flow):
	flow_data = _flow(flow)
	_require_create(flow)
	company = frappe.defaults.get_user_default("Company")
	if not company:
		companies = frappe.get_list("Company", fields=["name"], limit_page_length=2)
		company = companies[0].name if len(companies) == 1 else ""
	details = _company(company) if company else None
	default_source = ""
	if details:
		default_source = details.default_cash_account if "Cash" in flow_data["source_types"] else _default_bank(company) or ""
	return {"company": company, "source_account": default_source, "posting_date": nowdate()}


@frappe.whitelist()
def get_company_defaults(flow, company):
	flow_data = _flow(flow)
	_require_create(flow)
	details = _company(company)
	return {"source_account": details.default_cash_account if "Cash" in flow_data["source_types"] else _default_bank(company) or ""}


@frappe.whitelist()
def get_customer_receivable_account(company, customer):
	"""Resolve the customer's posting ledger for a direct customer payment."""
	details = _company(company)
	frappe.has_permission("Customer", "read", customer, throw=True)
	if not frappe.db.exists("Customer", {"name": customer, "disabled": 0}):
		frappe.throw(_("Select an active customer."))
	account = get_party_account("Customer", customer, company)
	if not account or _account(account, company, details.default_currency).account_type != "Receivable":
		frappe.throw(_("Set a valid receivable account for this customer or company."))
	return {"account": account, "account_type": "Receivable"}


@frappe.whitelist()
def get_counterpart_kind(flow, company, counterpart_account):
	_flow(flow)
	details = _company(company)
	account = _account(counterpart_account, company, details.default_currency)
	if flow == "cash_expense" and account.root_type != "Expense":
		frappe.throw(_("Choose an expense account."))
	if flow == "supplier_payment" and account.account_type != "Payable":
		frappe.throw(_("Choose a supplier payable account."))
	if flow == "internal_transfer" and account.account_type not in ("Cash", "Bank"):
		frappe.throw(_("Choose a cash or bank account."))
	if flow == "bank_receipt" and account.account_type != "Receivable" and account.root_type != "Income":
		frappe.throw(_("Choose a customer receivable or income account."))
	if flow == "payment" and account.account_type not in ("Payable", "Receivable", "Cash", "Bank") and account.root_type not in ("Expense", "Asset"):
		frappe.throw(_("Choose a supplier payable, customer receivable, expense, asset, cash, or bank account."))
	return {"account_type": account.account_type, "root_type": account.root_type}


@frappe.whitelist()
def get_open_invoices(flow, company, account, party):
	if flow == "bank_receipt":
		party_type, voucher_type, required_account = "Customer", "Sales Invoice", "Receivable"
	elif flow in ("supplier_payment", "payment"):
		party_type, voucher_type, required_account = "Supplier", "Purchase Invoice", "Payable"
	else:
		frappe.throw(_("This fast-entry flow has no invoice allocation."))
	details = _company(company)
	if _account(account, company, details.default_currency).account_type != required_account:
		frappe.throw(_("Select the correct party account."))
	return _open_references(company, account, party_type, party, voucher_type)


@frappe.whitelist()
def save_draft(
	flow, company, posting_date, source_account, counterpart_account, amount, narration=None, party=None, allocations=None,
	reference_no=None, reference_date=None, customer=None,
):
	flow_data = _flow(flow)
	_require_create(flow)
	details = _company(company)
	source = _account(source_account, company, details.default_currency)
	counterpart = _account(counterpart_account, company, details.default_currency)
	if source.account_type not in flow_data["source_types"]:
		frappe.throw(_("Choose an allowed cash or bank source account."))
	if source_account == counterpart_account:
		frappe.throw(_("Choose two different accounts."))
	if not posting_date:
		frappe.throw(_("Enter a posting date."))
	try:
		posting_date = str(getdate(posting_date))
	except Exception:
		frappe.throw(_("Enter a valid posting date."))
	amount = _money(amount)
	narration = (narration or "").strip()
	reference_no = (reference_no or "").strip()
	if reference_date:
		try:
			reference_date = str(getdate(reference_date))
		except Exception:
			frappe.throw(_("Enter a valid bank reference date."))
	if flow == "payment" and (source.account_type == "Bank" or counterpart.account_type == "Bank"):
		reference_date = reference_date or posting_date
		reference_no = reference_no or f"AUTO-PAY-{secrets.token_hex(8).upper()}"
	if source.account_type == "Bank" or counterpart.account_type == "Bank":
		if not reference_no or not reference_date:
			frappe.throw(_("Enter the bank reference number and date."))
	if len(narration) > 1000:
		frappe.throw(_("Narration is too long."))
	if isinstance(allocations, str):
		allocations = frappe.parse_json(allocations)
	allocations = allocations or []
	if not isinstance(allocations, list):
		frappe.throw(_("Invoice allocations must be a list."))
	if customer and (flow != "payment" or counterpart.account_type != "Receivable"):
		frappe.throw(_("Select a customer receivable account for a customer payment."))

	if flow == "cash_expense":
		frappe.has_permission("Journal Entry", "create", throw=True)
		if counterpart.root_type != "Expense" or party or allocations:
			frappe.throw(_("Cash expense requires an expense account and no party or invoice allocation."))
		doc = frappe.new_doc("Journal Entry")
		doc.update({"voucher_type": "Cash Entry", "company": company, "posting_date": posting_date, "user_remark": narration, "mode_of_payment": _mode(source.account_type)})
		row = {"account": counterpart_account, "debit_in_account_currency": float(amount), "cost_center": details.cost_center}
		doc.append("accounts", row)
		doc.append("accounts", {"account": source_account, "credit_in_account_currency": float(amount)})
	elif flow == "internal_transfer":
		frappe.has_permission("Payment Entry", "create", throw=True)
		if counterpart.account_type not in ("Cash", "Bank") or party or allocations:
			frappe.throw(_("Transfer requires a different cash or bank destination with no party or allocation."))
		doc = frappe.new_doc("Payment Entry")
		doc.update({
			"payment_type": "Internal Transfer", "company": company, "posting_date": posting_date,
			"paid_from": source_account, "paid_to": counterpart_account,
			"paid_from_account_currency": details.default_currency, "paid_to_account_currency": details.default_currency,
			"paid_amount": float(amount), "received_amount": float(amount), "source_exchange_rate": 1, "target_exchange_rate": 1,
			"mode_of_payment": _mode(source.account_type), "custom_remarks": 1 if narration else 0, "remarks": narration,
			"reference_no": reference_no, "reference_date": reference_date,
		})
	elif flow == "payment" and counterpart.account_type == "Receivable":
		frappe.has_permission("Journal Entry", "create", throw=True)
		if not customer or party or allocations:
			frappe.throw(_("Select the customer; customer payments cannot include invoice allocations."))
		if get_customer_receivable_account(company, customer)["account"] != counterpart_account:
			frappe.throw(_("The receivable account does not match the selected customer."))
		doc = frappe.new_doc("Journal Entry")
		doc.update({
			"voucher_type": "Cash Entry" if source.account_type == "Cash" else "Bank Entry",
			"company": company, "posting_date": posting_date, "user_remark": narration,
			"mode_of_payment": _mode(source.account_type), "cheque_no": reference_no, "cheque_date": reference_date,
		})
		doc.append("accounts", {
			"account": counterpart_account, "party_type": "Customer", "party": customer,
			"debit_in_account_currency": float(amount),
		})
		doc.append("accounts", {"account": source_account, "credit_in_account_currency": float(amount)})
	elif flow in ("supplier_payment", "bank_receipt", "payment"):
		party_type, voucher_type, account_type, payment_type = (
			("Supplier", "Purchase Invoice", "Payable", "Pay") if flow in ("supplier_payment", "payment") else ("Customer", "Sales Invoice", "Receivable", "Receive")
		)
		if counterpart.account_type == account_type:
			frappe.has_permission("Payment Entry", "create", throw=True)
			if not party:
				frappe.throw(_("Select the party for this account."))
			frappe.has_permission(party_type, "read", party, throw=True)
			references = _references(company, counterpart_account, party_type, party, voucher_type, allocations, amount)
			doc = frappe.new_doc("Payment Entry")
			doc.update({
				"payment_type": payment_type, "company": company, "posting_date": posting_date,
				"party_type": party_type, "party": party,
				"paid_from": source_account if flow in ("supplier_payment", "payment") else counterpart_account,
				"paid_to": counterpart_account if flow in ("supplier_payment", "payment") else source_account,
				"paid_from_account_currency": details.default_currency, "paid_to_account_currency": details.default_currency,
				"paid_amount": float(amount), "received_amount": float(amount), "source_exchange_rate": 1, "target_exchange_rate": 1,
				"cost_center": details.cost_center, "mode_of_payment": _mode(source.account_type),
				"custom_remarks": 1 if narration else 0, "remarks": narration,
				"reference_no": reference_no, "reference_date": reference_date,
			})
			for reference in references:
				doc.append("references", reference)
		elif flow == "bank_receipt" and counterpart.root_type == "Income" and not party and not allocations:
			frappe.has_permission("Journal Entry", "create", throw=True)
			doc = frappe.new_doc("Journal Entry")
			doc.update({"voucher_type": "Bank Entry", "company": company, "posting_date": posting_date, "user_remark": narration, "mode_of_payment": _mode(source.account_type), "cheque_no": reference_no, "cheque_date": reference_date})
			doc.append("accounts", {"account": source_account, "debit_in_account_currency": float(amount)})
			doc.append("accounts", {"account": counterpart_account, "credit_in_account_currency": float(amount), "cost_center": details.cost_center})
		elif flow == "payment" and counterpart.root_type in ("Expense", "Asset") and counterpart.account_type not in ("Cash", "Bank") and not party and not allocations:
			frappe.has_permission("Journal Entry", "create", throw=True)
			doc = frappe.new_doc("Journal Entry")
			doc.update({"voucher_type": "Cash Entry" if source.account_type == "Cash" else "Bank Entry", "company": company, "posting_date": posting_date, "user_remark": narration, "mode_of_payment": _mode(source.account_type), "cheque_no": reference_no, "cheque_date": reference_date})
			debit_row = {"account": counterpart_account, "debit_in_account_currency": float(amount)}
			if counterpart.root_type == "Expense":
				debit_row["cost_center"] = details.cost_center
			doc.append("accounts", debit_row)
			doc.append("accounts", {"account": source_account, "credit_in_account_currency": float(amount)})
		elif flow == "payment" and counterpart.account_type in ("Cash", "Bank") and not party and not allocations:
			frappe.has_permission("Payment Entry", "create", throw=True)
			doc = frappe.new_doc("Payment Entry")
			doc.update({"payment_type": "Internal Transfer", "company": company, "posting_date": posting_date, "paid_from": source_account, "paid_to": counterpart_account, "paid_from_account_currency": details.default_currency, "paid_to_account_currency": details.default_currency, "paid_amount": float(amount), "received_amount": float(amount), "source_exchange_rate": 1, "target_exchange_rate": 1, "mode_of_payment": _mode(source.account_type), "custom_remarks": 1 if narration else 0, "remarks": narration, "reference_no": reference_no, "reference_date": reference_date})
		else:
			frappe.throw(_("Choose the correct party account and party details."))
	else:
		frappe.throw(_("Invalid fast-entry flow."))

	doc.insert()
	return {"doctype": doc.doctype, "name": doc.name, "docstatus": doc.docstatus}
