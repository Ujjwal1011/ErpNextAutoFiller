"""dbt-style unit tests for Sales Order mould calculation and dialog scripts."""

import unittest

from kgmaccount.tests.client_scripts.sales_order.dbt_unit_test_utils import (
    assert_dbt_unit_test,
    get_source_case,
)
from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    CLIENT_SCRIPT_PROFILES,
    run_item_client_script,
    to_float,
)


PROFILE = "sales_order"


class TestSalesOrderMouldUnitTests(unittest.TestCase):
    def test_standard_mould_factor_six(self):
        assert_dbt_unit_test(self, "mould_factor_six")

    def test_mouldg_factor_three(self):
        assert_dbt_unit_test(self, "mouldg_factor_three")

    def test_job_work_factor_three_with_all_sides(self):
        assert_dbt_unit_test(self, "job_work_all_sides")

    def test_mould_dialog_copies_source_dimensions(self):
        case, csv_row = get_source_case("mould_factor_six", "standard_mould")
        result = self._run_dialog(
            csv_row,
            {
                side.removeprefix("custom_"): value
                for side, value in case["row"].items()
            },
            row_name="MOULD-ROW",
        )
        output = result["row"]

        self.assertEqual(output["custom_height"], to_float(csv_row["Height"]))
        self.assertEqual(output["custom_width"], to_float(csv_row["Width"]))
        self.assertEqual(output["custom_left"], 1)
        self.assertEqual(output["custom_top"], 1)

    def test_job_work_dialog_defaults_to_all_sides(self):
        _case, csv_row = get_source_case("job_work_all_sides", "tiles_job_work")
        result = self._run_dialog(csv_row, {}, row_name="JOB-WORK-ROW")
        output = result["row"]

        self.assertEqual(output["custom_right"], 1)
        self.assertEqual(output["custom_left"], 1)
        self.assertEqual(output["custom_top"], 1)
        self.assertEqual(output["custom_bottom"], 1)

    def _run_dialog(self, csv_row, dialog_values, row_name):
        height = to_float(csv_row["Height"])
        width = to_float(csv_row["Width"])
        return run_item_client_script(
            PROFILE,
            CLIENT_SCRIPT_PROFILES[PROFILE]["mould_dialog_script"],
            "item_code",
            {"name": row_name, "item_code": csv_row["Item Name"]},
            dialog_values=dialog_values,
            doc_items=[
                {
                    "name": "SOURCE-DIMENSION-ROW",
                    "custom_height": height,
                    "custom_width": width,
                },
                {"name": row_name, "item_code": csv_row["Item Name"]},
            ],
        )


if __name__ == "__main__":
    unittest.main()
