"""Tests for WhatsApp Sales Order item calculation bridge.

Input:
- Passes parsed WhatsApp item data such as `item_code`, `height`, `width`, and
  `quantity` into `calculate_sales_order_item_from_client_script`.
- Uses the exported Sales Order sqft Client Script from
  `kgmaccount/fixtures/client_script.json`.

How it checks:
- Confirms WhatsApp conversion reuses the same Client Script calculation as the
  Sales Order form.
- Checks returned `qty`, `custom_cut_from_height`, and
  `custom_cut_from_width`.
- Confirms conversion fails clearly if the source Client Script is disabled.
"""

import types
import unittest
from unittest.mock import Mock, patch

from kgmaccount.tests.client_script_test_utils import get_client_script
from kgmaccount.utils import order_builder


class TestOrderBuilderClientScriptBridge(unittest.TestCase):
    def test_calculate_sales_order_item_uses_current_sales_order_client_script(self):
        """WhatsApp item calculation should match the Desk Sales Order Client Script."""
        with patch.object(
            order_builder,
            "get_sales_order_qty_client_script",
            return_value=get_client_script("Sales-Order Kota Kaddpaa Granite Neno Calculation"),
        ):
            calculated = order_builder.calculate_sales_order_item_from_client_script(
                {
                    "item_code": "KOTA 42x24",
                    "height": 41,
                    "width": 23,
                    "quantity": 2,
                }
            )

        self.assertEqual(calculated["qty"], 14)
        self.assertEqual(calculated["custom_cut_from_height"], 42)
        self.assertEqual(calculated["custom_cut_from_width"], 24)

    def test_get_sales_order_qty_client_script_rejects_disabled_script(self):
        """Disabled source Client Script should stop WhatsApp conversion early."""
        fake_frappe = types.SimpleNamespace(
            db=types.SimpleNamespace(
                get_value=Mock(return_value=types.SimpleNamespace(script="console.log(1)", enabled=0))
            ),
            throw=Mock(side_effect=Exception),
        )

        with patch.object(order_builder, "frappe", fake_frappe):
            with self.assertRaises(Exception):
                order_builder.get_sales_order_qty_client_script()

    def test_resolve_whatsapp_customer_uses_suspense_when_ai_customer_is_missing(self):
        """Invalid AI customer links should fall back to the Suspense customer."""
        fake_frappe = types.SimpleNamespace(
            db=types.SimpleNamespace(
                exists=Mock(side_effect=lambda doctype, name: doctype == "Customer" and name == "Suspense"),
                get_value=Mock(return_value=None),
            ),
            throw=Mock(side_effect=Exception),
        )

        with patch.object(order_builder, "frappe", fake_frappe):
            self.assertEqual(order_builder.resolve_whatsapp_customer("Wrong AI Name"), "Suspense")

    def test_resolve_whatsapp_item_code_uses_kota_raj_when_ai_item_is_missing(self):
        """Invalid AI item links should fall back to the default item code."""
        fake_frappe = types.SimpleNamespace(
            db=types.SimpleNamespace(
                exists=Mock(side_effect=lambda doctype, name: doctype == "Item" and name == "KOTA 11x11 RAJ"),
                get_value=Mock(return_value=None),
            ),
            throw=Mock(side_effect=Exception),
        )

        with patch.object(order_builder, "frappe", fake_frappe):
            self.assertEqual(order_builder.resolve_whatsapp_item_code("Wrong AI Item"), "KOTA 11x11 RAJ")


if __name__ == "__main__":
    unittest.main()
