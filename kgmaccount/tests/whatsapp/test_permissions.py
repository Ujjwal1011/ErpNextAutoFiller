"""Tests for WhatsApp user/group access helpers."""

import types
import unittest
from unittest.mock import Mock, patch

from kgmaccount.tests.whatsapp.whatsapp_test_utils import FakeDoc
from kgmaccount.whatsapp_suite import permissions


class TestWhatsAppPermissions(unittest.TestCase):
    def test_system_manager_can_access_all_groups(self):
        """System Manager users should not be limited by access rows."""
        fake_frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="manager@example.com"),
            get_roles=Mock(return_value=["System Manager"]),
        )

        with patch.object(permissions, "frappe", fake_frappe):
            access = permissions.get_user_whatsapp_access()

        self.assertTrue(access["can_access"])
        self.assertTrue(access["is_admin"])
        self.assertIsNone(access["allowed_group_names"])

    def test_enabled_user_gets_only_configured_groups(self):
        """A configured user should receive only the groups from their access row."""
        fake_db = types.SimpleNamespace(get_value=Mock(return_value="user@example.com"))
        fake_access_doc = FakeDoc(
            enabled=1,
            allowed_groups=[FakeDoc(whatsapp_group="GROUP-1"), FakeDoc(whatsapp_group="GROUP-2")],
            get=lambda fieldname, default=None: getattr(fake_access_doc, fieldname, default),
        )
        fake_frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="user@example.com"),
            get_roles=Mock(return_value=[]),
            db=fake_db,
            get_doc=Mock(return_value=fake_access_doc),
        )

        with patch.object(permissions, "frappe", fake_frappe):
            access = permissions.get_user_whatsapp_access()

        self.assertTrue(access["can_access"])
        self.assertFalse(access["is_admin"])
        self.assertEqual(access["allowed_group_names"], ["GROUP-1", "GROUP-2"])

    def test_user_without_access_row_cannot_access_whatsapp(self):
        """Users without a WhatsApp User Access row should be denied."""
        fake_frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="user@example.com"),
            get_roles=Mock(return_value=[]),
            db=types.SimpleNamespace(get_value=Mock(return_value=None)),
        )

        with patch.object(permissions, "frappe", fake_frappe):
            access = permissions.get_user_whatsapp_access()

        self.assertFalse(access["can_access"])
        self.assertEqual(access["allowed_group_names"], [])


if __name__ == "__main__":
    unittest.main()
