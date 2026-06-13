"""Tests for Sales Order, Sales Invoice, and Quotation bill Print Formats.

Input:
- Reads exported Print Formats from `kgmaccount/fixtures/print_format.json`.
- Uses fake bill documents for Sales Order, Sales Invoice, and Quotation.

How it checks:
- Confirms each DocType has the expected enabled Jinja Print Format.
- Confirms each format has bill-critical source fields in the template:
  customer/cash customer, phone, items, item name, quantity, rate, amount,
  totals, taxes, and amount in words.
- Renders each Jinja template with a fake document using `StrictUndefined`, so
  missing fields and syntax errors fail the test.
- Checks the rendered bill contains sample customer, item, total, and tax data.
- Checks the rendered bill title matches the DocType being validated.
"""

import unittest

from kgmaccount.tests.bill_formats.bill_format_test_utils import (
    BILL_FORMAT_PROFILES,
    get_print_formats_by_doctype,
    make_sample_bill_doc,
    render_print_format,
)


REQUIRED_TEMPLATE_SNIPPETS = [
    "doc.items",
    "doc.taxes",
    "item.item_name",
    "item.qty",
    "item.rate",
    "item.amount",
    "doc.total",
    "doc.grand_total",
    "doc.in_words",
    "custom_cash_customer_name",
    "custom_phone_number",
]


class TestBillPrintFormats(unittest.TestCase):
    def setUp(self):
        self.print_formats = get_print_formats_by_doctype()

    def test_required_bill_print_formats_exist_and_are_enabled(self):
        """Each bill DocType should have exactly the exported format this app owns."""
        for doctype, profile in BILL_FORMAT_PROFILES.items():
            with self.subTest(doctype=doctype):
                print_format = self.print_formats.get(doctype)

                self.assertIsNotNone(print_format, f"Missing Print Format for {doctype}")
                self.assertEqual(print_format["name"], profile["print_format"])
                self.assertEqual(print_format["print_format_type"], "Jinja")
                self.assertEqual(print_format["disabled"], 0)
                self.assertGreater(len(print_format.get("html") or ""), 1000)

    def test_bill_print_formats_contain_required_source_fields(self):
        """The template source should include the important bill data fields."""
        for doctype in BILL_FORMAT_PROFILES:
            with self.subTest(doctype=doctype):
                html = self.print_formats[doctype]["html"]

                for snippet in REQUIRED_TEMPLATE_SNIPPETS:
                    self.assertIn(snippet, html, f"{doctype} template missing {snippet}")

    def test_bill_print_formats_render_with_sample_documents(self):
        """Each bill Print Format should render with representative item/tax data."""
        for doctype, profile in BILL_FORMAT_PROFILES.items():
            with self.subTest(doctype=doctype):
                doc = make_sample_bill_doc(doctype)
                rendered = render_print_format(self.print_formats[doctype], doc)

                self.assertIn(profile["sample_name"][-3:], rendered)
                self.assertIn(profile["expected_title"], rendered)
                self.assertIn("Kgm Cash Customer", rendered)
                self.assertIn("9999999999", rendered)
                self.assertIn("KOTA 42x24", rendered)
                self.assertIn("Dhar Mould", rendered)
                self.assertIn("GST", rendered)
                self.assertIn("Eight Hundred Seventy Four only", rendered)


if __name__ == "__main__":
    unittest.main()
