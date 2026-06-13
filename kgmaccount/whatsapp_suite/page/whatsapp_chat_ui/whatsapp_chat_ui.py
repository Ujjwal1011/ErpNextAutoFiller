import frappe

from kgmaccount.whatsapp_suite.permissions import (
    assert_can_access_whatsapp_group,
    get_user_whatsapp_access,
)


def _with_group_access_filter(filters, access):
    filters = dict(filters or {})
    allowed_group_names = access["allowed_group_names"]
    if allowed_group_names is not None:
        if not allowed_group_names:
            return None
        filters["name"] = ["in", allowed_group_names]

    return filters

@frappe.whitelist()
def get_groups():
    access = get_user_whatsapp_access()
    if not access["can_access"]:
        return {
            "can_access": False,
            "is_admin": False,
            "groups": [],
            "message": "You do not have WhatsApp access enabled for your user.",
        }

    filters = _with_group_access_filter({"scraping_enabled": 1}, access)
    if filters is None:
        return {
            "can_access": True,
            "is_admin": access["is_admin"],
            "groups": [],
            "message": "No WhatsApp groups are assigned to your user.",
        }

    groups = frappe.get_all(
        "WhatsApp Group",
        filters=filters,
        fields=["name", "group_name", "whatsapp_connection", "scraping_enabled", "scrape_start_date"],
        order_by="modified desc"
    )

    return {
        "can_access": True,
        "is_admin": access["is_admin"],
        "groups": groups,
    }


@frappe.whitelist()
def get_chat_history(group_name):
    assert_can_access_whatsapp_group(group_name)

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
