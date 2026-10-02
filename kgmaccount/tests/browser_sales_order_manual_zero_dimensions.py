"""Check that a Manual sales order item accepts entered Sqft with blank dimensions."""

import json

from kgmaccount.tests.browser_cash_receipt import Browser


def main():
	password = input().rstrip("\n")
	page = Browser()
	try:
		page.navigate("/login")
		credentials = json.dumps({"usr": "Administrator", "pwd": password})
		status = page.eval(
			f"fetch('/api/method/login', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:new URLSearchParams({credentials})}}).then(r=>r.status)"
		)
		assert status == 200, f"Dev login failed: HTTP {status}"
		page.navigate("/app/sales-order-fast-entry")
		page.wait("document.querySelector('#kgm-template') && document.querySelector('#kgm-manual-item-wrap input')", seconds=30)
		page.eval("$('#kgm-template').val('MANUAL').trigger('change')")
		page.eval("$('#kgm-manual-item-wrap input').val('Adhunik Brown').trigger('change')")
		page.eval("$('#kgm-sqft').val('25').trigger('input')")
		page.eval("$('#kgm-rate').val('10').trigger('input')")
		page.eval("$('#kgm-add-entry').click()")
		page.wait("document.querySelector('#kgm-preview-body tr')?.cells.length === 12 && document.querySelector('#kgm-preview-body').innerText.includes('Adhunik Brown')", seconds=30)
		row = page.eval("Array.from(document.querySelector('#kgm-preview-body tr').cells).map(cell=>cell.innerText.trim())")
		assert row[1:5] == ["Adhunik Brown", "0", "0", "1"], row
		assert row[7] == "25", row
		assert row[9] == "250", row
		print(json.dumps({"manual_item": row[1], "height": row[2], "width": row[3], "sqft": row[7], "amount": row[9]}))
	finally:
		page.close()


if __name__ == "__main__":
	main()
