"""Focused Width = 14 Sales Order sqft Client Script tests.

Input:
- Reads the user-provided CSV fixture at
  `kgmaccount/tests/client_scripts/sales_order/data/width_14_sqft_rows.csv`.
- Filters that fixture to Sales Order rows where CSV `Width` is exactly 14.
- Applies the same sqft exclusions used by `test_sqft_client_script.py`.

How it checks:
- Runs `Sales-Order Kota Kaddpaa Granite Neno Calculation` in Node.js.
- Compares Client Script `qty` with CSV `SQFT` for the supplied width-14 rows.
- On failure, prints a dbt-style failed-row table and writes the standard CSV
  failure log under `kgmaccount/tests/logs/sqft`.
"""

import csv
import unittest
from pathlib import Path

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    CLIENT_SCRIPT_PROFILES,
    collect_sqft_mismatches,
    format_dbt_style_failure_output,
    is_sqft_calculation_row,
    run_item_client_script_for_rows,
    to_float,
    write_failed_rows_log,
)


PROFILE = "sales_order"
WIDTH_14_CSV = Path(__file__).with_name("data") / "width_14_sqft_rows.csv"
FAILURE_LOG = "sales_order_width_14_sqft_failed_rows.json"


def iter_width_14_csv_rows():
    """Yield rows from the supplied width-14 fixture with useful row numbers."""
    with WIDTH_14_CSV.open(newline="") as csvfile:
        for row_number, row in enumerate(csv.DictReader(csvfile), start=2):
            row["_csv_row_number"] = row_number
            yield row


def is_width_14_sqft_row(csv_row):
    """Return True for exact-width 14 rows handled by the sqft script."""
    return to_float(csv_row["Width"]) == 14.0 and is_sqft_calculation_row(csv_row)


class TestSalesOrderWidth14SqftSpecificData(unittest.TestCase):
    def test_supplied_width_14_csv_rows_match_sqft_client_script(self):
        """Loop supplied Width = 14 rows and compare CSV SQFT with the Client Script."""
        self.assertTrue(
            WIDTH_14_CSV.exists(),
            f"Missing Width = 14 Client Script test data CSV: {WIDTH_14_CSV}",
        )

        profile = CLIENT_SCRIPT_PROFILES[PROFILE]
        csv_rows = [row for row in iter_width_14_csv_rows() if is_width_14_sqft_row(row)]
        results = run_item_client_script_for_rows(
            PROFILE,
            profile["sqft_script"],
            "item_code",
            csv_rows,
        )
        mismatches = collect_sqft_mismatches(csv_rows, results)

        self.assertGreater(len(csv_rows), 0, "No Width = 14 sqft rows found in supplied CSV")
        if mismatches:
            log_path = write_failed_rows_log(FAILURE_LOG, mismatches, PROFILE)
            self.fail(
                format_dbt_style_failure_output(
                    "sales_order_width_14_sqft",
                    len(csv_rows),
                    mismatches,
                    log_path,
                )
            )


if __name__ == "__main__":
    unittest.main()
