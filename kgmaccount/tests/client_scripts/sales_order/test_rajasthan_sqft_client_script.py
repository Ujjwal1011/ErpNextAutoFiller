"""Focused Rajasthan-only Sales Order sqft Client Script tests.

Input:
- Reads the user-provided CSV fixture at
  `kgmaccount/tests/client_scripts/sales_order/data/rajasthan_sqft_rows.csv`.
- Filters that fixture to Sales Order rows whose `Item Name` contains `RAJ`.
- Applies the same sqft exclusions used by `test_sqft_client_script.py`.

How it checks:
- Runs `Sales-Order Kota Kaddpaa Granite Neno Calculation` in Node.js.
- Compares Client Script `qty` with CSV `SQFT` for the supplied Rajasthan rows.
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
    write_failed_rows_log,
)


PROFILE = "sales_order"
RAJASTHAN_CSV = Path(__file__).with_name("data") / "rajasthan_sqft_rows.csv"
FAILURE_LOG = "sales_order_rajasthan_sqft_failed_rows.json"


def iter_rajasthan_csv_rows():
    """Yield rows from the supplied Rajasthan fixture with useful row numbers."""
    with RAJASTHAN_CSV.open(newline="") as csvfile:
        for row_number, row in enumerate(csv.DictReader(csvfile), start=2):
            row["_csv_row_number"] = row_number
            yield row


def is_rajasthan_sqft_row(csv_row):
    """Return True for supplied Rajasthan rows handled by the sqft script."""
    return "RAJ" in csv_row["Item Name"].upper() and is_sqft_calculation_row(csv_row)


class TestSalesOrderRajasthanSqftSpecificData(unittest.TestCase):
    def test_supplied_rajasthan_csv_rows_match_sqft_client_script(self):
        """Loop supplied Rajasthan rows and compare CSV SQFT with the Client Script."""
        self.assertTrue(
            RAJASTHAN_CSV.exists(),
            f"Missing Rajasthan Client Script test data CSV: {RAJASTHAN_CSV}",
        )

        profile = CLIENT_SCRIPT_PROFILES[PROFILE]
        csv_rows = [row for row in iter_rajasthan_csv_rows() if is_rajasthan_sqft_row(row)]
        results = run_item_client_script_for_rows(
            PROFILE,
            profile["sqft_script"],
            "item_code",
            csv_rows,
        )
        mismatches = collect_sqft_mismatches(csv_rows, results)

        self.assertGreater(len(csv_rows), 0, "No Rajasthan sqft rows found in supplied CSV")
        if mismatches:
            log_path = write_failed_rows_log(FAILURE_LOG, mismatches, PROFILE)
            self.fail(
                format_dbt_style_failure_output(
                    "sales_order_rajasthan_sqft",
                    len(csv_rows),
                    mismatches,
                    log_path,
                )
            )


if __name__ == "__main__":
    unittest.main()
