"""Browser regression checks for account Link selection and Tab navigation."""

import json
import time

from kgmaccount.tests.browser_cash_receipt import Browser


def main():
	password = input().rstrip("\n")
	page = Browser()
	try:
		page.navigate("/login")
		credentials = json.dumps({"usr": "Administrator", "pwd": password})
		assert page.eval(f"fetch('/api/method/login', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:new URLSearchParams({credentials})}}).then(r=>r.status)") == 200
		results = {}
		for route, field, query, expected, next_field in (
			("cash-receipt-fast-entry", "cash_account", "IDBI BANK 6842", "IDBI BANK 6842 - KGAM", "customer"),
			("cash-receipt-fast-entry", "counterpart_account", "IDBI BANK 6842", "IDBI BANK 6842 - KGAM", "kgm-receipt-amount"),
			("payment-fast-entry", "source_account", "IDBI BANK 6842", "IDBI BANK 6842 - KGAM", "customer"),
			("payment-fast-entry", "counterpart_account", "Discount Allowed", "Discount Allowed - KGAM", "kgm-fast-amount"),
		):
			page.navigate(f"/app/{route}")
			page.wait("document.querySelector('[data-fieldname=counterpart_account] input') && document.querySelector('[data-fieldname=source_account] input, [data-fieldname=cash_account] input')?.value === 'Cash - KGAM'")
			page.eval(f"{{const input=document.querySelector('[data-fieldname={field}] input'); input.focus(); input.value=''; input.dispatchEvent(new Event('input',{{bubbles:true}}));}}")
			page.call("Input.insertText", {"text": query})
			page.wait(f"document.querySelector('[data-fieldname={field}] .awesomplete ul:not([hidden]) [aria-selected=true]')")
			before = page.eval(f"({{field:document.activeElement?.closest('[data-fieldname]')?.getAttribute('data-fieldname'),value:document.querySelector('[data-fieldname={field}] input').value,selected:document.querySelector('[data-fieldname={field}] .awesomplete [aria-selected=true]')?.textContent}})")
			page.press_tab()
			page.wait(f"document.querySelector('[data-fieldname={field}] input')?.value === {json.dumps(expected)}")
			time.sleep(1)
			after = page.eval(f"({{field:document.activeElement?.closest('[data-fieldname]')?.getAttribute('data-fieldname'),id:document.activeElement?.id,value:document.querySelector('[data-fieldname={field}] input').value}})")
			assert (after.get("field") or after.get("id")) == next_field and after["value"] == expected, (route, field, before, after)
			results[f"{route}:{field}"] = {"before": before, "after": after}
		for route, amount_id, narration_id, save_id in (
			("cash-receipt-fast-entry", "kgm-receipt-amount", "kgm-receipt-narration", "kgm-receipt-save"),
			("payment-fast-entry", "kgm-fast-amount", "kgm-fast-narration", "kgm-fast-save"),
		):
			page.navigate(f"/app/{route}")
			page.wait("document.querySelector('[data-fieldname=company] input') && document.querySelector('[data-fieldname=source_account] input, [data-fieldname=cash_account] input')?.value === 'Cash - KGAM'")
			page.eval("document.querySelector('[data-fieldname=company] input').focus()")
			order = ["company"]
			for _ in range(7):
				page.press_tab()
				order.append(page.eval("document.activeElement?.closest('[data-fieldname]')?.getAttribute('data-fieldname') || document.activeElement?.id"))
			expected_order = ["company", "posting_date", "cash_account" if route == "cash-receipt-fast-entry" else "source_account", "customer", "counterpart_account", amount_id, narration_id, save_id]
			assert order == expected_order, (route, order)
			page.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9, "modifiers": 8})
			page.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9, "modifiers": 0})
			assert page.eval("document.activeElement?.id") == narration_id
			results[f"{route}:full_order"] = order
		print(json.dumps(results))
	finally:
		page.close()


if __name__ == "__main__":
	main()
