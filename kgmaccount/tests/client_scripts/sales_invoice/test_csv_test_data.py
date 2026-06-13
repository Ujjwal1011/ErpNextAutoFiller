"""Guard tests for the shared CSV data used by Sales Invoice Client Script tests.

Input:
- Reads `/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv`.
- Uses the named cases declared in the shared helper for Raj Kota, Kota without
  Raj, without Kota, Kaddpa, Mould, and MouldG.

How it checks:
- Confirms the CSV file exists.
- Confirms every named case can be found by `Item Name`, `Height`, `Width`,
  and `Quantity`.

Why this file exists:
- Other Client Script tests depend on this CSV. If the file is missing or one
  required row is changed, this test fails first with a clear message.
"""

import unittest

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    REQUIRED_CSV_CASES,
    SALES_ORDER_ITEM_CSV,
    get_item_csv_row,
)


class TestSalesInvoiceCsvTestData(unittest.TestCase):
    def test_required_csv_file_exists(self):
        """The user-provided item list CSV must be present."""
        self.assertTrue(
            SALES_ORDER_ITEM_CSV.exists(),
            f"Missing Client Script test data CSV: {SALES_ORDER_ITEM_CSV}",
        )

    def test_required_csv_cases_exist(self):
        """Every named test case must be backed by a row in the CSV."""
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
