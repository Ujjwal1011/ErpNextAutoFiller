"""Tests for Sales Invoice mould and MouldG Client Scripts.

Input:
- Reads mould rows from
  `/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv`.
- Uses CSV `Item Name`, `Height`, `Width`, `Quantity`, `SQFT`, and `Rate`.
- The CSV does not contain mould side flags, so the all-row mould test tries all
  16 combinations of `custom_left`, `custom_right`, `custom_top`, and
  `custom_bottom`.

How it checks:
- Runs `Sales-Invoice Moulding Dialog Box` to verify mould rows copy height and
  width from the previous stone row.
- Runs `Sales-Invoice Kota Granite Moulding Calculation` to calculate running
  feet for Mould and MouldG rows.
- Focused tests check known side selections against CSV `SQFT` and `Rate`.
- The all-row test checks whether any side selection can reproduce the CSV
  `SQFT` for each mould row.

Logs:
- If the all-row mould test fails, failed rows are written to
  `kgmaccount/tests/logs/sales_invoice_mould_failed_rows.json`.
"""

import unittest

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    CLIENT_SCRIPT_PROFILES,
    format_csv_expectation,
    get_required_case,
    is_mould_or_mouldg_row,
    iter_item_csv_rows,
    run_item_client_script,
    run_item_client_script_for_rows,
    to_float,
    write_failed_rows_log,
)


PROFILE = "sales_invoice"


class TestSalesInvoiceMouldClientScripts(unittest.TestCase):
    def test_all_mould_csv_rows_can_match_running_feet_with_side_selection(self):
        """Loop every mould CSV row and find a side-selection combination matching CSV sqft."""
        self._assert_all_mould_rows_can_match_running_feet()

    def test_mould_dialog_copies_previous_item_dimensions(self):
        """Sales Invoice mould dialog should copy height/width from the previous stone item row."""
        result = run_item_client_script(
            PROFILE,
            CLIENT_SCRIPT_PROFILES[PROFILE]["mould_dialog_script"],
            "item_code",
            {"name": "MOULD-ROW", "item_code": "Dhar Mould"},
            dialog_values={"left": 1, "top": 1, "right": 0, "bottom": 0},
            doc_items=[
                {"name": "STONE-ROW", "custom_height": 35, "custom_width": 29},
                {"name": "MOULD-ROW", "item_code": "Dhar Mould"},
            ],
        )
        debug = (
            f"client script output row={result['row']}; "
            f"dialog={result.get('dialog_values')}; "
            f"calls={result.get('calls')}; "
            f"messages={result.get('messages')}"
        )

        self.assertEqual(result["dialog_title"], "Item Custom Dimensions (Invoice)", debug)
        self.assertEqual(result["row"]["custom_height"], 35, debug)
        self.assertEqual(result["row"]["custom_width"], 29, debug)
        self.assertEqual(result["row"]["custom_left"], 1, debug)
        self.assertEqual(result["row"]["custom_top"], 1, debug)

    def test_job_work_dialog_selects_all_sides_by_default(self):
        """Sales Invoice job work rows should open the mould dialog with all sides selected."""
        result = run_item_client_script(
            PROFILE,
            CLIENT_SCRIPT_PROFILES[PROFILE]["mould_dialog_script"],
            "item_code",
            {"name": "JOB-WORK-ROW", "item_code": "Tiles Job Work"},
            doc_items=[
                {"name": "STONE-ROW", "custom_height": 31.2, "custom_width": 17.5},
                {"name": "JOB-WORK-ROW", "item_code": "Tiles Job Work"},
            ],
        )
        debug = (
            f"client script output row={result['row']}; "
            f"dialog={result.get('dialog_values')}; "
            f"calls={result.get('calls')}; "
            f"messages={result.get('messages')}"
        )

        self.assertEqual(result["row"]["custom_right"], 1, debug)
        self.assertEqual(result["row"]["custom_left"], 1, debug)
        self.assertEqual(result["row"]["custom_top"], 1, debug)
        self.assertEqual(result["row"]["custom_bottom"], 1, debug)

    def test_mould_quantity_calculation_matches_csv_running_feet(self):
        """Standard Mould rounds dimensions to six inches before running-foot calculation."""
        case, csv_row = get_required_case("mould")
        result = self._run_mould_case(case, {"custom_left": 1, "custom_top": 1})
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["qty"], float(csv_row["SQFT"]), debug)
        self.assertEqual(float(csv_row["Rate"]), 10.0, debug)

    def test_mouldg_quantity_calculation_matches_csv_running_feet(self):
        """MouldG rounds dimensions to three inches before running-foot calculation."""
        case, csv_row = get_required_case("mouldg")
        result = self._run_mould_case(case, {"custom_top": 1, "custom_bottom": 1})
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["qty"], float(csv_row["SQFT"]), debug)
        self.assertEqual(float(csv_row["Rate"]), 10.0, debug)

    def test_job_work_quantity_calculation_matches_csv_running_feet_with_all_sides(self):
        """Sales Invoice job work rows use moulding running-foot calculation instead of sqft."""
        case, csv_row = get_required_case("job_work")
        result = self._run_mould_case(
            case,
            {"custom_left": 1, "custom_right": 1, "custom_top": 1, "custom_bottom": 1},
        )
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["qty"], float(csv_row["SQFT"]), debug)
        self.assertEqual(float(csv_row["Rate"]), 15.0, debug)

    def _run_mould_case(self, case, side_values):
        """Run the Sales Invoice mould calculation script for one CSV-backed item."""
        row = {
            "item_code": case["item_name"],
            "custom_height": case["height"],
            "custom_width": case["width"],
            "custom_quantity": case["quantity"],
        }
        row.update(side_values)
        return run_item_client_script(
            PROFILE,
            CLIENT_SCRIPT_PROFILES[PROFILE]["mould_script"],
            "custom_quantity",
            row,
            apply_dialog=False,
        )

    def _assert_all_mould_rows_can_match_running_feet(self):
        """Run all mould rows through every side combination and log failures."""
        profile = CLIENT_SCRIPT_PROFILES[PROFILE]
        csv_rows = [
            row
            for row in iter_item_csv_rows()
            if is_mould_or_mouldg_row(row)
            and to_float(row["Height"]) > 0
            and to_float(row["Width"]) > 0
            and to_float(row["Quantity"]) > 0
        ]
        side_combinations = [
            {"custom_left": left, "custom_right": right, "custom_top": top, "custom_bottom": bottom}
            for left in (0, 1)
            for right in (0, 1)
            for top in (0, 1)
            for bottom in (0, 1)
        ]
        expanded_rows = []
        expanded_csv_rows = []
        for csv_row in csv_rows:
            for side_values in side_combinations:
                row_copy = dict(csv_row)
                row_copy.update(side_values)
                expanded_csv_rows.append(row_copy)
                expanded_rows.append(row_copy)

        results = run_item_client_script_for_rows(PROFILE, profile["mould_script"], "custom_quantity", expanded_rows)

        self.assertGreater(len(csv_rows), 0, "No mould rows found in shared CSV")
        grouped_results = {}
        for csv_row, result in zip(expanded_csv_rows, results):
            grouped_results.setdefault(csv_row["_csv_row_number"], []).append((csv_row, result))

        mismatches = []
        for csv_row in csv_rows:
            expected_sqft = to_float(csv_row["SQFT"])
            matching_results = [
                (candidate_row, result)
                for candidate_row, result in grouped_results[csv_row["_csv_row_number"]]
                if abs(to_float(result["row"].get("qty")) - expected_sqft) <= 0.01
            ]
            if not matching_results:
                candidate_qtys = sorted(
                    {
                        to_float(result["row"].get("qty"))
                        for _candidate, result in grouped_results[csv_row["_csv_row_number"]]
                    }
                )
                mismatches.append(
                    {
                        "csv_row": csv_row["_csv_row_number"],
                        "sales_order": csv_row["Sales Order"],
                        "item": csv_row["Item Name"],
                        "height": csv_row["Height"],
                        "width": csv_row["Width"],
                        "quantity": csv_row["Quantity"],
                        "expected_sqft": expected_sqft,
                        "candidate_qtys": candidate_qtys,
                    }
                )

        if mismatches:
            preview = "\n".join(str(row) for row in mismatches[:25])
            log_path = write_failed_rows_log(profile["mould_log"], mismatches, PROFILE)
            self.fail(
                f"{len(mismatches)} mould CSV rows could not match any Sales Invoice side selection. "
                f"Failed rows logged at: {log_path}\n"
                f"Showing first 25:\n{preview}"
            )


if __name__ == "__main__":
    unittest.main()
