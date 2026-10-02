"""Expose the fast-entry page without replacing site-specific workspace blocks."""

import json

import frappe


def execute():
	if not frappe.db.exists("Workspace", "Auto Filler"):
		return

	workspace = frappe.get_doc("Workspace", "Auto Filler")
	content = json.loads(workspace.content or "[]")
	changed = False
	if not any(block.get("id") == "cash_receipt_fast_entry_shortcut" for block in content):
		content.append(
			{
				"id": "cash_receipt_fast_entry_shortcut",
				"type": "shortcut",
				"data": {"shortcut_name": "Cash Receipt Fast Entry", "col": 3},
			}
		)
		workspace.content = json.dumps(content, separators=(",", ":"))
		changed = True
	if not any(row.label == "Cash Receipt Fast Entry" for row in workspace.links):
		workspace.append("links", {"label": "Accounting", "type": "Card Break"})
		workspace.append(
			"links",
			{
				"label": "Cash Receipt Fast Entry",
				"link_type": "Page",
				"link_to": "cash-receipt-fast-entry",
				"type": "Link",
			},
		)
		changed = True
	if not any(row.label == "Cash Receipt Fast Entry" for row in workspace.shortcuts):
		workspace.append(
			"shortcuts",
			{"label": "Cash Receipt Fast Entry", "type": "Page", "link_to": "cash-receipt-fast-entry"},
		)
		changed = True
	if not changed:
		return

	developer_mode = frappe.conf.developer_mode
	try:
		frappe.conf.developer_mode = 0
		workspace.save()
	finally:
		frappe.conf.developer_mode = developer_mode
