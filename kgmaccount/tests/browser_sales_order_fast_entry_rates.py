"""Check Manual bill rates and Save Draft navigation in the fast-entry page."""

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
		page.wait("document.querySelector('#kgm-template') && document.querySelector('#kgm-manual-item-wrap input')")
		page.wait("document.querySelector('#kgm-date-control input').value && document.querySelector('#kgm-delivery-date-control input').value")
		initial_dates = page.eval("[document.querySelector('#kgm-date-control input').value, document.querySelector('#kgm-delivery-date-control input').value]")
		assert page.eval("document.querySelector('#kgm-add-entry').innerText.includes('Enter') && document.querySelector('#kgm-add-entry').innerText.includes('Ctrl+Enter')")
		assert page.eval("document.querySelector('#kgm-save').innerText.includes('Ctrl+S')")
		page.eval("""(() => {
			const originalCall = frappe.call;
			window.fastEntrySaves = [];
			frappe.call = function(options) {
				if (options.method.endsWith('.preview_entry')) {
					const entry = options.args.entry;
					const rows = [entry.stone, ...(entry.operations || [])].map(row => ({
						...row, qty: Number(row.qty) || 2,
						amount: (Number(row.qty) || 2) * Number(row.rate || 0),
					}));
					options.callback?.({message: {rows}});
					options.always?.();
					return;
				}
				if (options.method.endsWith('.save_sales_order')) {
					window.fastEntrySaves.push(options.args);
					options.callback?.({message: {name: 'TEST-SO-1'}});
					options.always?.();
					return;
				}
				return originalCall.apply(this, arguments);
			};
		})()""")
		page.eval("$('#kgm-template').val('MANUAL').trigger('change')")
		page.eval("$('#kgm-manual-item-wrap input').val('Adhunik Brown').trigger('change')")
		page.eval("$('#kgm-customer-control input').val('Stone Galaxy Rahul').trigger('change'); $('#kgm-cash-customer-control input').val('Cash Customer').trigger('change'); $('#kgm-phone-control input').val('1234567890').trigger('change')")
		page.wait("document.querySelectorAll('#kgm-operation option').length > 1")
		work = page.eval("document.querySelector('#kgm-operation option:nth-child(2)').value")
		assert work, "No work item available for Manual entry"

		page.eval("$('#kgm-sqft').val('20').trigger('input'); $('#kgm-finish').val('Fine').trigger('change')")
		page.eval(f"$('#kgm-operation').val({json.dumps(work)}).trigger('change'); $('#kgm-operation-rate').val('10')")
		page.eval("$('#kgm-rate').val('12'); $('#kgm-add-entry').click(); true")
		page.wait("document.querySelectorAll('#kgm-preview-body tr').length === 2")
		assert page.eval("document.querySelector('#kgm-preview-body tr').cells[8].innerText.trim()") == "12"
		assert page.eval("document.querySelector('#kgm-template').value === 'MANUAL' && document.querySelector('#kgm-manual-item-wrap input').value === 'Adhunik Brown'")
		assert page.eval("['#kgm-height', '#kgm-width', '#kgm-sqft', '#kgm-rate', '#kgm-operation-rate'].every(selector => document.querySelector(selector).value === '')")
		assert page.eval("document.querySelector('#kgm-quantity').value === '1' && document.querySelector('#kgm-finish').value === '' && document.querySelector('#kgm-operation').value === ''")
		assert page.eval("document.querySelector('#kgm-customer-control input').value === 'Stone Galaxy Rahul' && document.querySelector('#kgm-cash-customer-control input').value === 'Cash Customer' && document.querySelector('#kgm-phone-control input').value === '1234567890'")
		assert page.eval("[document.querySelector('#kgm-date-control input').value, document.querySelector('#kgm-delivery-date-control input').value]") == initial_dates
		page.eval("document.querySelector('#kgm-manual-item-wrap input').focus(); document.querySelector('#kgm-height').focus(); true")
		page.wait("document.querySelector('#kgm-rate').value === '12'")
		page.eval(f"$('#kgm-operation').val({json.dumps(work)}).trigger('change')")
		assert page.eval("document.querySelector('#kgm-operation-rate').value") == "10"

		page.eval("$('#kgm-sqft').val('30').trigger('input'); $('#kgm-rate').val('15'); $('#kgm-operation-rate').val('11')")
		page.eval("$('#kgm-add-entry').click()")
		page.wait("document.querySelectorAll('#kgm-preview-body tr').length === 4")
		assert page.eval("document.querySelector('#kgm-rate').value === ''")
		page.eval("document.querySelector('#kgm-manual-item-wrap input').focus(); document.querySelector('#kgm-height').focus(); true")
		page.wait("document.querySelector('#kgm-rate').value === '15'")
		rates = page.eval("Array.from(document.querySelectorAll('#kgm-preview-body tr')).map(row => row.cells[8].innerText.trim())")
		assert rates == ["15", "11", "15", "11"], rates
		page.eval("document.querySelector('.kgm-edit-entry').click()")
		assert page.eval("document.querySelector('#kgm-add-entry .kgm-action-label').innerText === 'Update Entry'")
		page.eval("document.querySelector('#kgm-cancel-edit').click()")

		page.eval("$('#kgm-tax-charge-type').val('Actual').trigger('change'); $('#kgm-date-control input').val('2040-01-01').trigger('change'); $('#kgm-delivery-date-control input').val('2040-02-01').trigger('change'); true")
		page.press_ctrl_s()
		page.wait("window.fastEntrySaves.length === 1")
		assert page.eval("location.pathname.endsWith('/app/sales-order-fast-entry')")
		assert page.eval("document.querySelector('#kgm-preview-body').innerText.includes('No entries yet.')")
		assert page.eval("window.fastEntrySaves[0].entries.length") == 2
		assert page.eval("window.fastEntrySaves[0].entries.flatMap(entry => entry.rows.map(row => row.rate))") == [15, 11, 15, 11]
		page.wait(f"JSON.stringify([document.querySelector('#kgm-date-control input').value, document.querySelector('#kgm-delivery-date-control input').value]) === JSON.stringify({json.dumps(initial_dates)})")
		assert page.eval("[document.querySelector('#kgm-date-control input').value, document.querySelector('#kgm-delivery-date-control input').value]") == initial_dates
		assert page.eval("document.querySelector('#kgm-template').value === 'KOTA' && document.querySelector('#kgm-manual-item-wrap input').value === '' && document.querySelector('#kgm-finish').value === ''")
		assert page.eval("document.querySelector('#kgm-customer-control input').value === '' && document.querySelector('#kgm-cash-customer-control input').value === '' && document.querySelector('#kgm-phone-control input').value === ''")
		assert page.eval("document.querySelector('#kgm-tax-charge-type').value === 'On Net Total' && document.querySelector('#kgm-tax-rate').value === '' && document.querySelector('#kgm-tax-amount').value === ''")
		page.eval("$('#kgm-height').val('24').trigger('input'); $('#kgm-width').val('24').trigger('input'); $('#kgm-quantity').val('2').trigger('input'); $('#kgm-finish').val('DP').trigger('change'); $('#kgm-rate').val('99'); $('#kgm-add-entry').click(); true")
		page.wait("document.querySelectorAll('#kgm-preview-body tr').length === 1")
		assert page.eval("document.querySelector('#kgm-template').value === 'KOTA' && document.querySelector('#kgm-finish').value === '' && document.querySelector('#kgm-rate').value === '' && document.querySelector('#kgm-quantity').value === '1'")
		print(json.dumps({"work": work, "rates": rates, "saved_on_page": True}))
	finally:
		page.close()


if __name__ == "__main__":
	main()
