"""Separate Sales Invoice Select Item tests for Kaddpa rows.

Input:
- Reads every row from
  `/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv`
  where `Item Name` starts with `Kaddpa`.
- Sends the CSV `Height` and `Width` into the fake Sales Invoice Item row.
- Sets the Select Item dialog template option to `KADDPA`.

How it checks:
- Runs `Sales-Invoice Select Item` in Node.js with the fake Frappe dialog.
- Simulates pressing the dialog primary action.
- Checks the generated item code against the exact CSV item code.
- Checks `custom_cut_from_height` and `custom_cut_from_width` against the CSV
  `Cut From Height` and `Cut From Width`.
- Does not check rate or price list data.

Logs:
- Failed Kaddpa rows are written to
  `kgmaccount/tests/logs/select_item/sales_invoice_kaddpa_select_item_failed_rows.csv`.
"""

import unittest

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    collect_select_item_mismatches,
    is_kaddpa_item_row,
    iter_item_csv_rows,
    write_failed_rows_log,
)


PROFILE = "sales_invoice"
LOG_FILENAME = "sales_invoice_kaddpa_select_item_failed_rows.json"


class TestSalesInvoiceKaddpaSelectItemDialog(unittest.TestCase):
    def test_all_kaddpa_csv_rows_generate_expected_item_code_and_cut_size(self):
        """Loop every Kaddpa CSV row and log what the dialog cannot reproduce."""
        csv_rows = [row for row in iter_item_csv_rows() if is_kaddpa_item_row(row)]

        self.assertGreater(len(csv_rows), 0, "No Kaddpa rows found in shared CSV")
        mismatches = collect_select_item_mismatches(PROFILE, csv_rows)
        log_path = write_failed_rows_log(LOG_FILENAME, mismatches, PROFILE)

        if mismatches:
            preview = "\n".join(str(row) for row in mismatches[:25])
            self.fail(
                f"{len(mismatches)} Kaddpa CSV rows do not match the Sales Invoice Select Item dialog. "
                f"Failed rows logged at: {log_path}\n"
                f"Showing first 25:\n{preview}"
            )


if __name__ == "__main__":
    unittest.main()
