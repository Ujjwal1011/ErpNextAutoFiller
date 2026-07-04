import frappe

from kgmaccount.auto_filler.doctype.auto_filler_settings.auto_filler_settings import (
	apply_missing_defaults,
)


def execute():
	doc = frappe.get_single("Auto Filler Settings")
	if apply_missing_defaults(doc):
		doc.save(ignore_permissions=True)
