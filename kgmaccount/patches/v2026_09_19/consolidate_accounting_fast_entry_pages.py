"""Keep only the Receipt and Payment fast-entry shortcuts in Auto Filler."""

import json

import frappe


OLD_LABELS = {
	"Cash Expense Fast Entry",
	"Supplier Payment Fast Entry",
	"Cash / Bank Transfer Fast Entry",
	"Bank Receipt Fast Entry",
}
OLD_ROUTES = {
	"cash-expense-fast-entry",
	"supplier-payment-fast-entry",
	"cash-bank-transfer-fast-entry",
	"bank-receipt-fast-entry",
}


def execute():
	if not frappe.db.exists("Workspace", "Auto Filler"):
		return
	workspace = frappe.get_doc("Workspace", "Auto Filler")
	content = json.loads(workspace.content or "[]")
	content = [
		block for block in content
		if block.get("data", {}).get("shortcut_name") not in OLD_LABELS
		and block.get("data", {}).get("shortcut_name") != "Payment Fast Entry"
	]
	content.append({"id": "payment_fast_entry_shortcut", "type": "shortcut", "data": {"shortcut_name": "Payment Fast Entry", "col": 3}})
	workspace.set("links", [row for row in workspace.links if row.label not in OLD_LABELS and row.label != "Payment Fast Entry"])
	workspace.append("links", {"label": "Payment Fast Entry", "link_type": "Page", "link_to": "payment-fast-entry", "type": "Link"})
	workspace.set("shortcuts", [row for row in workspace.shortcuts if row.label not in OLD_LABELS and row.label != "Payment Fast Entry"])
	workspace.append("shortcuts", {"label": "Payment Fast Entry", "type": "Page", "link_to": "payment-fast-entry"})
	workspace.content = json.dumps(content, separators=(",", ":"))
	developer_mode = frappe.conf.developer_mode
	try:
		frappe.conf.developer_mode = 0
		workspace.save()
	finally:
		frappe.conf.developer_mode = developer_mode
