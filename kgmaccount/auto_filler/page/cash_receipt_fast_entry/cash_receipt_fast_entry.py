"""A small input adapter for standard ERPNext cash receipt vouchers."""

import secrets
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_outstanding_reference_documents

from kgmaccount.auto_filler.utils.accounting_fast_entry import order_invoice_rows
from erpnext.accounts.party import get_party_account


def _money(value):
	try:
		amount = Decimal(str(value))
		if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
			raise ValueError
		return amount
	except (InvalidOperation, TypeError, ValueError):
		frappe.throw(_("Enter an amount greater than zero with at most two decimal places."))


def _company(company):
	frappe.has_permission("Company", "read", company, throw=True)
	details = frappe.db.get_value(
		"Company", company, ["default_currency", "default_cash_account", "cost_center"], as_dict=True
	)
	if not details:
		frappe.throw(_("Select a valid company."))
	if details.default_currency != "INR":
		frappe.throw(_("This fast-entry page currently supports INR companies only."))
	return details


def _account(name, company, currency):
	frappe.has_permission("Account", "read", name, throw=True)
	account = frappe.db.get_value(
		"Account",
		name,
		["company", "account_type", "account_currency", "root_type", "is_group", "disabled"],
		as_dict=True,
	)
	if not account or account.company != company or account.is_group or account.disabled:
		frappe.throw(_("Select an active posting account in the chosen company."))
	if account.account_currency != currency:
		frappe.throw(_("Both accounts must use the company currency ({0}).").format(currency))
	return account


def _invoice_rows(company, account, customer):
	frappe.has_permission("Payment Entry", "create", throw=True)
	frappe.has_permission("Customer", "read", customer, throw=True)
	rows = get_outstanding_reference_documents(
		{
			"company": company,
			"party_type": "Customer",
			"party": customer,
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
		if row.voucher_type == "Sales Invoice"
		and Decimal(str(row.outstanding_amount)) > 0
		and frappe.has_permission("Sales Invoice", "read", row.voucher_no)
	], "Sales Invoice", newest_first=False)


@frappe.whitelist()
def get_page_context():
	if not (frappe.has_permission("Payment Entry", "create") or frappe.has_permission("Journal Entry", "create")):
		frappe.throw(_("You need permission to create Payment Entries or Journal Entries."), frappe.PermissionError)
	company = frappe.defaults.get_user_default("Company")
	if not company:
		companies = frappe.get_list("Company", fields=["name"], limit_page_length=2)
		company = companies[0].name if len(companies) == 1 else ""
	return {
		"company": company,
		"cash_account": _company(company).default_cash_account if company else "",
		"posting_date": nowdate(),
	}


@frappe.whitelist()
def get_company_defaults(company):
	return {"cash_account": _company(company).default_cash_account}


@frappe.whitelist()
def get_receipt_account_kind(company, account):
	details = _company(company)
	receipt_account = _account(account, company, details.default_currency)
	if receipt_account.account_type not in ("Cash", "Bank"):
		frappe.throw(_("Select a cash or bank account."))
	return {"account_type": receipt_account.account_type}


@frappe.whitelist()
def get_counterpart_kind(company, account):
	details = _company(company)
	counterpart = _account(account, company, details.default_currency)
	if counterpart.account_type == "Payable":
		frappe.throw(_("Choose an income, customer receivable, cash, or bank account."))
	return {"account_type": counterpart.account_type, "root_type": counterpart.root_type}


@frappe.whitelist()
def get_customer_receivable_account(company, customer):
	"""Resolve the posting account while letting the cashier search by customer name."""
	details = _company(company)
	frappe.has_permission("Customer", "read", customer, throw=True)
	if not frappe.db.exists("Customer", {"name": customer, "disabled": 0}):
		frappe.throw(_("Select an active customer."))
	account = get_party_account("Customer", customer, company)
	if not account or _account(account, company, details.default_currency).account_type != "Receivable":
		frappe.throw(_("Set a valid receivable account for this customer or company."))
	return {"account": account, "account_type": "Receivable"}


@frappe.whitelist()
def get_open_invoices(company, account, customer):
	details = _company(company)
	if _account(account, company, details.default_currency).account_type != "Receivable":
		frappe.throw(_("Select a customer receivable account."))
	return _invoice_rows(company, account, customer)


@frappe.whitelist()
def save_cash_receipt_draft(
	company, posting_date, cash_account, counterpart_account, amount, narration=None, customer=None, allocations=None,
	reference_no=None, reference_date=None,
):
	company_details = _company(company)
	cash = _account(cash_account, company, company_details.default_currency)
	counterpart = _account(counterpart_account, company, company_details.default_currency)
	if cash.account_type not in ("Cash", "Bank"):
		frappe.throw(_("The receipt account must be a Cash or Bank account."))
	if counterpart_account == cash_account or counterpart.account_type == "Payable":
		frappe.throw(_("Choose a different income, customer receivable, cash, or bank account."))
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
	if cash.account_type == "Bank" or counterpart.account_type == "Bank":
		reference_date = reference_date or posting_date
		reference_no = reference_no or f"AUTO-REC-{secrets.token_hex(8).upper()}"
	if (cash.account_type == "Bank" or counterpart.account_type == "Bank") and (not reference_no or not reference_date):
		frappe.throw(_("Enter the bank reference number and date."))
	if len(narration) > 1000:
		frappe.throw(_("Narration is too long."))
	if isinstance(allocations, str):
		allocations = frappe.parse_json(allocations)
	allocations = allocations or []
	if not isinstance(allocations, list):
		frappe.throw(_("Invoice allocations must be a list."))

	if counterpart.account_type in ("Cash", "Bank"):
		frappe.has_permission("Payment Entry", "create", throw=True)
		if customer or allocations:
			frappe.throw(_("Customer and invoice fields do not apply to a cash or bank transfer."))
		doc = frappe.new_doc("Payment Entry")
		doc.update({
			"payment_type": "Internal Transfer", "company": company, "posting_date": posting_date,
			"paid_from": counterpart_account, "paid_to": cash_account,
			"paid_from_account_currency": company_details.default_currency, "paid_to_account_currency": company_details.default_currency,
			"paid_amount": float(amount), "received_amount": float(amount), "source_exchange_rate": 1, "target_exchange_rate": 1,
			"mode_of_payment": "Cash" if counterpart.account_type == "Cash" and frappe.db.exists("Mode of Payment", "Cash") else ("Bank" if frappe.db.exists("Mode of Payment", "Bank") else None),
			"custom_remarks": 1 if narration else 0, "remarks": narration, "reference_no": reference_no, "reference_date": reference_date,
		})
	elif counterpart.account_type == "Receivable":
		frappe.has_permission("Payment Entry", "create", throw=True)
		if not customer:
			frappe.throw(_("Select the customer for this receivable account."))
		frappe.has_permission("Customer", "read", customer, throw=True)
		available = {
			(row["invoice"], row["payment_term"]): Decimal(str(row["outstanding_amount"]))
			for row in _invoice_rows(company, counterpart_account, customer)
		}
		seen = set()
		allocated_total = Decimal("0")
		references = []
		for allocation in allocations:
			if not isinstance(allocation, dict):
				frappe.throw(_("Invalid invoice allocation."))
			key = (allocation.get("invoice"), allocation.get("payment_term") or "")
			if key in seen or key not in available:
				frappe.throw(_("Select an open invoice belonging to this customer and account."))
			seen.add(key)
			allocated = _money(allocation.get("amount"))
			if allocated > available[key]:
				frappe.throw(_("An invoice allocation exceeds its outstanding amount."))
			allocated_total += allocated
			reference = {
				"reference_doctype": "Sales Invoice",
				"reference_name": key[0],
				"allocated_amount": float(allocated),
			}
			if key[1]:
				reference["payment_term"] = key[1]
			references.append(reference)
		if allocated_total > amount:
			frappe.throw(_("Invoice allocations cannot exceed the cash received."))

		doc = frappe.new_doc("Payment Entry")
		doc.update(
			{
				"payment_type": "Receive",
				"company": company,
				"posting_date": posting_date,
				"party_type": "Customer",
				"party": customer,
				"paid_from": counterpart_account,
				"paid_to": cash_account,
				"paid_from_account_currency": company_details.default_currency,
				"paid_to_account_currency": company_details.default_currency,
				"paid_amount": float(amount),
				"received_amount": float(amount),
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"cost_center": company_details.cost_center,
				"mode_of_payment": cash.account_type if frappe.db.exists("Mode of Payment", cash.account_type) else None,
				"custom_remarks": 1 if narration else 0,
				"remarks": narration,
				"reference_no": reference_no,
				"reference_date": reference_date,
			}
		)
		for reference in references:
			doc.append("references", reference)
	else:
		frappe.has_permission("Journal Entry", "create", throw=True)
		if customer or allocations:
			frappe.throw(_("Customer and invoice fields apply only to receivable accounts."))
		doc = frappe.new_doc("Journal Entry")
		doc.update(
			{
				"voucher_type": "Cash Entry" if cash.account_type == "Cash" else "Bank Entry",
				"company": company,
				"posting_date": posting_date,
				"user_remark": narration,
				"mode_of_payment": cash.account_type if frappe.db.exists("Mode of Payment", cash.account_type) else None,
				"cheque_no": reference_no,
				"cheque_date": reference_date,
			}
		)
		doc.append("accounts", {"account": cash_account, "debit_in_account_currency": float(amount)})
		row = {"account": counterpart_account, "credit_in_account_currency": float(amount)}
		if counterpart.root_type in ("Income", "Expense"):
			row["cost_center"] = company_details.cost_center
		doc.append("accounts", row)

	doc.insert()
	return {"doctype": doc.doctype, "name": doc.name, "docstatus": doc.docstatus}
