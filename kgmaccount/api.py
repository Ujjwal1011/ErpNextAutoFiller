import frappe
from whatsapp_suite.doctype.whatsapp_group.whatsapp_group import fetch_group_messages
def sync_all_active_groups():
    # Fetch messages for all groups where 'scraping_enabled' is checked
    active_groups = frappe.get_all("WhatsApp Group", filters={"scraping_enabled": 1})
    for g in active_groups:
        fetch_group_messages(g.name)