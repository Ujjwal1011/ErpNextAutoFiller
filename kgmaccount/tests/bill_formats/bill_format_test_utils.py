"""Helpers for validating exported bill Print Format fixtures.

Input:
- Reads `kgmaccount/fixtures/print_format.json`.
- Builds fake Sales Order, Sales Invoice, and Quotation documents with the
  fields used by the exported Jinja print formats.

How checks work:
- Print Format metadata is checked directly from the fixture.
- The Jinja `html` is rendered with `StrictUndefined` so missing fake document
  fields or broken Jinja expressions fail loudly.
- Rendered output is checked for important bill text and sample item/customer
  values.
"""

import json
import types
from pathlib import Path

from jinja2 import Environment, StrictUndefined


APP_PACKAGE = Path(__file__).resolve().parents[2]
PRINT_FORMAT_FIXTURE = APP_PACKAGE / "fixtures" / "print_format.json"

BILL_FORMAT_PROFILES = {
    "Sales Order": {
        "print_format": "Sales Order Printing",
        "sample_name": "SAL-ORD-TEST-0001",
        "expected_title": "Sales Order",
    },
    "Quotation": {
        "print_format": "Quotation Print Format",
        "sample_name": "QTN-TEST-0001",
        "expected_title": "Quotation",
    },
    "Sales Invoice": {
        "print_format": "Sales Invoice Print Format",
        "sample_name": "SINV-TEST-0001",
        "expected_title": "Sales Invoice",
    },
}


class FakeRow(types.SimpleNamespace):
    """Simple object that supports attribute and dict-style access in Jinja."""

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)


class FakeBillDoc(FakeRow):
    """Fake bill document with Frappe-like `get_formatted` support."""

    def get_formatted(self, fieldname):
        value = getattr(self, fieldname, "")
        if isinstance(value, (int, float)):
            return f"{value:,.2f}"
        return str(value)


def get_print_formats_by_doctype():
    """Return exported Print Formats keyed by their target DocType."""
    with PRINT_FORMAT_FIXTURE.open() as fixture:
        print_formats = json.load(fixture)
    return {print_format["doc_type"]: print_format for print_format in print_formats}


def make_sample_bill_doc(doctype):
    """Build one fake bill document for print-format rendering."""
    item = FakeRow(
        name="ITEM-ROW-1",
        idx=1,
        item_code="KOTA 42x24",
        item_name="KOTA 42x24",
        description="KOTA 42x24",
        uom="Nos",
        stock_uom="Nos",
        qty=14,
        rate=49,
        amount=686,
        custom_height=41,
        custom_width=23,
        custom_quantity=2,
        custom_cut_from_height=42,
        custom_cut_from_width=24,
        custom_left=0,
        custom_right=0,
        custom_top=0,
        custom_bottom=0,
    )
    mould_item = FakeRow(
        name="ITEM-ROW-2",
        idx=2,
        item_code="Dhar Mould",
        item_name="Dhar Mould",
        description="Dhar Mould",
        uom="Ft",
        stock_uom="Ft",
        qty=5.5,
        rate=10,
        amount=55,
        custom_height=35,
        custom_width=29,
        custom_quantity=1,
        custom_cut_from_height=0,
        custom_cut_from_width=0,
        custom_left=1,
        custom_right=0,
        custom_top=1,
        custom_bottom=0,
    )
    tax = FakeRow(
        name="TAX-ROW-1",
        description="GST",
        account_head="GST",
        rate=18,
        tax_amount=133.38,
        total=874.38,
    )

    return FakeBillDoc(
        doctype=doctype,
        name=BILL_FORMAT_PROFILES[doctype]["sample_name"],
        customer="CUST-TEST",
        customer_name="KGM Test Customer",
        party_name="KGM Test Customer",
        custom_cash_customer_name="KGM Cash Customer",
        custom_phone_number="9999999999",
        transaction_date="2026-06-13",
        posting_date="2026-06-13",
        items=[item, mould_item],
        taxes=[tax],
        total=741,
        net_total=741,
        grand_total=874.38,
        rounded_total=874,
        in_words="Eight Hundred Seventy Four only",
    )


def render_print_format(print_format, doc):
    """Render one exported Jinja Print Format with strict missing-field checks."""
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    template = environment.from_string(print_format["html"])
    return template.render(doc=doc)
