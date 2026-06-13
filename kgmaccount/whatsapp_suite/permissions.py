import frappe
from frappe import _


ACCESS_DOCTYPE = "WhatsApp User Access"
ADMIN_ROLE = "System Manager"


def is_whatsapp_admin(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or ADMIN_ROLE in frappe.get_roles(user)


def get_user_whatsapp_access(user=None):
    user = user or frappe.session.user

    if is_whatsapp_admin(user):
        return {
            "can_access": True,
            "is_admin": True,
            "user": user,
            "allowed_group_names": None,
        }

    if not user or user == "Guest":
        return {
            "can_access": False,
            "is_admin": False,
            "user": user,
            "allowed_group_names": [],
        }

    access_name = frappe.db.get_value(ACCESS_DOCTYPE, {"user": user}, "name")
    if not access_name:
        return {
            "can_access": False,
            "is_admin": False,
            "user": user,
            "allowed_group_names": [],
        }

    access_doc = frappe.get_doc(ACCESS_DOCTYPE, access_name)
    if not access_doc.enabled:
        return {
            "can_access": False,
            "is_admin": False,
            "user": user,
            "allowed_group_names": [],
        }

    allowed_group_names = [
        row.whatsapp_group
        for row in access_doc.get("allowed_groups", [])
        if row.whatsapp_group
    ]

    return {
        "can_access": True,
        "is_admin": False,
        "user": user,
        "allowed_group_names": allowed_group_names,
    }


def get_allowed_group_names(user=None):
    access = get_user_whatsapp_access(user)
    if not access["can_access"]:
        return []
    return access["allowed_group_names"]


def can_access_whatsapp_group(group_name, user=None):
    if not group_name:
        return False

    allowed_group_names = get_allowed_group_names(user)
    if allowed_group_names is None:
        return True

    return group_name in allowed_group_names


def assert_can_access_whatsapp_group(group_name, user=None):
    if can_access_whatsapp_group(group_name, user):
        return

    frappe.throw(
        _("You are not allowed to access this WhatsApp group."),
        frappe.PermissionError,
    )


def assert_whatsapp_admin(user=None):
    if is_whatsapp_admin(user):
        return

    frappe.throw(
        _("Only System Manager users can manage WhatsApp access."),
        frappe.PermissionError,
    )
