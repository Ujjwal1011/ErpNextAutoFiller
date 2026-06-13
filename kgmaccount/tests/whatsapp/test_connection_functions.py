"""Tests for WhatsApp Connection server functions.

Input:
- Uses mocked WAHA client methods for connection test and QR generation.
- Uses fake webhook JSON for incoming WAHA message events.
- Uses fake Frappe logger, database, and document creation objects.

How it checks:
- `test_waha_connection` returns a success payload when WAHA responds.
- `generate_qr_code` returns QR image data from the mocked WAHA response.
- `handle_incoming_webhook` creates an Incoming WhatsApp Message for message
  events and ignores non-message events.
- No real WAHA server is called.
"""

import types
import unittest
from unittest.mock import Mock, patch

from kgmaccount.tests.whatsapp.whatsapp_test_utils import FakeDb, FakeDoc, NoopLogger, call_whitelisted
from kgmaccount.whatsapp_suite.doctype.whatsapp_connection import whatsapp_connection


class TestWhatsAppConnectionFunctions(unittest.TestCase):
    def test_waha_connection_success_returns_success_payload(self):
        """Test Connection button should return a success payload when WAHA responds."""
        fake_client = Mock()
        fake_client.sessions.get.return_value = {"name": "default"}
        fake_frappe = types.SimpleNamespace(
            logger=lambda *args, **kwargs: NoopLogger(),
            log_error=Mock(),
        )

        with patch.object(whatsapp_connection, "WAHAClient", return_value=fake_client), patch.object(
            whatsapp_connection, "frappe", fake_frappe
        ), patch.object(whatsapp_connection, "assert_whatsapp_admin", lambda: None):
            result = call_whitelisted(
                whatsapp_connection.test_waha_connection,
                "localhost:3000",
                "default",
                "secret",
            )

        self.assertEqual(result["status"], "success")
        self.assertIn("Successfully connected", result["message"])

    def test_generate_qr_code_returns_qr_data(self):
        """Generate QR Code button should return the QR image data from WAHA."""
        fake_client = Mock()
        fake_client.sessions.get_qr.return_value = {"data": "data:image/png;base64,abc"}
        fake_frappe = types.SimpleNamespace(
            logger=lambda *args, **kwargs: NoopLogger(),
            log_error=Mock(),
        )

        with patch.object(whatsapp_connection, "WAHAClient", return_value=fake_client), patch.object(
            whatsapp_connection, "frappe", fake_frappe
        ), patch.object(whatsapp_connection, "assert_whatsapp_admin", lambda: None):
            result = call_whitelisted(
                whatsapp_connection.generate_qr_code,
                "localhost:3000",
                "default",
                "secret",
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["qr_data"], "data:image/png;base64,abc")

    def test_waha_connection_offline_returns_friendly_error(self):
        """Offline WAHA should return a user-facing error without raw traceback text."""
        fake_frappe = types.SimpleNamespace(
            logger=lambda *args, **kwargs: NoopLogger(),
            log_error=Mock(),
        )

        with patch.object(whatsapp_connection, "WAHAClient", side_effect=ConnectionError("refused")), patch.object(
            whatsapp_connection, "frappe", fake_frappe
        ), patch.object(whatsapp_connection, "assert_whatsapp_admin", lambda: None):
            result = call_whitelisted(
                whatsapp_connection.test_waha_connection,
                "localhost:3000",
                "default",
                "secret",
            )

        self.assertEqual(result["status"], "error")
        self.assertIn("Could not reach WhatsApp server", result["message"])
        self.assertIn("Please start the WAHA server", result["message"])

    def test_handle_incoming_webhook_saves_message_event(self):
        """Incoming WAHA message event should create an Incoming WhatsApp Message doc."""
        fake_db = FakeDb()
        inserted_docs = []

        def fake_new_doc(doctype):
            doc = FakeDoc(doctype=doctype)
            doc.insert = lambda ignore_permissions=False, doc=doc: inserted_docs.append(doc) or doc
            return doc

        fake_frappe = types.SimpleNamespace(
            request=types.SimpleNamespace(
                get_json=lambda force=False: {
                    "event": "message",
                    "session": "default",
                    "payload": {
                        "from": "120@g.us",
                        "body": "hello",
                        "id": {"_serialized": "MSG-ID"},
                    },
                }
            ),
            new_doc=fake_new_doc,
            db=fake_db,
            logger=lambda *args, **kwargs: NoopLogger(),
            log_error=Mock(),
        )

        with patch.object(whatsapp_connection, "frappe", fake_frappe):
            result = call_whitelisted(whatsapp_connection.handle_incoming_webhook)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(inserted_docs[0].message_id, "MSG-ID")
        self.assertEqual(inserted_docs[0].direction, "Incoming")
        self.assertEqual(fake_db.commits, 1)

    def test_handle_incoming_webhook_ignores_non_message_event(self):
        """Non-message webhook events should be ignored without creating rows."""
        fake_frappe = types.SimpleNamespace(
            request=types.SimpleNamespace(get_json=lambda force=False: {"event": "session.status"}),
            logger=lambda *args, **kwargs: NoopLogger(),
            log_error=Mock(),
        )

        with patch.object(whatsapp_connection, "frappe", fake_frappe):
            result = call_whitelisted(whatsapp_connection.handle_incoming_webhook)

        self.assertEqual(result, {"status": "ignored", "event": "session.status"})


if __name__ == "__main__":
    unittest.main()
