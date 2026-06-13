"""Tests for the WhatsApp chat UI page data helpers.

Input:
- Uses fake WhatsApp Message rows.
- Uses fake WhatsApp Order Staging rows linked to those messages.
- Uses fake `frappe.get_all`; no database is queried.

How it checks:
- Runs `get_chat_history`.
- Confirms messages are returned in display order.
- Confirms each message includes its related `order_staging_links`.
"""

import types
import unittest
from unittest.mock import patch

from kgmaccount.tests.whatsapp.whatsapp_test_utils import FakeDoc, call_whitelisted
from kgmaccount.whatsapp_suite.page.whatsapp_chat_ui import whatsapp_chat_ui


class TestWhatsAppChatPageFunctions(unittest.TestCase):
    def test_get_chat_history_attaches_staging_links_to_each_message(self):
        """Chat history should include grouped staging links for each message."""
        def fake_get_all(doctype, **kwargs):
            if doctype == "WhatsApp Message":
                return [FakeDoc(name="MSG-2"), FakeDoc(name="MSG-1")]
            if doctype == "WhatsApp Order Staging":
                return [
                    FakeDoc(name="STG-1", whatsapp_message="MSG-1", status="Pending"),
                    FakeDoc(name="STG-2", whatsapp_message="MSG-2", status="Converted"),
                ]
            raise AssertionError(f"Unexpected doctype {doctype}")

        fake_frappe = types.SimpleNamespace(get_all=fake_get_all)

        with patch.object(whatsapp_chat_ui, "frappe", fake_frappe), patch.object(
            whatsapp_chat_ui, "assert_can_access_whatsapp_group", lambda group_name: None
        ):
            history = call_whitelisted(whatsapp_chat_ui.get_chat_history, "GROUP-1")

        self.assertEqual([message.name for message in history], ["MSG-1", "MSG-2"])
        self.assertEqual(history[0]["order_staging_links"][0].name, "STG-1")
        self.assertEqual(history[1]["order_staging_links"][0].name, "STG-2")

    def test_get_groups_returns_access_denied_payload_without_access(self):
        """Users without WhatsApp access should receive no groups."""
        with patch.object(
            whatsapp_chat_ui,
            "get_user_whatsapp_access",
            lambda: {"can_access": False, "is_admin": False, "allowed_group_names": []},
        ):
            result = call_whitelisted(whatsapp_chat_ui.get_groups)

        self.assertFalse(result["can_access"])
        self.assertEqual(result["groups"], [])

    def test_get_groups_filters_to_assigned_groups(self):
        """Allowed users should only receive their assigned WhatsApp groups."""
        captured_filters = {}

        def fake_get_all(doctype, **kwargs):
            captured_filters.update(kwargs["filters"])
            return [FakeDoc(name="GROUP-1")]

        fake_frappe = types.SimpleNamespace(get_all=fake_get_all)

        with patch.object(whatsapp_chat_ui, "frappe", fake_frappe), patch.object(
            whatsapp_chat_ui,
            "get_user_whatsapp_access",
            lambda: {"can_access": True, "is_admin": False, "allowed_group_names": ["GROUP-1"]},
        ):
            result = call_whitelisted(whatsapp_chat_ui.get_groups)

        self.assertTrue(result["can_access"])
        self.assertEqual(captured_filters["name"], ["in", ["GROUP-1"]])
        self.assertEqual(result["groups"][0].name, "GROUP-1")


if __name__ == "__main__":
    unittest.main()
