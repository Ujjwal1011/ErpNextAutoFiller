import frappe

@frappe.whitelist()
def get_groups():
    return frappe.get_all(
        "WhatsApp Group",
        filters={"scraping_enabled": 1},  # The database fieldname
        fields=["name", "group_name", "whatsapp_connection"],
        order_by="modified desc"
    )

@frappe.whitelist()
def get_chat_history(group_name):
    # Fetch the latest 100 messages for the selected group
    messages = frappe.get_all(
        "WhatsApp Message",
        filters={"whatsapp_group": group_name},
        fields=["name", "message", "direction", "timestamp", "has_media", "media_type", "attachment"],
        order_by="timestamp desc",
        limit=100
    )

    message_names = [message.name for message in messages]
    if message_names:
        staging_rows = frappe.get_all(
            "WhatsApp Order Staging",
            filters={"whatsapp_message": ["in", message_names]},
            fields=["name", "whatsapp_message", "status", "created_sales_order"],
            order_by="creation asc",
        )
        staging_by_message = {}
        for row in staging_rows:
            staging_by_message.setdefault(row.whatsapp_message, []).append(row)

        for message in messages:
            message["order_staging_links"] = staging_by_message.get(message.name, [])

    # Reverse so the newest messages appear at the bottom
    return list(reversed(messages))
