"""Rollback-safe accounting checks for the Cash Receipt Fast Entry page.

Run on the isolated dev site with:
    bench --site frontend execute kgmaccount.tests.test_cash_receipt_fast_entry.run
"""

from decimal import Decimal

import frappe

from kgmaccount.auto_filler.page.cash_receipt_fast_entry import cash_receipt_fast_entry as receipt


COMPANY = "Kirti Granite And Marble"
CASH = "Cash - KGAM"
INCOME = "Sales - KGAM"
DEBTORS = "Debtors - KGAM"
CUSTOMER = "Stone Galaxy Rahul"
INVOICES = ("ACC-SINV-2026-00054", "ACC-SINV-2026-00114")


def _money(value):
	if value is None:
		return Decimal("0.00")
	return Decimal(str(value)).quantize(Decimal("0.01"))


def _reject(label, changes, checks):
	try:
		receipt.save_cash_receipt_draft(**changes)
	except Exception as exc:
		checks[label] = {"passed": type(exc).__name__ in {"ValidationError", "LinkValidationError", "PermissionError"}, "rejected_as": type(exc).__name__}
	else:
		checks[label] = {"passed": False, "error": "Accepted invalid receipt"}


def _gl(doctype, name):
	return frappe.get_all(
		"GL Entry",
		filters={"voucher_type": doctype, "voucher_no": name},
		fields=["account", "debit", "credit", "is_cancelled"],
		order_by="account",
	)


def _balances():
	return {name: _money(frappe.db.get_value("Sales Invoice", name, "outstanding_amount")) for name in INVOICES}


def run():
	"""Create, submit, inspect, and roll back all test vouchers."""
	checks = {}
	frappe.set_user("Administrator")
	frappe.db.savepoint("cash_receipt_verification")
	created = []
	try:
		assert receipt.get_page_context()["cash_account"] == CASH
		checks["default_cash"] = {"passed": True, "account": CASH}
		invoice_before = _balances()
		bank = frappe.get_doc({"doctype": "Account", "account_name": "Cash Receipt Test Bank", "company": COMPANY, "parent_account": "Bank Accounts - KGAM", "root_type": "Asset", "account_type": "Bank", "is_group": 0}).insert()
		base = dict(
			company=COMPANY,
			posting_date=frappe.utils.nowdate(),
			cash_account=CASH,
			counterpart_account=INCOME,
			amount="125",
			narration="Rollback-safe cash receipt verification",
		)
		journal_result = receipt.save_cash_receipt_draft(**base)
		created.append(journal_result)
		journal = frappe.get_doc(journal_result["doctype"], journal_result["name"])
		journal_rows = {row.account: (_money(row.debit_in_account_currency), _money(row.credit_in_account_currency)) for row in journal.accounts}
		checks["income_draft"] = {
			"passed": journal.doctype == "Journal Entry" and journal.docstatus == 0 and journal.voucher_type == "Cash Entry" and journal_rows == {CASH: (_money(125), _money(0)), INCOME: (_money(0), _money(125))},
			"voucher": journal_result,
			"rows": {key: [str(x) for x in value] for key, value in journal_rows.items()},
		}

		customer_base = {**base, "counterpart_account": DEBTORS, "customer": CUSTOMER}
		available = receipt.get_open_invoices(COMPANY, DEBTORS, CUSTOMER)
		available_names = {row["invoice"] for row in available}
		checks["invoice_list"] = {"passed": all(name in available_names for name in INVOICES), "selected": list(INVOICES), "available_count": len(available)}
		checks["fifo_oldest_bill_first"] = {"passed": bool(available) and available[0]["invoice"] == "ACC-SINV-2026-00114", "first_invoice": available[0]["invoice"] if available else None}
		allocations = [{"invoice": INVOICES[0], "amount": "60"}, {"invoice": INVOICES[1], "amount": "40"}]
		payment_result = receipt.save_cash_receipt_draft(**customer_base, allocations=allocations)
		created.append(payment_result)
		payment = frappe.get_doc(payment_result["doctype"], payment_result["name"])
		refs = {row.reference_name: _money(row.allocated_amount) for row in payment.references}
		checks["customer_draft"] = {
			"passed": payment.doctype == "Payment Entry" and payment.docstatus == 0 and payment.payment_type == "Receive" and payment.paid_from == DEBTORS and payment.paid_to == CASH and _money(payment.paid_amount) == _money(125) and refs == {INVOICES[0]: _money(60), INVOICES[1]: _money(40)} and _money(payment.unallocated_amount) == _money(25),
			"voucher": payment_result,
			"allocations": {key: str(value) for key, value in refs.items()},
			"unallocated": str(_money(payment.unallocated_amount)),
		}
		checks["draft_does_not_post"] = {"passed": not _gl("Journal Entry", journal.name) and not _gl("Payment Entry", payment.name) and _balances() == invoice_before, "invoice_before": {key: str(value) for key, value in invoice_before.items()}, "invoice_after": {key: str(value) for key, value in _balances().items()}, "gl_rows": 0}

		frappe.get_doc(journal_result["doctype"], journal_result["name"]).submit()
		frappe.get_doc(payment_result["doctype"], payment_result["name"]).submit()
		journal_gl = _gl("Journal Entry", journal.name)
		payment_gl = _gl("Payment Entry", payment.name)
		invoice_after = _balances()
		def checked_gl(rows, opposite):
			return bool(rows) and sum((_money(row.debit) for row in rows), _money(0)) == sum((_money(row.credit) for row in rows), _money(0)) and sum((_money(row.debit) for row in rows if row.account == CASH), _money(0)) == _money(125) and sum((_money(row.credit) for row in rows if row.account == opposite), _money(0)) == _money(125)
		checks["income_submit_gl"] = {"passed": checked_gl(journal_gl, INCOME), "rows": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in journal_gl]}
		checks["customer_submit_gl"] = {"passed": checked_gl(payment_gl, DEBTORS), "rows": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in payment_gl]}
		checks["invoice_decrements"] = {"passed": invoice_after[INVOICES[0]] == invoice_before[INVOICES[0]] - _money(60) and invoice_after[INVOICES[1]] == invoice_before[INVOICES[1]] - _money(40), "before": {key: str(value) for key, value in invoice_before.items()}, "after": {key: str(value) for key, value in invoice_after.items()}}

		advance_result = receipt.save_cash_receipt_draft(**customer_base, allocations=[])
		created.append(advance_result)
		advance = frappe.get_doc(advance_result["doctype"], advance_result["name"])
		checks["unallocated_advance"] = {"passed": advance.docstatus == 0 and not advance.references and _money(advance.unallocated_amount) == _money(125), "unallocated": str(_money(advance.unallocated_amount))}
		partial_result = receipt.save_cash_receipt_draft(**{**customer_base, "amount": "25"}, allocations=[{"invoice": INVOICES[0], "amount": "25"}])
		created.append(partial_result)
		partial = frappe.get_doc(partial_result["doctype"], partial_result["name"])
		checks["partial_invoice_payment"] = {"passed": partial.docstatus == 0 and len(partial.references) == 1 and _money(partial.references[0].allocated_amount) == _money(25) and _money(partial.unallocated_amount) == _money(0), "allocated": str(_money(partial.references[0].allocated_amount)), "unallocated": str(_money(partial.unallocated_amount))}
		frappe.get_doc(advance_result["doctype"], advance_result["name"]).submit()
		advance_gl = _gl("Payment Entry", advance_result["name"])
		checks["advance_submit_gl"] = {"passed": checked_gl(advance_gl, DEBTORS) and _balances() == invoice_after, "rows": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in advance_gl], "invoice_balances": {key: str(value) for key, value in _balances().items()}}
		frappe.get_doc(partial_result["doctype"], partial_result["name"]).submit()
		partial_gl = _gl("Payment Entry", partial_result["name"])
		partial_after = _balances()
		checks["partial_submit_gl"] = {"passed": bool(partial_gl) and sum((_money(row.debit) for row in partial_gl), _money(0)) == _money(25) and sum((_money(row.credit) for row in partial_gl), _money(0)) == _money(25) and sum((_money(row.debit) for row in partial_gl if row.account == CASH), _money(0)) == _money(25) and sum((_money(row.credit) for row in partial_gl if row.account == DEBTORS), _money(0)) == _money(25) and partial_after[INVOICES[0]] == invoice_after[INVOICES[0]] - _money(25) and partial_after[INVOICES[1]] == invoice_after[INVOICES[1]], "rows": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in partial_gl], "invoice_before": {key: str(value) for key, value in invoice_after.items()}, "invoice_after": {key: str(value) for key, value in partial_after.items()}}

		bank_base = {**base, "cash_account": bank.name, "posting_date": frappe.utils.add_days(frappe.utils.nowdate(), -1)}
		bank_journal_result = receipt.save_cash_receipt_draft(**bank_base)
		created.append(bank_journal_result)
		bank_journal = frappe.get_doc(bank_journal_result["doctype"], bank_journal_result["name"])
		bank_rows = {row.account: (_money(row.debit_in_account_currency), _money(row.credit_in_account_currency)) for row in bank_journal.accounts}
		checks["bank_income_draft"] = {"passed": bank_journal.doctype == "Journal Entry" and bank_journal.voucher_type == "Bank Entry" and bank_journal.cheque_no.startswith("AUTO-REC-") and str(bank_journal.cheque_date) == str(bank_journal.posting_date) == bank_base["posting_date"] and bank_journal.docstatus == 0 and bank_rows == {bank.name: (_money(125), _money(0)), INCOME: (_money(0), _money(125))}, "voucher": bank_journal_result, "reference_no": bank_journal.cheque_no, "reference_date": str(bank_journal.cheque_date)}
		checks["bank_draft_does_not_post"] = {"passed": not _gl("Journal Entry", bank_journal.name), "gl_rows": len(_gl("Journal Entry", bank_journal.name))}
		bank_journal.submit()
		bank_journal_gl = _gl("Journal Entry", bank_journal.name)
		checks["bank_income_submit_gl"] = {"passed": bool(bank_journal_gl) and sum((_money(row.debit) for row in bank_journal_gl if row.account == bank.name), _money(0)) == _money(125) and sum((_money(row.credit) for row in bank_journal_gl if row.account == INCOME), _money(0)) == _money(125), "rows": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in bank_journal_gl]}
		bank_invoice_before = _balances()
		bank_payment_result = receipt.save_cash_receipt_draft(**{**bank_base, "counterpart_account": DEBTORS, "customer": CUSTOMER, "amount": "10"}, allocations=[{"invoice": INVOICES[0], "amount": "10"}])
		created.append(bank_payment_result)
		bank_payment = frappe.get_doc(bank_payment_result["doctype"], bank_payment_result["name"])
		checks["bank_customer_draft"] = {"passed": bank_payment.doctype == "Payment Entry" and bank_payment.payment_type == "Receive" and bank_payment.paid_to == bank.name and bank_payment.reference_no.startswith("AUTO-REC-") and bank_payment.reference_no != bank_journal.cheque_no and str(bank_payment.reference_date) == str(bank_payment.posting_date) and bank_payment.docstatus == 0 and not _gl("Payment Entry", bank_payment.name), "reference_no": bank_payment.reference_no, "reference_date": str(bank_payment.reference_date)}
		bank_payment.submit()
		bank_invoice_after = _balances()
		checks["bank_customer_submit"] = {"passed": sum((_money(row.debit) for row in _gl("Payment Entry", bank_payment.name) if row.account == bank.name), _money(0)) == _money(10) and sum((_money(row.credit) for row in _gl("Payment Entry", bank_payment.name) if row.account == DEBTORS), _money(0)) == _money(10) and bank_invoice_after[INVOICES[0]] == bank_invoice_before[INVOICES[0]] - _money(10), "invoice_before": str(bank_invoice_before[INVOICES[0]]), "invoice_after": str(bank_invoice_after[INVOICES[0]])}
		bank_two = frappe.get_doc({"doctype": "Account", "account_name": "Cash Receipt Test Bank Two", "company": COMPANY, "parent_account": "Bank Accounts - KGAM", "root_type": "Asset", "account_type": "Bank", "is_group": 0}).insert()
		for label, receipt_account, transfer_from in (
			("cash_to_bank_transfer", bank.name, CASH),
			("bank_to_cash_transfer", CASH, bank.name),
			("interbank_transfer", bank_two.name, bank.name),
		):
			transfer_result = receipt.save_cash_receipt_draft(**{**base, "cash_account": receipt_account, "counterpart_account": transfer_from})
			created.append(transfer_result)
			transfer = frappe.get_doc(transfer_result["doctype"], transfer_result["name"])
			draft_ok = transfer.doctype == "Payment Entry" and transfer.payment_type == "Internal Transfer" and transfer.paid_from == transfer_from and transfer.paid_to == receipt_account and transfer.reference_no.startswith("AUTO-REC-") and str(transfer.reference_date) == str(transfer.posting_date) and transfer.docstatus == 0 and not _gl("Payment Entry", transfer.name)
			transfer.submit()
			rows = _gl("Payment Entry", transfer.name)
			checks[label] = {"passed": draft_ok and sum((_money(row.debit) for row in rows if row.account == receipt_account), _money(0)) == _money(125) and sum((_money(row.credit) for row in rows if row.account == transfer_from), _money(0)) == _money(125), "gl": [dict(account=row.account, debit=str(_money(row.debit)), credit=str(_money(row.credit))) for row in rows]}

		for label, value in [("zero_amount", "0"), ("negative_amount", "-1"), ("receipt_overprecision", "125.001"), ("trailing_zero_overprecision", "125.000")]:
			_reject(label, {**base, "amount": value}, checks)
		_reject("allocation_over_receipt", {**customer_base, "allocations": [{"invoice": INVOICES[0], "amount": "126"}]}, checks)
		_reject("allocation_over_outstanding", {**customer_base, "amount": "999999", "allocations": [{"invoice": INVOICES[0], "amount": "999999"}]}, checks)
		_reject("allocation_overprecision", {**customer_base, "allocations": [{"invoice": INVOICES[0], "amount": "1.001"}]}, checks)
		_reject("duplicate_invoice", {**customer_base, "allocations": [{"invoice": INVOICES[0], "amount": "1"}, {"invoice": INVOICES[0], "amount": "1"}]}, checks)
		_reject("missing_customer", {**base, "counterpart_account": DEBTORS}, checks)
		_reject("missing_customer_record", {**customer_base, "customer": "Nonexistent Customer"}, checks)
		_reject("foreign_customer_invoice", {**customer_base, "allocations": [{"invoice": "ACC-SINV-2026-00015", "amount": "1"}]}, checks)
		_reject("cash_counterpart", {**base, "counterpart_account": CASH}, checks)
		_reject("group_counterpart", {**base, "counterpart_account": "Income - KGAM"}, checks)
		_reject("supplier_payable", {**base, "counterpart_account": "Creditors - KGAM"}, checks)
		_reject("bank_group", {**base, "counterpart_account": "Bank Accounts - KGAM"}, checks)
		disabled = frappe.get_doc({"doctype": "Account", "account_name": "Cash Receipt Test Disabled", "company": COMPANY, "parent_account": "Indirect Income - KGAM", "root_type": "Income", "account_type": "Income Account", "is_group": 0, "disabled": 1}).insert()
		_reject("disabled_counterpart", {**base, "counterpart_account": disabled.name}, checks)
		frappe.db.sql("""insert into `tabAccount` (name, creation, modified, owner, modified_by, account_name, company, account_currency, root_type, is_group, disabled) values (%s, now(), now(), %s, %s, %s, %s, %s, %s, 0, 0)""", ("Cash Receipt Foreign Fixture - TEST", "Administrator", "Administrator", "Cash Receipt Foreign Fixture", "Unrelated Test Company", "INR", "Income"))
		_reject("wrong_company_account", {**base, "counterpart_account": "Cash Receipt Foreign Fixture - TEST"}, checks)
		_reject("invalid_cash_account", {**base, "cash_account": INCOME}, checks)
		_reject("customer_on_income", {**base, "customer": CUSTOMER}, checks)
		_reject("negative_allocation", {**customer_base, "allocations": [{"invoice": INVOICES[0], "amount": "-1"}]}, checks)
		frappe.set_user("Guest")
		try:
			_reject("guest_cannot_create", base, checks)
			try:
				receipt.get_page_context()
			except frappe.PermissionError:
				checks["guest_cannot_open"] = {"passed": True}
			else:
				checks["guest_cannot_open"] = {"passed": False}
		finally:
			frappe.set_user("Administrator")
	finally:
		frappe.db.rollback(save_point="cash_receipt_verification")
	checks["rollback_cleanup"] = {"passed": all(not frappe.db.exists(row["doctype"], row["name"]) and not _gl(row["doctype"], row["name"]) for row in created) and _balances() == invoice_before, "vouchers_checked": len(created), "invoice_balances": {key: str(value) for key, value in _balances().items()}}
	return checks


def cleanup_browser_drafts():
	"""Remove only drafts carrying the browser test's exact narration."""
	marker = "BROWSER CASH RECEIPT TEST - DELETE"
	rows = [("Journal Entry", name) for name in frappe.get_all("Journal Entry", filters={"user_remark": marker, "docstatus": 0}, pluck="name")]
	rows += [("Payment Entry", name) for name in frappe.get_all("Payment Entry", filters={"remarks": marker, "docstatus": 0}, pluck="name")]
	gl_before = {name: len(_gl(doctype, name)) for doctype, name in rows}
	for doctype, name in rows:
		frappe.delete_doc(doctype, name)
	frappe.db.commit()
	return {"draft_count_before": len(rows), "vouchers": rows, "gl_before": gl_before, "draft_count_after": frappe.db.count("Journal Entry", {"user_remark": marker}) + frappe.db.count("Payment Entry", {"remarks": marker}), "gl_after": {name: len(_gl(doctype, name)) for doctype, name in rows}}


def audit_residue():
	"""Read-only confirmation that test accounting data was removed."""
	accounts = ["Cash Receipt Test Disabled - KGAM", "Cash Receipt Test Bank - KGAM", "Cash Receipt Foreign Fixture - TEST"]
	return {
		"invoice_balances": {key: str(value) for key, value in _balances().items()},
		"test_accounts": {name: bool(frappe.db.exists("Account", name)) for name in accounts},
		"role_test_users": {role: bool(frappe.db.exists("User", f"cash-receipt-role-{role.lower().replace(' ', '-')}@example.invalid")) for role in ("Accounts User", "Accounts Manager", "Employee")},
		"accounting_test_drafts": frappe.db.count("Journal Entry", {"user_remark": "Rollback-safe cash receipt verification"}) + frappe.db.count("Payment Entry", {"remarks": "Rollback-safe cash receipt verification"}),
		"role_test_drafts": frappe.db.count("Journal Entry", {"user_remark": "Rollback-safe role check"}) + frappe.db.count("Payment Entry", {"remarks": "Rollback-safe role check"}),
		"browser_test_drafts": frappe.db.count("Journal Entry", {"user_remark": "BROWSER CASH RECEIPT TEST - DELETE"}) + frappe.db.count("Payment Entry", {"remarks": "BROWSER CASH RECEIPT TEST - DELETE"}),
		"cash_receipt_doctypes": frappe.get_all("DocType", filters={"name": ["like", "%Cash Receipt%"]}, pluck="name"),
		"cash_receipt_tables": [row[0] for row in frappe.db.sql("select table_name from information_schema.tables where table_schema=database() and table_name like 'tabCash Receipt%'")],
	}


def run_role_matrix():
	"""Check the page's accounting roles with temporary users and drafts."""
	roles = ("Accounts User", "Accounts Manager", "Employee")
	emails = {role: f"cash-receipt-role-{role.lower().replace(' ', '-')}@example.invalid" for role in roles}
	baseline = _balances()
	results = {}
	created = []
	frappe.set_user("Administrator")
	frappe.db.savepoint("cash_receipt_role_matrix")
	try:
		for role in roles:
			email = emails[role]
			user = frappe.get_doc({
				"doctype": "User", "email": email, "first_name": "Cash Receipt Permission Test",
				"enabled": 1, "user_type": "System User", "send_welcome_email": 0,
				"roles": [{"role": role}],
			})
			user.insert(ignore_permissions=True)
			frappe.set_user(email)
			permissions = {
				f"{doctype}:{permission}": bool(frappe.has_permission(doctype, permission, name))
				for doctype, permission, name in (
					("Company", "read", COMPANY), ("Account", "read", CASH),
					("Customer", "read", CUSTOMER), ("Sales Invoice", "read", INVOICES[0]),
					("Journal Entry", "create", None), ("Payment Entry", "create", None),
				)
			}
			try:
				context = receipt.get_page_context()
				page = {"allowed": True, "default_cash": context.get("cash_account")}
			except Exception as exc:
				page = {"allowed": False, "error_type": type(exc).__name__}
			base = dict(
				company=COMPANY, posting_date=frappe.utils.nowdate(), cash_account=CASH,
				counterpart_account=INCOME, amount="1", narration="Rollback-safe role check",
			)
			drafts = {}
			for kind, values in (
				("income", base),
				("customer_advance", {**base, "counterpart_account": DEBTORS, "customer": CUSTOMER, "allocations": []}),
				("customer_allocated", {**base, "counterpart_account": DEBTORS, "customer": CUSTOMER, "amount": "125", "allocations": [{"invoice": INVOICES[0], "amount": "60"}, {"invoice": INVOICES[1], "amount": "40"}]}),
			):
				try:
					voucher = receipt.save_cash_receipt_draft(**values)
					created.append(voucher)
					drafts[kind] = {"allowed": True, "doctype": voucher["doctype"], "docstatus": voucher["docstatus"]}
				except Exception as exc:
					drafts[kind] = {"allowed": False, "error_type": type(exc).__name__}
			try:
				invoice_names = {row["invoice"] for row in receipt.get_open_invoices(COMPANY, DEBTORS, CUSTOMER)}
				invoice_list = {"allowed": True, "selected_invoices_visible": all(name in invoice_names for name in INVOICES)}
			except Exception as exc:
				invoice_list = {"allowed": False, "error_type": type(exc).__name__}
			results[role] = {"permissions": permissions, "page": page, "drafts": drafts, "invoice_list": invoice_list}
			frappe.set_user("Administrator")
	finally:
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="cash_receipt_role_matrix")
		for email in emails.values():
			frappe.clear_cache(user=email)
	results["cleanup"] = {
		"temporary_users_exist": {role: bool(frappe.db.exists("User", email)) for role, email in emails.items()},
		"drafts_exist": {row["name"]: bool(frappe.db.exists(row["doctype"], row["name"])) for row in created},
		"gl_rows": {row["name"]: len(_gl(row["doctype"], row["name"])) for row in created},
		"invoice_balances_unchanged": _balances() == baseline,
	}
	return results
