"""Tests for WhatsApp Group server functions."""

import types
import unittest
from unittest.mock import Mock, patch

from kgmaccount.tests.whatsapp.whatsapp_test_utils import FakeDb, FakeDoc, NoopLogger, call_whitelisted
from kgmaccount.whatsapp_suite.doctype.whatsapp_group import whatsapp_group


class TestWhatsAppGroupFunctions(unittest.TestCase):
    def test_fetch_group_messages_returns_friendly_error_when_waha_is_offline(self):
        """Offline WAHA should return an error payload instead of raising a traceback."""
        fake_group = FakeDoc(
            name="GROUP-1",
            whatsapp_connection="CONN-1",
            whatsapp_id="120@g.us",
            get=lambda fieldname, default=None: "2026-06-13" if fieldname == "scrape_start_date" else default,
        )
        fake_connection = FakeDoc(
            name="CONN-1",
            waha_server_ip="localhost:3000",
            session_name="default",
            api_key="secret",
        )

        def fake_get_doc(doctype, name):
            if doctype == "WhatsApp Group":
                return fake_group
            if doctype == "WhatsApp Connection":
                return fake_connection
            raise AssertionError(f"Unexpected doctype {doctype}")

        fake_db = FakeDb()
        fake_db.get_value = Mock(return_value=None)

        fake_frappe = types.SimpleNamespace(
            get_doc=fake_get_doc,
            db=fake_db,
            log_error=Mock(),
            get_traceback=Mock(return_value="traceback"),
            logger=lambda *args, **kwargs: NoopLogger(),
        )

        fake_client = Mock()
        fake_client.chats.get_messages.side_effect = ConnectionError("connection refused")

        with patch.object(whatsapp_group, "frappe", fake_frappe), patch.object(
            whatsapp_group, "assert_can_access_whatsapp_group", lambda group_name: None
        ), patch.object(whatsapp_group, "WAHAClient", return_value=fake_client):
            result = call_whitelisted(whatsapp_group.fetch_group_messages, "GROUP-1")

        self.assertEqual(result["status"], "error")
        self.assertIn("Could not reach WhatsApp server", result["message"])
        self.assertIn("Please start the WAHA server", result["message"])


if __name__ == "__main__":
    unittest.main()
