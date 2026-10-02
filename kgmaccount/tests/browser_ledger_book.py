"""Browser check for the visible General Ledger Account Book."""

import json

from kgmaccount.tests.browser_cash_receipt import Browser


def main():
	password = input().rstrip("\n")
	page = Browser()
	try:
		page.navigate("/login")
		credentials = json.dumps({"usr": "Administrator", "pwd": password})
		login = page.eval(
			f"fetch('/api/method/login', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:new URLSearchParams({credentials})}}).then(r=>r.status)"
		)
		assert login == 200, f"Dev login failed: HTTP {login}"
		page.navigate("/app/ledger-book")
		page.wait("document.querySelector('#kgm-ledger-list') && document.querySelectorAll('#kgm-ledger-list .kgm-ledger-option').length >= 100", seconds=30)
		assert page.eval("document.querySelector('#kgm-ledger-picker').offsetParent !== null")
		assert page.eval("document.querySelector('#kgm-ledger-report').offsetParent === null")
		assert page.eval("getComputedStyle(document.querySelector('#page-ledger-book .page-head')).display === 'none'")
		assert page.eval("document.querySelectorAll('#kgm-ledger-actions [data-new-doctype]').length >= 1")
		layout = page.eval("({viewport: innerHeight, ledger: document.querySelector('.kgm-ledger').clientHeight, list: document.querySelector('#kgm-ledger-list').clientHeight, listScroll: document.querySelector('#kgm-ledger-list').scrollHeight})")
		assert layout["ledger"] <= layout["viewport"] and layout["listScroll"] > layout["list"], layout
		accounts = page.eval("Array.from(document.querySelectorAll('#kgm-ledger-list .kgm-ledger-option strong')).map(row=>row.innerText)")
		assert {"Cash", "Auto", "Truck", "A G L"}.issubset(set(accounts)), accounts
		assert not {"Current Assets", "Direct Expenses", "Indirect Expenses"}.intersection(set(accounts)), accounts
		assert not page.eval("Array.from(document.querySelectorAll('#kgm-ledger-list .kgm-ledger-option')).some(row=>row.innerText.includes('Account Group'))")
		assert page.eval("Array.from(document.querySelectorAll('#kgm-ledger-list .kgm-ledger-option')).some(row=>row.querySelector('strong')?.innerText==='A G L' && row.innerText.includes('Debtor'))")
		page.eval("$('#kgm-ledger-search').val('Cash').trigger('input')")
		keyboard_state = page.eval("({value:document.querySelector('#kgm-ledger-search').value,count:document.querySelectorAll('#kgm-ledger-list .kgm-ledger-option').length,active:document.querySelector('#kgm-ledger-list .kgm-ledger-option.active')?.innerText})")
		assert keyboard_state["active"], keyboard_state
		page.eval("$('#kgm-ledger-search').trigger($.Event('keydown',{key:'Enter'}))")
		page.wait("location.pathname.includes('/app/ledger-book/') && document.querySelector('#kgm-ledger-output .kgm-ledger-table') && document.querySelector('#kgm-ledger-output').innerText.includes('Opening Balance')", seconds=30)
		assert page.eval("document.querySelector('#kgm-ledger-picker').offsetParent === null")
		assert page.eval("document.querySelector('#kgm-ledger-report').offsetParent !== null")
		assert page.eval("document.querySelector('#kgm-ledger-actions').offsetParent === null")
		assert page.eval("getComputedStyle(document.querySelector('.kgm-ledger-table th')).position === 'sticky'")
		assert page.eval("document.querySelector('.kgm-tally-totals').innerText.includes('Current Total') && document.querySelector('.kgm-tally-totals').innerText.includes('Closing Balance')")
		assert page.eval("document.querySelectorAll('.kgm-ledger-row').length > 2 && document.querySelector('.kgm-ledger-row.active')?.dataset.rowIndex === '0'")
		page.eval("$(document).trigger($.Event('keydown',{key:'ArrowDown'}))")
		assert page.eval("document.querySelector('.kgm-ledger-row.active')?.dataset.rowIndex === '1'")
		page.eval("window._ledgerSetRoute=frappe.set_route; window._ledgerOpened=null; frappe.set_route=function(){window._ledgerOpened=Array.from(arguments)}; $(document).trigger($.Event('keydown',{key:'Enter'})); frappe.set_route=window._ledgerSetRoute")
		assert page.eval("window._ledgerOpened?.[0] === 'Form' && Boolean(window._ledgerOpened?.[1]) && Boolean(window._ledgerOpened?.[2])")
		page.eval("$('.kgm-ledger-row[data-row-index=2]').trigger('mouseenter')")
		assert page.eval("document.querySelector('.kgm-ledger-row.active')?.dataset.rowIndex === '2'")
		page.eval("window._ledgerOpened=null; frappe.set_route=function(){window._ledgerOpened=Array.from(arguments)}; document.querySelector('.kgm-ledger-row.active').click(); frappe.set_route=window._ledgerSetRoute")
		assert page.eval("window._ledgerOpened?.[0] === 'Form' && Boolean(window._ledgerOpened?.[1]) && Boolean(window._ledgerOpened?.[2])")
		page.eval("$(document).trigger($.Event('keydown',{key:'F2'}))")
		assert page.eval("document.querySelector('#kgm-ledger-period-editor').offsetParent !== null")
		page.eval("$(document).trigger($.Event('keydown',{key:'Escape'}))")
		assert page.eval("document.querySelector('#kgm-ledger-period-editor').offsetParent === null")
		assert page.eval("location.pathname.includes('/app/ledger-book/')")
		page.eval("$(document).trigger($.Event('keydown',{key:'Escape'}))")
		page.wait("location.pathname === '/app/ledger-book' && document.querySelector('#kgm-ledger-picker').offsetParent !== null", seconds=10)
		assert page.eval("document.querySelector('#kgm-ledger-search').value === 'Cash'")
		print(json.dumps({"account_count": len(accounts), "cash_statement_visible": True, "debtors_visible": True, "groups_hidden": True, "layout": layout}))
	finally:
		page.close()


if __name__ == "__main__":
	main()
