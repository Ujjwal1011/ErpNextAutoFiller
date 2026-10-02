"""Browser checks for the consolidated Payment Fast Entry page."""

import json

from kgmaccount.tests.browser_cash_receipt import Browser


def main():
	password = input().rstrip("\n")
	page = Browser()
	try:
		page.navigate("/login")
		credentials = json.dumps({"usr": "Administrator", "pwd": password})
		login = page.eval(f"fetch('/api/method/login', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:new URLSearchParams({credentials})}}).then(r=>r.status)")
		assert login == 200, f"Dev login failed: HTTP {login}"
		page.navigate("/app/auto-filler")
		page.wait("document.body && document.body.innerText.includes('Payment Fast Entry')")
		shortcuts = page.eval("Array.from(document.querySelectorAll('[shortcut_name]')).map(e=>e.getAttribute('shortcut_name')).filter(name=>name && name.includes('Fast Entry'))")
		assert "Cash Receipt Fast Entry" in shortcuts and "Payment Fast Entry" in shortcuts, shortcuts
		assert not any(name in shortcuts for name in ("Cash Expense Fast Entry", "Supplier Payment Fast Entry", "Cash / Bank Transfer Fast Entry", "Bank Receipt Fast Entry")), shortcuts

		page.navigate("/app/payment-fast-entry")
		page.wait("document.querySelector('#kgm-fast-amount') && document.querySelectorAll('.kgm-fast-switch a').length === 2")
		page.wait("document.querySelector('[data-fieldname=source_account] input')?.value === 'Cash - KGAM'")
		labels = page.eval("Array.from(document.querySelectorAll('.kgm-fast-entry label')).map(label=>label.innerText)")
		assert "Paid From Cash / Bank" in labels and "Paid To Account" in labels and "Paid To Customer" in labels, labels
		assert "Bank Reference No" not in labels and "Bank Reference Date" not in labels, labels
		page.eval("{const a=document.querySelector('[data-fieldname=counterpart_account] input'); a.value='Discount Allowed - KGAM'; a.dispatchEvent(new Event('change',{bubbles:true}));}")
		page.wait("document.querySelector('[data-fieldname=counterpart_account] input')?.value === 'Discount Allowed - KGAM'")
		page.eval("document.querySelector('#kgm-fast-amount').value='10'; document.querySelector('#kgm-fast-amount').dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('#kgm-fast-narration').value='BROWSER OTHER FAST ENTRY TEST - DELETE'; document.querySelector('#kgm-fast-amount').focus();")
		preview = page.eval("({debit:document.querySelector('#kgm-fast-debit').innerText,credit:document.querySelector('#kgm-fast-credit').innerText})")
		page.press_ctrl_s(); page.press_ctrl_s()
		page.wait("location.pathname.endsWith('/app/payment-fast-entry') && document.querySelector('#kgm-fast-status a')?.getAttribute('href')?.includes('/app/journal-entry/') && document.querySelector('#kgm-fast-amount').value === ''", seconds=30)
		saved = page.eval("({link:document.querySelector('#kgm-fast-status a').getAttribute('href'),target:document.querySelector('#kgm-fast-status a').target,source:document.querySelector('[data-fieldname=source_account] input').value,counterpart:document.querySelector('[data-fieldname=counterpart_account] input').value})")
		page.eval("{const c=document.querySelector('[data-fieldname=customer] input'); c.value='Hanuman Granite'; c.dispatchEvent(new Event('change',{bubbles:true}));}")
		page.wait("document.querySelector('[data-fieldname=counterpart_account] input')?.value === 'Debtors - KGAM' && document.querySelector('[data-fieldname=customer] input')?.value === 'Hanuman Granite'")
		page.eval("document.querySelector('#kgm-fast-amount').value='35'; document.querySelector('#kgm-fast-amount').dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('#kgm-fast-narration').value='BROWSER OTHER FAST ENTRY TEST - DELETE';")
		customer_preview = page.eval("({debit:document.querySelector('#kgm-fast-debit').innerText,credit:document.querySelector('#kgm-fast-credit').innerText,party:document.querySelector('#kgm-fast-debit-account').innerText,invoice_visible:document.querySelector('#kgm-fast-invoice-section').style.display !== 'none'})")
		assert customer_preview["debit"] == customer_preview["credit"] and "Hanuman Granite" in customer_preview["party"] and not customer_preview["invoice_visible"], customer_preview
		page.eval("document.querySelector('#kgm-fast-save').click(); document.querySelector('#kgm-fast-save').click();")
		page.wait("document.querySelector('#kgm-fast-status a')?.getAttribute('href')?.includes('/app/journal-entry/') && document.querySelector('#kgm-fast-amount').value === '' && document.querySelector('[data-fieldname=customer] input').value === ''", seconds=30)
		customer_saved = page.eval("({link:document.querySelector('#kgm-fast-status a').getAttribute('href'),source:document.querySelector('[data-fieldname=source_account] input').value,focused:document.activeElement?.closest('[data-fieldname]')?.getAttribute('data-fieldname')})")
		page.navigate(customer_saved["link"])
		page.wait("window.cur_frm && cur_frm.doc?.doctype === 'Journal Entry' && cur_frm.doc?.name === location.pathname.split('/').pop()", seconds=30)
		customer_voucher = page.eval("({doctype:cur_frm.doc.doctype,docstatus:cur_frm.doc.docstatus,party_rows:cur_frm.doc.accounts.filter(row=>row.party_type==='Customer' && row.party==='Hanuman Granite').map(row=>({account:row.account,debit:row.debit_in_account_currency,reference:row.reference_name}))})")
		assert customer_voucher["doctype"] == "Journal Entry" and customer_voucher["docstatus"] == 0 and len(customer_voucher["party_rows"]) == 1 and customer_voucher["party_rows"][0]["account"] == "Debtors - KGAM" and customer_voucher["party_rows"][0]["debit"] == 35 and not customer_voucher["party_rows"][0].get("reference"), customer_voucher
		page.navigate("/app/payment-fast-entry")
		page.wait("document.querySelector('#kgm-fast-amount') && document.querySelector('[data-fieldname=source_account] input')?.value === 'Cash - KGAM'")
		page.eval("{const source=document.querySelector('[data-fieldname=source_account] input'); source.value='IDBI BANK 6842 - KGAM'; source.dispatchEvent(new Event('change',{bubbles:true})); const account=document.querySelector('[data-fieldname=counterpart_account] input'); account.value='Suspense Account - KGAM'; account.dispatchEvent(new Event('change',{bubbles:true})); document.querySelector('#kgm-fast-amount').value='20000'; document.querySelector('#kgm-fast-amount').dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('#kgm-fast-narration').value='BROWSER OTHER FAST ENTRY TEST - DELETE';}")
		page.wait("document.querySelector('[data-fieldname=source_account] input')?.value === 'IDBI BANK 6842 - KGAM' && document.querySelector('[data-fieldname=counterpart_account] input')?.value === 'Suspense Account - KGAM'")
		page.press_ctrl_s()
		page.wait("document.querySelector('#kgm-fast-status a')?.getAttribute('href')?.includes('/app/journal-entry/') && document.querySelector('#kgm-fast-amount').value === ''", seconds=30)
		bank_saved = page.eval("({link:document.querySelector('#kgm-fast-status a').getAttribute('href'),reference_field_count:document.querySelectorAll('#kgm-fast-reference-no, #kgm-fast-reference-date').length})")
		page.navigate(bank_saved["link"])
		page.wait("window.cur_frm && cur_frm.doc?.doctype === 'Journal Entry' && cur_frm.doc?.name === location.pathname.split('/').pop()", seconds=30)
		bank_voucher = page.eval("({doctype:cur_frm.doc.doctype,voucher_type:cur_frm.doc.voucher_type,docstatus:cur_frm.doc.docstatus,posting_date:cur_frm.doc.posting_date,reference_date:cur_frm.doc.cheque_date,reference_no:cur_frm.doc.cheque_no,accounts:cur_frm.doc.accounts.map(row=>({account:row.account,debit:row.debit_in_account_currency,credit:row.credit_in_account_currency}))})")
		assert bank_saved["reference_field_count"] == 0 and bank_voucher["voucher_type"] == "Bank Entry" and bank_voucher["docstatus"] == 0 and bank_voucher["reference_no"].startswith("AUTO-PAY-") and bank_voucher["reference_date"] == bank_voucher["posting_date"] and any(row["account"] == "Suspense Account - KGAM" and row["debit"] == 20000 for row in bank_voucher["accounts"]) and any(row["account"] == "IDBI BANK 6842 - KGAM" and row["credit"] == 20000 for row in bank_voucher["accounts"]), bank_voucher
		page.navigate("/app/payment-fast-entry")
		page.wait("document.querySelector('#kgm-fast-amount')")
		shortcut_labels = page.eval("Array.from(document.querySelectorAll('.kgm-fast-switch a')).map(link=>link.innerText)")
		assert any("Receipt" in label and "F6" in label for label in shortcut_labels) and any("Payment" in label and "F5" in label for label in shortcut_labels), shortcut_labels
		page.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "F6", "code": "F6", "windowsVirtualKeyCode": 117, "modifiers": 0})
		page.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "F6", "code": "F6", "windowsVirtualKeyCode": 117, "modifiers": 0})
		page.wait("location.pathname.endsWith('/app/cash-receipt-fast-entry') && document.querySelectorAll('.kgm-receipt-switch a').length === 2")
		page.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "F5", "code": "F5", "windowsVirtualKeyCode": 116, "modifiers": 0})
		page.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "F5", "code": "F5", "windowsVirtualKeyCode": 116, "modifiers": 0})
		page.wait("location.pathname.endsWith('/app/payment-fast-entry') && document.querySelectorAll('.kgm-fast-switch a').length === 2")
		print(json.dumps({"shortcuts": shortcuts, "preview": preview, "saved": saved, "customer_preview": customer_preview, "customer_saved": customer_saved, "customer_voucher": customer_voucher, "bank_saved": bank_saved, "bank_voucher": bank_voucher, "f6_route": "/app/cash-receipt-fast-entry", "f5_route": "/app/payment-fast-entry", "passed": preview["debit"] == preview["credit"] and saved["target"] == "_blank" and saved["source"] == "Cash - KGAM" and saved["counterpart"] == "" and customer_saved["source"] == "Cash - KGAM" and customer_saved["focused"] == "customer"}))
	finally:
		page.close()


if __name__ == "__main__":
	main()
