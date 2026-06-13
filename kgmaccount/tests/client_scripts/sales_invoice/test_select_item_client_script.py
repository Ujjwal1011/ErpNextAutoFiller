"""Tests for the Sales Invoice `custom_select_item` dialog Client Script.

Input:
- Reads selected CSV cases from
  `/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv`.
- Sends CSV `Height` and `Width` to the fake Sales Invoice Item row.
- Adds dialog choices such as `custom_is_rajsthan`, `custom_is_gadela`, or
  `item_template_filter = KADDPA`.
- The all-row test loops only CSV rows whose `Item Name` starts with `KOTA`.

How it checks:
- Runs `Sales-Invoice Select Item` in Node.js with a fake `frappe.ui.Dialog`.
- Simulates pressing the dialog primary action.
- Checks that the generated `item_code`, `custom_cut_from_height`, and
  `custom_cut_from_width` match the expected case.
- Does not check Item Price or price list data because rates can be wrong or
  incomplete on the development server. This script only owns item selection.

Cases covered:
- All Kota CSV rows, plus focused Raj Kota, Kota without Raj, and Kaddpa cases.

Logs:
- If any Kota CSV row does not match, failed rows are written to
  `kgmaccount/tests/logs/sales_invoice_select_item_failed_rows.csv`.
"""

import unittest

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    CLIENT_SCRIPT_PROFILES,
    collect_select_item_mismatches,
    format_csv_expectation,
    get_required_case,
    is_kota_item_row,
    iter_item_csv_rows,
    run_item_client_script,
    write_failed_rows_log,
)


PROFILE = "sales_invoice"


class TestSalesInvoiceSelectItemDialog(unittest.TestCase):
    def test_all_kota_csv_rows_generate_expected_item_code_and_cut_size(self):
        """Loop every Kota CSV row and log rows where the dialog cannot reproduce it."""
        profile = CLIENT_SCRIPT_PROFILES[PROFILE]
        csv_rows = [row for row in iter_item_csv_rows() if is_kota_item_row(row)]

        self.assertGreater(len(csv_rows), 0, "No Kota rows found in shared CSV")
        mismatches = collect_select_item_mismatches(PROFILE, csv_rows)
        log_path = write_failed_rows_log(profile["select_item_log"], mismatches, PROFILE)

        if mismatches:
            preview = "\n".join(str(row) for row in mismatches[:25])
            self.fail(
                f"{len(mismatches)} Kota CSV rows do not match the Sales Invoice Select Item dialog. "
                f"Failed rows logged at: {log_path}\n"
                f"Showing first 25:\n{preview}"
            )

    def test_raj_kota_dialog_generates_item_code_and_cut_size(self):
        """Raj Kota: Sales Invoice dialog should generate `KOTA 24x24 RAJ G` and cut size."""
        case, csv_row = get_required_case("raj_kota")
        result = run_item_client_script(
            PROFILE,
            CLIENT_SCRIPT_PROFILES[PROFILE]["select_script"],
            "custom_select_item",
            {"custom_height": case["height"], "custom_width": case["width"]},
            dialog_values={"custom_is_rajsthan": 1, "custom_is_gadela": 1},
            available_items=[case["item_name"]],
        )
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["item_code"], "KOTA 24x24 RAJ G", debug)
        self.assertEqual(result["row"]["custom_cut_from_height"], 24, debug)
        self.assertEqual(result["row"]["custom_cut_from_width"], 24, debug)

    def test_kota_without_raj_dialog_generates_item_code_and_cut_size(self):
        """Kota without Raj: Sales Invoice dialog should generate `KOTA 42x24` and cut size."""
        case, csv_row = get_required_case("kota_without_raj")
        result = run_item_client_script(
            PROFILE,
            CLIENT_SCRIPT_PROFILES[PROFILE]["select_script"],
            "custom_select_item",
            {"custom_height": case["height"], "custom_width": case["width"]},
            available_items=[case["item_name"]],
        )
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["item_code"], "KOTA 42x24", debug)
        self.assertEqual(result["row"]["custom_cut_from_height"], 42, debug)
        self.assertEqual(result["row"]["custom_cut_from_width"], 24, debug)

    def test_kaddpa_dialog_generates_item_code_and_cut_size(self):
        """Kaddpa: Sales Invoice dialog template switch should generate `KADDPA 42x24`."""
        case, csv_row = get_required_case("kaddpa")
        result = run_item_client_script(
            PROFILE,
            CLIENT_SCRIPT_PROFILES[PROFILE]["select_script"],
            "custom_select_item",
            {"custom_height": case["height"], "custom_width": case["width"]},
            dialog_values={"item_template_filter": "KADDPA"},
            available_items=["KADDPA 42x24"],
        )
        debug = format_csv_expectation(csv_row, result)

        self.assertEqual(result["row"]["item_code"], "KADDPA 42x24", debug)
        self.assertEqual(result["row"]["custom_cut_from_height"], 42, debug)
        self.assertEqual(result["row"]["custom_cut_from_width"], 24, debug)


if __name__ == "__main__":
    unittest.main()
