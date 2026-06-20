"""Tests for the Quotation sqft calculation Client Script.

Input:
- Reads rows from `/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv`.
- For each applicable row, sends these CSV fields to the Quotation Item script:
  `Item Name` -> `item_code`, `Height` -> `custom_height`,
  `Width` -> `custom_width`, `Quantity` -> `custom_quantity`.
- Skips rows handled by mould, mouldG, tiles, hole, and farma scripts.

How it checks:
- Runs `Quotation Kota Kaddpaa Granite Neno Calculation` in Node.js.
- Compares Client Script `qty` with CSV `SQFT`.
- Focused branch tests compare cut sizes with CSV `Cut From Height` and
  `Cut From Width`, and check CSV `Rate`.
- Uses the same Raj Kota, Kota without Raj, without Kota, and Kaddpa cases as
  the Sales Order tests.

Logs:
- If the all-row CSV test fails, failed rows are written to
  `kgmaccount/tests/logs/quotation_sqft_failed_rows.json`.
"""

import unittest

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    CLIENT_SCRIPT_PROFILES,
    format_csv_expectation,
    get_required_case,
    is_sqft_calculation_row,
    iter_item_csv_rows,
    run_item_client_script,
    run_item_client_script_for_rows,
    to_float,
    write_failed_rows_log,
)


PROFILE = "quotation"


class TestQuotationSqftCalculationClientScript(unittest.TestCase):
    def test_all_applicable_csv_rows_match_sqft_client_script(self):
        """Loop every non-mould calculable CSV row and compare sqft with Quotation script."""
        profile = CLIENT_SCRIPT_PROFILES[PROFILE]
        csv_rows = [row for row in iter_item_csv_rows() if is_sqft_calculation_row(row)]
        results = run_item_client_script_for_rows(PROFILE, profile["sqft_script"], "item_code", csv_rows)

        self.assertGreater(len(csv_rows), 0, "No sqft-calculable rows found in shared CSV")
        mismatches = []
        for csv_row, result in zip(csv_rows, results):
            expected_sqft = to_float(csv_row["SQFT"])
            actual_sqft = to_float(result["row"].get("qty"))
            if abs(actual_sqft - expected_sqft) > 0.01:
                mismatches.append(
                    {
                        "csv_row": csv_row["_csv_row_number"],
                        "sales_order": csv_row["Sales Order"],
                        "item": csv_row["Item Name"],
                        "height": csv_row["Height"],
                        "width": csv_row["Width"],
                        "quantity": csv_row["Quantity"],
                        "expected_sqft": expected_sqft,
                        "actual_sqft": actual_sqft,
                    }
                )

        if mismatches:
            preview = "\n".join(str(row) for row in mismatches[:25])
            log_path = write_failed_rows_log(profile["sqft_log"], mismatches, PROFILE)
            self.fail(
                f"{len(mismatches)} CSV rows do not match the current Quotation sqft Client Script. "
                f"Failed rows logged at: {log_path}\n"
                f"Showing first 25:\n{preview}"
            )

    def test_raj_kota_gets_expected_sqft_and_cut_sizes_from_csv(self):
        """Raj Kota uses plus-six rounding for both height and width."""
        case, csv_row = get_required_case("raj_kota")
        result = self._run_sqft_case(case)
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["cut_from_height"], float(csv_row["Cut From Height"]), debug)
        self.assertEqual(result["row"]["cut_from_width"], float(csv_row["Cut From Width"]), debug)
        self.assertEqual(result["row"]["qty"], float(csv_row["SQFT"]), debug)
        self.assertEqual(float(csv_row["Rate"]), 37.0, debug)

    def test_kota_without_raj_gets_expected_sqft_and_cut_sizes_from_csv(self):
        """Kota without Raj uses pair/single width rules and strict-next-six height."""
        case, csv_row = get_required_case("kota_without_raj")
        result = self._run_sqft_case(case)
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["cut_from_height"], float(csv_row["Cut From Height"]), debug)
        self.assertEqual(result["row"]["cut_from_width"], float(csv_row["Cut From Width"]), debug)
        self.assertEqual(result["row"]["qty"], float(csv_row["SQFT"]), debug)
        self.assertEqual(float(csv_row["Rate"]), 49.0, debug)

    def test_without_kota_gets_expected_sqft_and_csv_price(self):
        """Non-Kota/non-Kaddpa granite uses the default three-inch rounding branch."""
        case, csv_row = get_required_case("without_kota")
        result = self._run_sqft_case(case)
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["qty"], float(csv_row["SQFT"]), debug)
        self.assertEqual(float(csv_row["Rate"]), 165.0, debug)

    def test_kaddpa_gets_expected_sqft_and_cut_sizes_from_csv(self):
        """Kaddpa uses six-inch rounding for both height and width."""
        case, csv_row = get_required_case("kaddpa")
        result = self._run_sqft_case(case)
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["cut_from_height"], float(csv_row["Cut From Height"]), debug)
        self.assertEqual(result["row"]["cut_from_width"], float(csv_row["Cut From Width"]), debug)
        self.assertEqual(result["row"]["qty"], float(csv_row["SQFT"]), debug)
        self.assertEqual(float(csv_row["Rate"]), 55.0, debug)

    def test_job_work_is_skipped_by_sqft_calculation(self):
        """Quotation job work rows are handled by moulding quantity, not sqft calculation."""
        case, _csv_row = get_required_case("job_work")
        result = self._run_sqft_case(case)
        debug = f"client script output row={result['row']}; calls={result.get('calls')}"

        self.assertNotIn("qty", result["row"], debug)
        self.assertNotIn("cut_from_height", result["row"], debug)
        self.assertNotIn("cut_from_width", result["row"], debug)

    def _run_sqft_case(self, case):
        """Run the Quotation sqft script for one CSV-backed item example."""
        return run_item_client_script(
            PROFILE,
            CLIENT_SCRIPT_PROFILES[PROFILE]["sqft_script"],
            "item_code",
            {
                "item_code": case["item_name"],
                "custom_height": case["height"],
                "custom_width": case["width"],
                "custom_quantity": case["quantity"],
            },
            apply_dialog=False,
        )


if __name__ == "__main__":
    unittest.main()
