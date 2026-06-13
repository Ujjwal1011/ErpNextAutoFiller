"""Guard tests for the shared CSV data used by Quotation Client Script tests.

Input:
- Reads `/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv`.
- Reuses the same named CSV cases as Sales Order because the Quotation item
  scripts should calculate the same item code, sqft, cut size, and rate.

How it checks:
- Confirms the CSV file exists.
- Confirms every named case can be found by `Item Name`, `Height`, `Width`,
  and `Quantity`.

Why this file exists:
- Quotation tests intentionally share the same expected data source. If that
  CSV changes, this small guard test fails before the more detailed script
  tests make debugging noisy.
"""

import unittest

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    REQUIRED_CSV_CASES,
    SALES_ORDER_ITEM_CSV,
    get_item_csv_row,
)


class TestQuotationCsvTestData(unittest.TestCase):
    def test_required_csv_file_exists(self):
        """The shared item list CSV must be present for Quotation tests."""
        self.assertTrue(
            SALES_ORDER_ITEM_CSV.exists(),
            f"Missing Client Script test data CSV: {SALES_ORDER_ITEM_CSV}",
        )

    def test_required_csv_cases_exist(self):
        """Every named Quotation test case must be backed by the shared CSV."""
        for case_name, case in REQUIRED_CSV_CASES.items():
            with self.subTest(case=case_name):
                row = get_item_csv_row(
                    case["item_name"],
                    case["height"],
                    case["width"],
                    case["quantity"],
                )
                self.assertEqual(row["Item Name"], case["item_name"])


if __name__ == "__main__":
    unittest.main()
