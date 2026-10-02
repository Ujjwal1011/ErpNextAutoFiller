"""Minimal Chrome DevTools browser check; reads the dev password from stdin."""

import base64
import json
import os
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


class Browser:
	def __init__(self):
		self.profile = tempfile.TemporaryDirectory(prefix="cash-receipt-browser-")
		self.proc = subprocess.Popen(
			[
				"chromium-headless-shell", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
				"--remote-debugging-port=0", "--remote-allow-origins=*", f"--user-data-dir={self.profile.name}",
				"about:blank",
			],
			stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
		)
		port_file = Path(self.profile.name) / "DevToolsActivePort"
		for _ in range(100):
			if port_file.exists():
				break
			if self.proc.poll() is not None:
				raise RuntimeError("Chromium exited before DevTools opened")
			time.sleep(0.1)
		port = port_file.read_text().splitlines()[0]
		request = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?about:blank", method="PUT")
		ws_url = json.load(urllib.request.urlopen(request))["webSocketDebuggerUrl"]
		self.sock = socket.create_connection(("127.0.0.1", int(port)))
		self.sock.settimeout(30)
		key = base64.b64encode(os.urandom(16)).decode()
		path = ws_url.split(f"127.0.0.1:{port}", 1)[1]
		self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nOrigin: http://127.0.0.1\r\n\r\n").encode())
		handshake = self.sock.recv(4096)
		assert b"HTTP/1.1 101" in handshake, handshake.decode(errors="replace")
		self.next_id = 0
		self.call("Page.enable")
		self.call("Runtime.enable")
		width, height = map(int, os.environ.get("CASH_RECEIPT_VIEWPORT", "1440x900").split("x"))
		self.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})

	def _read(self, n):
		data = b""
		while len(data) < n:
			data += self.sock.recv(n - len(data))
		return data

	def call(self, method, params=None):
		self.next_id += 1
		id_ = self.next_id
		payload = json.dumps({"id": id_, "method": method, "params": params or {}}).encode()
		mask = os.urandom(4)
		header = bytes([0x81, 0x80 | len(payload)]) if len(payload) < 126 else bytes([0x81, 0x80 | 126]) + struct.pack("!H", len(payload))
		self.sock.sendall(header + mask + bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload)))
		while True:
			head = self._read(2)
			length = head[1] & 0x7f
			if length == 126:
				length = struct.unpack("!H", self._read(2))[0]
			elif length == 127:
				length = struct.unpack("!Q", self._read(8))[0]
			if head[1] & 0x80:
				response_mask = self._read(4)
			else:
				response_mask = None
			data = self._read(length)
			if response_mask:
				data = bytes(byte ^ response_mask[index % 4] for index, byte in enumerate(data))
			if (head[0] & 0x0f) != 1:
				continue
			message = json.loads(data)
			if message.get("id") == id_:
				if "error" in message:
					raise RuntimeError(message["error"])
				return message.get("result", {})

	def eval(self, expression):
		result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
		if "exceptionDetails" in result:
			raise RuntimeError(result["exceptionDetails"].get("text"))
		return result.get("result", {}).get("value")

	def navigate(self, path):
		self.call("Page.navigate", {"url": "http://frontend:8080" + path})
		self.wait("document.readyState === 'complete'")

	def press_ctrl_s(self):
		self.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Control", "code": "ControlLeft", "windowsVirtualKeyCode": 17, "modifiers": 2})
		self.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "s", "code": "KeyS", "windowsVirtualKeyCode": 83, "modifiers": 2})
		self.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "s", "code": "KeyS", "windowsVirtualKeyCode": 83, "modifiers": 2})
		self.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Control", "code": "ControlLeft", "windowsVirtualKeyCode": 17, "modifiers": 0})

	def press_tab(self):
		self.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
		self.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})

	def wait(self, expression, seconds=25):
		until = time.time() + seconds
		while time.time() < until:
			try:
				value = self.eval(expression)
				if value:
					return value
			except RuntimeError:
				pass
			time.sleep(0.2)
		raise TimeoutError(expression)

	def close(self):
		self.sock.close()
		self.proc.terminate()
		self.proc.wait(timeout=10)
		self.profile.cleanup()


def main():
	password = input().rstrip("\n")
	page = Browser()
	try:
		page.navigate("/login")
		credentials = json.dumps({"usr": "Administrator", "pwd": password})
		login = page.eval(f"fetch('/api/method/login', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:new URLSearchParams({credentials})}}).then(r=>r.status)")
		assert login == 200, f"Dev login failed: HTTP {login}"
		page.navigate("/app/auto-filler")
		page.wait("document.body && document.body.innerText.includes('Cash Receipt Fast Entry')")
		shortcut = page.eval("document.querySelector('[shortcut_name=\"Cash Receipt Fast Entry\"] [role=link]')?.getAttribute('aria-label')")
		assert shortcut, "Auto Filler shortcut missing"
		page.eval("document.querySelector('[shortcut_name=\"Cash Receipt Fast Entry\"] [role=link]').click()")
		page.wait("location.pathname.endsWith('/app/cash-receipt-fast-entry') && document.querySelector('#kgm-receipt-amount')")
		page.wait("document.querySelector('[data-fieldname=cash_account] input')?.value === 'Cash - KGAM'")
		page.wait("document.activeElement?.closest('[data-fieldname]')?.getAttribute('data-fieldname') === 'customer'")
		initial_focus = page.eval("document.activeElement.closest('[data-fieldname]').getAttribute('data-fieldname')")
		fields = page.eval("Array.from(document.querySelectorAll('.kgm-receipt .frappe-control')).map(e=>e.getAttribute('data-fieldname')).filter(Boolean)")
		assert "reference_date" not in fields and not page.eval("Boolean(document.querySelector('#kgm-receipt-reference-no'))"), fields
		receipt_account_label = page.eval("document.querySelector('[data-fieldname=cash_account] label')?.innerText")
		default = page.eval("document.querySelector('[data-fieldname=cash_account] input').value")
		page.eval("document.querySelector('#kgm-receipt-amount').value='125'; document.querySelector('#kgm-receipt-amount').dispatchEvent(new Event('input',{bubbles:true}));")
		preview = page.eval("({debit:document.querySelector('#kgm-receipt-debit').innerText,credit:document.querySelector('#kgm-receipt-credit').innerText})")
		page.eval("{const a=document.querySelector('[data-fieldname=counterpart_account] input'); a.value='Debtors - KGAM'; a.dispatchEvent(new Event('change',{bubbles:true}));}")
		page.wait("document.querySelector('#kgm-receipt-customer-field')?.style.display !== 'none'")
		page.eval("const c=document.querySelector('[data-fieldname=customer] input'); c.value='Stone Galaxy Rahul'; c.dispatchEvent(new Event('change',{bubbles:true}));")
		page.wait("document.querySelectorAll('input[data-invoice-index]').length >= 2")
		customer_ui = page.eval("({customer_visible:document.querySelector('#kgm-receipt-customer-field').style.display!=='none',invoice_rows:document.querySelectorAll('input[data-invoice-index]').length})")
		auto_allocated = page.eval("Array.from(document.querySelectorAll('input[data-invoice-index]')).reduce((sum,input)=>sum+(Number(input.value)||0),0)")
		assert abs(auto_allocated - 125) < 0.001, auto_allocated
		fifo_first = page.eval("(() => {const rows=Array.from(document.querySelectorAll('.kgm-receipt-invoice-row')); return {invoice:rows[0].querySelector('strong').innerText,outstanding:Number(rows[0].querySelector('input').max),allocated:Number(rows[0].querySelector('input').value),other_allocated:rows.slice(1).reduce((sum,row)=>sum+(Number(row.querySelector('input').value)||0),0)}})()")
		assert fifo_first["invoice"] == "ACC-SINV-2026-00114" and fifo_first["allocated"] == 125 and fifo_first["other_allocated"] == 0, fifo_first
		page.eval("{const input=document.querySelector('#kgm-receipt-amount'); input.value=(Number(document.querySelector('.kgm-receipt-invoice-row input').max)+25.37).toFixed(2); input.dispatchEvent(new Event('input',{bubbles:true}));}")
		split_allocation = page.eval("(() => {const inputs=Array.from(document.querySelectorAll('.kgm-receipt-invoice-row input')); return {first:Number(inputs[0].value),second:Number(inputs[1].value),later:inputs.slice(2).reduce((sum,input)=>sum+(Number(input.value)||0),0)}})()")
		assert split_allocation["first"] == fifo_first["outstanding"] and split_allocation["second"] == 25.37 and split_allocation["later"] == 0, split_allocation
		page.eval("document.querySelector('#kgm-receipt-amount').value='125'; document.querySelector('#kgm-receipt-amount').dispatchEvent(new Event('input',{bubbles:true}));")
		layout = page.eval("({viewport:innerHeight,document:document.scrollingElement.scrollHeight,viewport_width:innerWidth,document_width:document.scrollingElement.scrollWidth,form_bottom:document.querySelector('.kgm-receipt').getBoundingClientRect().bottom,scrollables:Array.from(document.querySelectorAll('*')).filter(e=>e.scrollHeight>e.clientHeight+2 && ['auto','scroll'].includes(getComputedStyle(e).overflowY)).map(e=>({class:e.className,client:e.clientHeight,scroll:e.scrollHeight})).slice(0,8)})")
		sections = page.eval("Array.from(document.querySelectorAll('.kgm-receipt > .kgm-receipt-head, .kgm-receipt > .kgm-receipt-section')).map(e=>({name:e.id||e.className,height:Math.round(e.getBoundingClientRect().height),top:Math.round(e.getBoundingClientRect().top)}))")
		page.eval("document.querySelector('[data-fieldname=company] input').focus()")
		tab_order = ["company"]
		for _ in range(15):
			page.press_tab()
			tab_order.append(page.eval("{const e=document.activeElement; e?.dataset?.invoiceIndex !== undefined ? 'invoice:'+e.closest('.kgm-receipt-invoice-row').querySelector('strong').innerText : e?.closest('[data-fieldname]')?.getAttribute('data-fieldname') || e?.id || e?.tagName}"))
		if os.environ.get("CASH_RECEIPT_INSPECT_ONLY") == "1":
			print(json.dumps({"layout": layout, "sections": sections, "initial_focus": initial_focus, "tab_order": tab_order}))
			return
		page.eval("{const a=document.querySelector('[data-fieldname=counterpart_account] input'); a.value='Sales - KGAM'; a.dispatchEvent(new Event('change',{bubbles:true}));}")
		page.wait("document.querySelector('[data-fieldname=counterpart_account] input')?.value === 'Sales - KGAM'")
		page.wait("document.querySelector('#kgm-receipt-invoice-section')?.style.display === 'none' && document.querySelector('[data-fieldname=customer] input')?.value === ''")
		server_precision_status = page.eval("fetch('/api/method/kgmaccount.auto_filler.page.cash_receipt_fast_entry.cash_receipt_fast_entry.save_cash_receipt_draft',{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':frappe.csrf_token},body:JSON.stringify({company:'Kirti Granite And Marble',posting_date:frappe.datetime.get_today(),cash_account:'Cash - KGAM',counterpart_account:'Sales - KGAM',amount:'125.000',narration:'BROWSER CASH RECEIPT TEST - DELETE'})}).then(r=>r.status)")
		server_precision_rejected = server_precision_status != 200
		page.eval("window._receiptMsgprint=frappe.msgprint; window._receiptValidation=[]; frappe.msgprint=(message)=>window._receiptValidation.push(message); document.querySelector('#kgm-receipt-amount').value='125.000'; document.querySelector('#kgm-receipt-save').click();")
		precision_rejected = page.eval("window._receiptValidation.length === 1 && location.pathname.endsWith('/app/cash-receipt-fast-entry')")
		page.eval("frappe.msgprint=window._receiptMsgprint; document.querySelector('#kgm-receipt-amount').value='125'; document.querySelector('#kgm-receipt-amount').dispatchEvent(new Event('input',{bubbles:true}));")
		page.eval("document.querySelector('#kgm-receipt-narration').value='BROWSER CASH RECEIPT TEST - DELETE';")
		page.eval("document.querySelector('#kgm-receipt-amount').focus()")
		if os.environ.get("CASH_RECEIPT_FIRST_SAVE_BUTTON") == "1":
			page.eval("document.querySelector('#kgm-receipt-save').click(); document.querySelector('#kgm-receipt-save').click();")
		else:
			page.press_ctrl_s()
			page.press_ctrl_s()
		page.wait("location.pathname.endsWith('/app/cash-receipt-fast-entry') && document.querySelector('#kgm-receipt-status a')?.getAttribute('href')?.includes('/app/journal-entry/') && document.querySelector('#kgm-receipt-amount').value === ''", seconds=30)
		journal_ready = page.eval("({path:location.pathname,voucher_link:document.querySelector('#kgm-receipt-status a').getAttribute('href'),link_target:document.querySelector('#kgm-receipt-status a').target,account:document.querySelector('[data-fieldname=counterpart_account] input').value,amount:document.querySelector('#kgm-receipt-amount').value,narration:document.querySelector('#kgm-receipt-narration').value,cash:document.querySelector('[data-fieldname=cash_account] input').value,focused:document.activeElement?.closest('[data-fieldname]')?.getAttribute('data-fieldname')})")
		page.navigate(journal_ready["voucher_link"])
		page.wait("location.pathname.includes('/app/journal-entry/')", seconds=30)
		page.wait("window.cur_frm && cur_frm.doc?.doctype === 'Journal Entry' && cur_frm.doc?.name === location.pathname.split('/').pop()", seconds=30)
		voucher = page.eval("({path:location.pathname,doctype:cur_frm.doc.doctype,name:cur_frm.doc.name,docstatus:cur_frm.doc.docstatus})")
		page.navigate("/app/cash-receipt-fast-entry")
		page.wait("document.querySelector('#kgm-receipt-amount') && document.querySelector('[data-fieldname=cash_account] input')?.value === 'Cash - KGAM'")
		page.eval("{const a=document.querySelector('[data-fieldname=counterpart_account] input'); a.value='Debtors - KGAM'; a.dispatchEvent(new Event('change',{bubbles:true}));}")
		page.wait("document.querySelector('#kgm-receipt-customer-field')?.style.display !== 'none'")
		page.eval("{const c=document.querySelector('[data-fieldname=customer] input'); c.value='Stone Galaxy Rahul'; c.dispatchEvent(new Event('change',{bubbles:true}));}")
		page.wait("document.querySelectorAll('input[data-invoice-index]').length >= 2")
		page.eval("document.querySelector('#kgm-receipt-amount').value='125'; document.querySelector('#kgm-receipt-amount').dispatchEvent(new Event('input',{bubbles:true}));")
		page.eval("document.querySelectorAll('input[data-invoice-index]').forEach(input=>input.value='');")
		for invoice, amount in [("ACC-SINV-2026-00054", "60"), ("ACC-SINV-2026-00114", "40")]:
			page.eval("{const row=Array.from(document.querySelectorAll('.kgm-receipt-invoice-row')).find(row=>row.querySelector('strong').innerText.includes(" + json.dumps(invoice) + ")); const input=row.querySelector('input'); input.value=" + json.dumps(amount) + "; input.dispatchEvent(new Event('input',{bubbles:true}));}")
		allocation_summary = page.eval("document.querySelector('#kgm-receipt-allocation-summary').innerText")
		page.eval("document.querySelector('#kgm-receipt-narration').value='BROWSER CASH RECEIPT TEST - DELETE'; document.querySelector('#kgm-receipt-narration').focus();")
		page.press_ctrl_s()
		page.press_ctrl_s()
		page.wait("location.pathname.endsWith('/app/cash-receipt-fast-entry') && document.querySelector('#kgm-receipt-status a')?.getAttribute('href')?.includes('/app/payment-entry/') && document.querySelector('#kgm-receipt-amount').value === ''", seconds=30)
		payment_ready = page.eval("({path:location.pathname,voucher_link:document.querySelector('#kgm-receipt-status a').getAttribute('href'),link_target:document.querySelector('#kgm-receipt-status a').target,account:document.querySelector('[data-fieldname=counterpart_account] input').value,customer:document.querySelector('[data-fieldname=customer] input').value,amount:document.querySelector('#kgm-receipt-amount').value,narration:document.querySelector('#kgm-receipt-narration').value,cash:document.querySelector('[data-fieldname=cash_account] input').value,invoice_count:document.querySelectorAll('input[data-invoice-index]').length,focused:document.activeElement?.closest('[data-fieldname]')?.getAttribute('data-fieldname')})")
		page.navigate(payment_ready["voucher_link"])
		page.wait("location.pathname.includes('/app/payment-entry/')", seconds=30)
		page.wait("window.cur_frm && cur_frm.doc?.doctype === 'Payment Entry' && cur_frm.doc?.name === location.pathname.split('/').pop()", seconds=30)
		payment_voucher = page.eval("({path:location.pathname,doctype:cur_frm.doc.doctype,name:cur_frm.doc.name,docstatus:cur_frm.doc.docstatus,paid_amount:cur_frm.doc.paid_amount,unallocated_amount:cur_frm.doc.unallocated_amount,references:cur_frm.doc.references.map(r=>({invoice:r.reference_name,amount:r.allocated_amount}))})")
		page.navigate("/app/cash-receipt-fast-entry")
		page.wait("document.querySelector('#kgm-receipt-amount') && document.querySelector('[data-fieldname=cash_account] input')?.value === 'Cash - KGAM'")
		page.eval("{const bank=document.querySelector('[data-fieldname=cash_account] input'); bank.value='IDBI BANK 6842 - KGAM'; bank.dispatchEvent(new Event('change',{bubbles:true})); const account=document.querySelector('[data-fieldname=counterpart_account] input'); account.value='Sales - KGAM'; account.dispatchEvent(new Event('change',{bubbles:true})); document.querySelector('#kgm-receipt-amount').value='10'; document.querySelector('#kgm-receipt-amount').dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('#kgm-receipt-narration').value='BROWSER CASH RECEIPT TEST - DELETE';}")
		page.wait("document.querySelector('[data-fieldname=cash_account] input')?.value === 'IDBI BANK 6842 - KGAM' && document.querySelector('[data-fieldname=counterpart_account] input')?.value === 'Sales - KGAM'")
		assert page.eval("document.querySelectorAll('#kgm-receipt-reference-no, #kgm-receipt-reference-date').length") == 0
		page.press_ctrl_s()
		page.wait("document.querySelector('#kgm-receipt-status a')?.getAttribute('href')?.includes('/app/journal-entry/') && document.querySelector('#kgm-receipt-amount').value === ''", seconds=30)
		bank_link = page.eval("document.querySelector('#kgm-receipt-status a').getAttribute('href')")
		page.navigate(bank_link)
		page.wait("window.cur_frm && cur_frm.doc?.doctype === 'Journal Entry' && cur_frm.doc?.name === location.pathname.split('/').pop()", seconds=30)
		bank_voucher = page.eval("({doctype:cur_frm.doc.doctype,voucher_type:cur_frm.doc.voucher_type,docstatus:cur_frm.doc.docstatus,posting_date:cur_frm.doc.posting_date,reference_date:cur_frm.doc.cheque_date,reference_no:cur_frm.doc.cheque_no})")
		assert bank_voucher["voucher_type"] == "Bank Entry" and bank_voucher["docstatus"] == 0 and bank_voucher["reference_no"].startswith("AUTO-REC-") and bank_voucher["reference_date"] == bank_voucher["posting_date"], bank_voucher
		print(json.dumps({"shortcut": shortcut, "fields": fields, "receipt_account_label": receipt_account_label, "cash_default": default, "initial_focus": initial_focus, "preview": preview, "customer_ui": customer_ui, "auto_allocated": auto_allocated, "fifo_first": fifo_first, "split_allocation": split_allocation, "layout": layout, "sections": sections, "tab_order": tab_order, "precision_rejected": precision_rejected, "server_precision_rejected": server_precision_rejected, "server_precision_status": server_precision_status, "save_method": "button twice, then Ctrl+S twice" if os.environ.get("CASH_RECEIPT_FIRST_SAVE_BUTTON") == "1" else "Ctrl+S twice for each voucher", "journal_ready_for_next": journal_ready, "saved_voucher": voucher, "allocation_summary": allocation_summary, "payment_ready_for_next": payment_ready, "saved_payment": payment_voucher, "bank_voucher": bank_voucher}))
	finally:
		page.close()


if __name__ == "__main__":
	main()
