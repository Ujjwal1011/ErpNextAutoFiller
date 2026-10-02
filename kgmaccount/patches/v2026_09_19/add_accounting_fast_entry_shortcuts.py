"""Add the accounting fast-entry pages to the existing Auto Filler workspace."""

import json

import frappe


PAGES = (
	("cash-expense-fast-entry", "Cash Expense Fast Entry"),
	("supplier-payment-fast-entry", "Supplier Payment Fast Entry"),
	("cash-bank-transfer-fast-entry", "Cash / Bank Transfer Fast Entry"),
	("bank-receipt-fast-entry", "Bank Receipt Fast Entry"),
)


def execute():
	if not frappe.db.exists("Workspace", "Auto Filler"):
		return
	workspace = frappe.get_doc("Workspace", "Auto Filler")
	content = json.loads(workspace.content or "[]")
	changed = False
	for route, label in PAGES:
		block_id = route.replace("-", "_") + "_shortcut"
		if not any(block.get("id") == block_id for block in content):
			content.append({"id": block_id, "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
			changed = True
		if not any(row.label == label for row in workspace.links):
			workspace.append("links", {"label": label, "link_type": "Page", "link_to": route, "type": "Link"})
			changed = True
		if not any(row.label == label for row in workspace.shortcuts):
			workspace.append("shortcuts", {"label": label, "type": "Page", "link_to": route})
			changed = True
	if not changed:
		return
	workspace.content = json.dumps(content, separators=(",", ":"))
	developer_mode = frappe.conf.developer_mode
	try:
		frappe.conf.developer_mode = 0
		workspace.save()
	finally:
		frappe.conf.developer_mode = developer_mode
