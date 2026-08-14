"""Rendering checks for the shared Sales Order batch print templates."""

import types
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


APP_ROOT = Path(__file__).resolve().parents[3]


class FakeRow(types.SimpleNamespace):
    def get_formatted(self, fieldname):
        return str(getattr(self, fieldname, ""))


def make_item(name, idx, item_name, width, height, item_code=None):
    return FakeRow(
        name=name,
        idx=idx,
        item_code=item_code or item_name,
        item_name=item_name,
        custom_width=width,
        custom_height=height,
        custom_quantity=1,
        custom_top=0,
        custom_bottom=1 if "mould" in (item_code or item_name).lower() else 0,
        custom_left=0,
        custom_right=1 if "mould" in (item_code or item_name).lower() else 0,
        qty=10,
        uom="SQFT",
        rate=25,
        amount=250,
    )


def make_bill(name, items, grand_total):
    return FakeRow(
        name=name,
        docstatus=1,
        customer="CUST-001",
        customer_name="AMBIKA TRADERS",
        custom_cash_customer_name="Ambika ...Dilip",
        custom_phone_number="",
        transaction_date="2026-04-24",
        items=items,
        taxes=[],
        total=grand_total,
        grand_total=grand_total,
        in_words="",
    )


class FakeFrappe:
    def __init__(self, bills):
        self.bills = bills

    def get_doc(self, doctype, name):
        if doctype != "Sales Order":
            raise AssertionError(f"Unexpected DocType: {doctype}")
        return self.bills[name]

    @staticmethod
    def format(value, options):
        if options != {"fieldtype": "Date"}:
            raise AssertionError(f"Unexpected format options: {options}")
        return str(value)


class TestSalesOrderBatchPrintFormat(unittest.TestCase):
    def render_batch(self):
        first_bill = make_bill(
            "SAL-ORD-2026-00007",
            [
                make_item("ROW-1", 1, "KOTA 66x24", 20, 65),
                make_item("ROW-2", 2, "Dhar Mould A", 20, 65),
                make_item("ROW-3", 3, "Blue Pearl", 20, 65),
                make_item("ROW-4", 4, "Dhar Mould B", 20, 65),
            ],
            4015,
        )
        second_bill = make_bill(
            "SAL-ORD-2026-00030",
            [make_item("ROW-5", 1, "KOTA 30x24 RIV", 25, 29)],
            1125,
        )
        bills = {first_bill.name: first_bill, second_bill.name: second_bill}
        batch = FakeRow(
            from_date="2026-04-01",
            to_date="2026-08-31",
            sales_orders=[
                FakeRow(sales_order=first_bill.name),
                FakeRow(sales_order=second_bill.name),
            ],
        )

        environment = Environment(
            loader=FileSystemLoader(APP_ROOT),
            undefined=StrictUndefined,
            autoescape=False,
        )
        environment.globals["frappe"] = FakeFrappe(bills)
        template = environment.from_string(
            '{% include "kgmaccount/templates/includes/sales_order_batch_moulding_combine_styles.html" %}'
            '{% include "kgmaccount/templates/includes/sales_order_batch_moulding_combine.html" %}'
        )
        return template.render(doc=batch)

    def test_batch_matches_moulding_combine_structure(self):
        rendered = self.render_batch()

        self.assertIn("Ambika ...Dilip", rendered)
        self.assertIn("AMBIKA TRADERS".title(), rendered)
        self.assertIn("Quotations", rendered)
        self.assertIn("2026-04-01", rendered)
        self.assertIn("2026-08-31", rendered)
        self.assertIn("007", rendered)
        self.assertIn("030", rendered)
        self.assertIn("BATCH GRAND TOTAL", rendered)
        self.assertIn("5140.00", rendered)

    def test_moulding_is_combined_by_rate(self):
        rendered = self.render_batch()

        self.assertNotIn("Dhar Mould A", rendered)
        self.assertNotIn("Dhar Mould B", rendered)
        self.assertEqual(rendered.count(">Combined Moulding<"), 1)
        self.assertIn("20.000", rendered)
        self.assertIn("500.00", rendered)
        self.assertLess(rendered.index("Blue Pearl"), rendered.index("Combined Moulding"))


if __name__ == "__main__":
    unittest.main()
