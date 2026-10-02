"""Rollback-safe verification for the additional accounting fast-entry pages."""

from decimal import Decimal

import frappe

from kgmaccount.auto_filler.utils import accounting_fast_entry as entry


COMPANY = "Kirti Granite And Marble"
CASH = "Cash - KGAM"
PAYABLE = "Creditors - KGAM"
RECEIVABLE = "Debtors - KGAM"
INCOME = "Sales - KGAM"
SUSPENSE = "Suspense Account - KGAM"
CUSTOMER = "Stone Galaxy Rahul"
CUSTOMER_PAYMENT = "Hanuman Granite"
INVOICE = "ACC-SINV-2026-00054"
BROWSER_MARKER = "BROWSER OTHER FAST ENTRY TEST - DELETE"


def _money(value):
	return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _gl(doctype, name):
	return frappe.get_all("GL Entry", filters={"voucher_type": doctype, "voucher_no": name}, fields=["account", "debit", "credit"])


def _balanced(rows, debit_account, credit_account, amount):
	amount = _money(amount)
	return (
		bool(rows)
		and sum((_money(row.debit) for row in rows), _money(0)) == sum((_money(row.credit) for row in rows), _money(0))
		and sum((_money(row.debit) for row in rows if row.account == debit_account), _money(0)) == amount
		and sum((_money(row.credit) for row in rows if row.account == credit_account), _money(0)) == amount
	)


def run():
	"""Create, submit, inspect, and roll back one of each new fast-entry type."""
	frappe.set_user("Administrator")
	frappe.db.savepoint("additional_fast_entries")
	checks, created = {}, []
	invoice_before = _money(frappe.db.get_value("Sales Invoice", INVOICE, "outstanding_amount"))
	try:
		expense = frappe.db.get_value(
			"Account", {"company": COMPANY, "is_group": 0, "disabled": 0, "root_type": "Expense"}, "name"
		)
		bank = frappe.get_doc({
			"doctype": "Account", "account_name": "Fast Entry Test Bank", "company": COMPANY,
			"parent_account": "Bank Accounts - KGAM", "root_type": "Asset", "account_type": "Bank", "is_group": 0,
		}).insert()
		supplier = frappe.get_doc({"doctype": "Supplier", "supplier_name": "Fast Entry Test Supplier", "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")}).insert()
		base = {"company": COMPANY, "posting_date": frappe.utils.nowdate(), "source_account": CASH, "amount": "125", "narration": "Rollback-safe additional fast-entry verification"}

		cash_expense = entry.save_draft("payment", counterpart_account=expense, **base)
		created.append(cash_expense)
		cash_expense_doc = frappe.get_doc(cash_expense["doctype"], cash_expense["name"])
		checks["cash_expense_draft"] = {"passed": cash_expense_doc.doctype == "Journal Entry" and cash_expense_doc.voucher_type == "Cash Entry" and not cash_expense_doc.cheque_no and cash_expense_doc.docstatus == 0 and not _gl("Journal Entry", cash_expense_doc.name)}
		cash_expense_doc.submit()
		checks["cash_expense_submit"] = {"passed": _balanced(_gl("Journal Entry", cash_expense_doc.name), expense, CASH, 125), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Journal Entry", cash_expense_doc.name)]}

		suspense_payment = entry.save_draft("payment", counterpart_account=SUSPENSE, **{**base, "amount": "20000"})
		created.append(suspense_payment)
		suspense_doc = frappe.get_doc(suspense_payment["doctype"], suspense_payment["name"])
		checks["cash_to_suspense_draft"] = {"passed": suspense_doc.doctype == "Journal Entry" and suspense_doc.voucher_type == "Cash Entry" and suspense_doc.docstatus == 0 and not _gl("Journal Entry", suspense_doc.name)}
		suspense_doc.submit()
		checks["cash_to_suspense_submit"] = {"passed": _balanced(_gl("Journal Entry", suspense_doc.name), SUSPENSE, CASH, 20000), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Journal Entry", suspense_doc.name)]}

		customer_account = entry.get_customer_receivable_account(COMPANY, CUSTOMER_PAYMENT)["account"]
		customer_invoices_before = {
			row.name: _money(row.outstanding_amount) for row in frappe.get_all(
				"Sales Invoice", filters={"customer": CUSTOMER_PAYMENT, "docstatus": 1},
				fields=["name", "outstanding_amount"],
			)
		}
		customer_payment = entry.save_draft(
			"payment", counterpart_account=customer_account, customer=CUSTOMER_PAYMENT,
			**{**base, "amount": "35"},
		)
		created.append(customer_payment)
		customer_payment_doc = frappe.get_doc(customer_payment["doctype"], customer_payment["name"])
		customer_row = next((row for row in customer_payment_doc.accounts if row.account == customer_account), None)
		checks["direct_customer_payment_draft"] = {"passed": bool(
			customer_payment_doc.doctype == "Journal Entry" and customer_payment_doc.voucher_type == "Cash Entry"
			and customer_payment_doc.docstatus == 0 and customer_row
			and customer_row.party_type == "Customer" and customer_row.party == CUSTOMER_PAYMENT
			and _money(customer_row.debit_in_account_currency) == _money(35)
			and not customer_row.reference_type and not customer_row.reference_name
			and not _gl("Journal Entry", customer_payment_doc.name)
		)}
		customer_payment_doc.submit()
		customer_gl = frappe.get_all(
			"GL Entry", filters={"voucher_type": "Journal Entry", "voucher_no": customer_payment_doc.name},
			fields=["account", "party_type", "party", "debit", "credit"],
		)
		checks["direct_customer_payment_submit"] = {
			"passed": _balanced(customer_gl, customer_account, CASH, 35)
			and any(row.account == customer_account and row.party_type == "Customer" and row.party == CUSTOMER_PAYMENT and _money(row.debit) == _money(35) for row in customer_gl)
			and all(_money(frappe.db.get_value("Sales Invoice", name, "outstanding_amount")) == balance for name, balance in customer_invoices_before.items()),
			"gl": [dict(account=row.account, party_type=row.party_type, party=row.party, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in customer_gl],
			"customer_invoices_checked": len(customer_invoices_before),
			"customer_invoice_before": {name: str(balance) for name, balance in customer_invoices_before.items()},
			"customer_invoice_after": {name: str(_money(frappe.db.get_value("Sales Invoice", name, "outstanding_amount"))) for name in customer_invoices_before},
		}

		bank_customer_payment = entry.save_draft(
			"payment", source_account=bank.name, counterpart_account=customer_account,
			customer=CUSTOMER_PAYMENT,
			**{key: value for key, value in base.items() if key != "source_account"},
		)
		created.append(bank_customer_payment)
		bank_customer_doc = frappe.get_doc(bank_customer_payment["doctype"], bank_customer_payment["name"])
		checks["bank_customer_payment_draft"] = {"passed": bank_customer_doc.doctype == "Journal Entry" and bank_customer_doc.voucher_type == "Bank Entry" and bank_customer_doc.cheque_no.startswith("AUTO-PAY-") and str(bank_customer_doc.cheque_date) == str(bank_customer_doc.posting_date) and bank_customer_doc.docstatus == 0 and not _gl("Journal Entry", bank_customer_doc.name), "reference_no": bank_customer_doc.cheque_no, "reference_date": str(bank_customer_doc.cheque_date)}
		bank_customer_doc.submit()
		bank_customer_gl = frappe.get_all("GL Entry", filters={"voucher_type": "Journal Entry", "voucher_no": bank_customer_doc.name}, fields=["account", "party_type", "party", "debit", "credit"])
		checks["bank_customer_payment_submit"] = {"passed": _balanced(bank_customer_gl, customer_account, bank.name, 125) and any(row.account == customer_account and row.party_type == "Customer" and row.party == CUSTOMER_PAYMENT for row in bank_customer_gl) and all(_money(frappe.db.get_value("Sales Invoice", name, "outstanding_amount")) == balance for name, balance in customer_invoices_before.items()), "gl": [dict(account=row.account, party_type=row.party_type, party=row.party, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in bank_customer_gl]}
		for label, changes in (
			("missing_customer_on_receivable", {"customer": None}),
			("customer_payment_with_invoice_allocation", {"customer": CUSTOMER_PAYMENT, "allocations": [{"invoice": "ACC-SINV-2026-00028", "amount": "5"}]}),
			("customer_on_expense_account", {"customer": CUSTOMER_PAYMENT, "counterpart_account": expense}),
			("supplier_party_on_customer_payment", {"customer": CUSTOMER_PAYMENT, "party": supplier.name}),
		):
			try:
				unexpected = entry.save_draft("payment", **{**base, "counterpart_account": customer_account, **changes})
				created.append(unexpected)
				checks[label] = {"passed": False, "unexpected_voucher": unexpected}
			except (frappe.ValidationError, frappe.PermissionError, frappe.LinkValidationError) as exc:
				checks[label] = {"passed": True, "rejected_as": type(exc).__name__}

		supplier_payment = entry.save_draft("payment", counterpart_account=PAYABLE, party=supplier.name, allocations=[], **{**base, "amount": "75"})
		created.append(supplier_payment)
		supplier_doc = frappe.get_doc(supplier_payment["doctype"], supplier_payment["name"])
		checks["supplier_advance_draft"] = {"passed": supplier_doc.doctype == "Payment Entry" and supplier_doc.payment_type == "Pay" and supplier_doc.party == supplier.name and supplier_doc.docstatus == 0 and not _gl("Payment Entry", supplier_doc.name)}
		supplier_doc.submit()
		checks["supplier_advance_submit"] = {"passed": _balanced(_gl("Payment Entry", supplier_doc.name), PAYABLE, CASH, 75), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Payment Entry", supplier_doc.name)]}
		bank_supplier_payment = entry.save_draft("payment", source_account=bank.name, counterpart_account=PAYABLE, party=supplier.name, allocations=[], **{key: value for key, value in base.items() if key != "source_account"})
		created.append(bank_supplier_payment)
		bank_supplier_doc = frappe.get_doc(bank_supplier_payment["doctype"], bank_supplier_payment["name"])
		checks["bank_supplier_payment_draft"] = {"passed": bank_supplier_doc.doctype == "Payment Entry" and bank_supplier_doc.payment_type == "Pay" and bank_supplier_doc.reference_no.startswith("AUTO-PAY-") and str(bank_supplier_doc.reference_date) == str(bank_supplier_doc.posting_date) and bank_supplier_doc.reference_no != bank_customer_doc.cheque_no and bank_supplier_doc.docstatus == 0 and not _gl("Payment Entry", bank_supplier_doc.name), "reference_no": bank_supplier_doc.reference_no, "reference_date": str(bank_supplier_doc.reference_date)}
		bank_supplier_doc.submit()
		checks["bank_supplier_payment_submit"] = {"passed": _balanced(_gl("Payment Entry", bank_supplier_doc.name), PAYABLE, bank.name, 125), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Payment Entry", bank_supplier_doc.name)]}
		bank_expense_date = frappe.utils.add_days(frappe.utils.nowdate(), -1)
		bank_expense = entry.save_draft("payment", source_account=bank.name, counterpart_account=expense, **{**{key: value for key, value in base.items() if key != "source_account"}, "posting_date": bank_expense_date})
		created.append(bank_expense)
		bank_expense_doc = frappe.get_doc(bank_expense["doctype"], bank_expense["name"])
		checks["bank_expense_draft"] = {"passed": bank_expense_doc.doctype == "Journal Entry" and bank_expense_doc.voucher_type == "Bank Entry" and bank_expense_doc.cheque_no.startswith("AUTO-PAY-") and str(bank_expense_doc.cheque_date) == str(bank_expense_doc.posting_date) == bank_expense_date and bank_expense_doc.docstatus == 0 and not _gl("Journal Entry", bank_expense_doc.name), "reference_no": bank_expense_doc.cheque_no, "posting_date": str(bank_expense_doc.posting_date), "reference_date": str(bank_expense_doc.cheque_date)}
		bank_expense_doc.submit()
		checks["bank_expense_submit"] = {"passed": _balanced(_gl("Journal Entry", bank_expense_doc.name), expense, bank.name, 125), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Journal Entry", bank_expense_doc.name)]}
		bank_suspense = entry.save_draft("payment", source_account=bank.name, counterpart_account=SUSPENSE, **{key: value for key, value in base.items() if key != "source_account"})
		created.append(bank_suspense)
		bank_suspense_doc = frappe.get_doc(bank_suspense["doctype"], bank_suspense["name"])
		checks["bank_to_suspense_draft"] = {"passed": bank_suspense_doc.doctype == "Journal Entry" and bank_suspense_doc.voucher_type == "Bank Entry" and bank_suspense_doc.cheque_no.startswith("AUTO-PAY-") and str(bank_suspense_doc.cheque_date) == str(bank_suspense_doc.posting_date) and bank_suspense_doc.docstatus == 0 and not _gl("Journal Entry", bank_suspense_doc.name), "reference_no": bank_suspense_doc.cheque_no, "reference_date": str(bank_suspense_doc.cheque_date)}
		bank_suspense_doc.submit()
		checks["bank_to_suspense_submit"] = {"passed": _balanced(_gl("Journal Entry", bank_suspense_doc.name), SUSPENSE, bank.name, 125), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Journal Entry", bank_suspense_doc.name)]}

		transfer = entry.save_draft(
			"payment", counterpart_account=bank.name, party=None, allocations=[],
			**{**base, "amount": "50"},
		)
		created.append(transfer)
		transfer_doc = frappe.get_doc(transfer["doctype"], transfer["name"])
		checks["transfer_draft"] = {"passed": transfer_doc.doctype == "Payment Entry" and transfer_doc.payment_type == "Internal Transfer" and transfer_doc.reference_no.startswith("AUTO-PAY-") and str(transfer_doc.reference_date) == str(transfer_doc.posting_date) and transfer_doc.docstatus == 0 and not _gl("Payment Entry", transfer_doc.name), "reference_no": transfer_doc.reference_no, "reference_date": str(transfer_doc.reference_date)}
		transfer_doc.submit()
		checks["transfer_submit"] = {"passed": _balanced(_gl("Payment Entry", transfer_doc.name), bank.name, CASH, 50), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Payment Entry", transfer_doc.name)]}

		customer_receipt = entry.save_draft(
			"bank_receipt", source_account=bank.name, counterpart_account=RECEIVABLE, party=CUSTOMER,
			allocations=[{"invoice": INVOICE, "amount": "60"}], reference_no="FAST-BANK-CUSTOMER-TEST",
			reference_date=frappe.utils.nowdate(), **{key: value for key, value in base.items() if key not in ("source_account", "amount")}, amount="60",
		)
		created.append(customer_receipt)
		customer_doc = frappe.get_doc(customer_receipt["doctype"], customer_receipt["name"])
		checks["bank_customer_receipt_draft"] = {"passed": customer_doc.doctype == "Payment Entry" and customer_doc.payment_type == "Receive" and customer_doc.references[0].reference_name == INVOICE and _money(customer_doc.references[0].allocated_amount) == _money(60) and customer_doc.docstatus == 0 and not _gl("Payment Entry", customer_doc.name)}
		customer_doc.submit()
		invoice_after = _money(frappe.db.get_value("Sales Invoice", INVOICE, "outstanding_amount"))
		checks["bank_customer_receipt_submit"] = {"passed": _balanced(_gl("Payment Entry", customer_doc.name), bank.name, RECEIVABLE, 60) and invoice_after == invoice_before - _money(60), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Payment Entry", customer_doc.name)], "invoice_before": str(invoice_before), "invoice_after": str(invoice_after)}

		income_receipt = entry.save_draft(
			"bank_receipt", source_account=bank.name, counterpart_account=INCOME, party=None, allocations=[],
			reference_no="FAST-BANK-INCOME-TEST", reference_date=frappe.utils.nowdate(),
			**{key: value for key, value in base.items() if key != "source_account"},
		)
		created.append(income_receipt)
		income_doc = frappe.get_doc(income_receipt["doctype"], income_receipt["name"])
		checks["bank_income_receipt_draft"] = {"passed": income_doc.doctype == "Journal Entry" and income_doc.voucher_type == "Bank Entry" and income_doc.docstatus == 0 and not _gl("Journal Entry", income_doc.name)}
		income_doc.submit()
		checks["bank_income_receipt_submit"] = {"passed": _balanced(_gl("Journal Entry", income_doc.name), bank.name, INCOME, 125), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in _gl("Journal Entry", income_doc.name)]}
	finally:
		frappe.db.rollback(save_point="additional_fast_entries")
	checks["rollback_cleanup"] = {"passed": all(not frappe.db.exists(item["doctype"], item["name"]) and not _gl(item["doctype"], item["name"]) for item in created) and _money(frappe.db.get_value("Sales Invoice", INVOICE, "outstanding_amount")) == invoice_before and all(_money(frappe.db.get_value("Sales Invoice", name, "outstanding_amount")) == balance for name, balance in customer_invoices_before.items()), "invoice_balance": str(_money(frappe.db.get_value("Sales Invoice", INVOICE, "outstanding_amount")))}
	return checks


def cleanup_browser_drafts():
	"""Remove the one browser-created draft after its standard-voucher check."""
	frappe.set_user("Administrator")
	deleted = []
	for doctype, fieldname in (("Journal Entry", "user_remark"), ("Payment Entry", "remarks")):
		for name in frappe.get_all(doctype, filters={fieldname: BROWSER_MARKER, "docstatus": 0}, pluck="name"):
			frappe.delete_doc(doctype, name, force=True)
			deleted.append(f"{doctype} {name}")
	frappe.db.commit()
	return {"deleted": deleted, "remaining": sum(frappe.db.count(doctype, {fieldname: BROWSER_MARKER}) for doctype, fieldname in (("Journal Entry", "user_remark"), ("Payment Entry", "remarks")))}


def structural_audit():
	"""Verify these page features introduce no accounting schema."""
	keywords = ("Cash Receipt Fast Entry", "Cash Expense Fast Entry", "Supplier Payment Fast Entry", "Cash / Bank Transfer Fast Entry", "Bank Receipt Fast Entry")
	matching_doctypes = [name for name in frappe.get_all("DocType", pluck="name") if any(keyword in name for keyword in keywords)]
	matching_tables = [name for name in frappe.db.get_tables() if "fast_entry" in name or "cash_receipt" in name]
	return {"passed": not matching_doctypes and not matching_tables, "doctypes": matching_doctypes, "tables": matching_tables}
