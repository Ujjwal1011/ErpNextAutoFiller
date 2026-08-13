"""Guard the analyzed CSV source and its minimal dbt-style row contracts."""

import unittest

from kgmaccount.tests.client_scripts.sales_order.dbt_unit_test_utils import (
    UNIT_TEST_YAML,
    load_unit_tests,
    validate_unit_test_sources,
)
from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    SALES_ORDER_ITEM_CSV,
)


EXPECTED_SQFT_UNIT_TESTS = 55


class TestSalesOrderUnitTestData(unittest.TestCase):
    def test_source_csv_and_unit_test_yaml_exist(self):
        self.assertTrue(SALES_ORDER_ITEM_CSV.exists(), f"Missing source CSV: {SALES_ORDER_ITEM_CSV}")
        self.assertTrue(UNIT_TEST_YAML.exists(), f"Missing unit-test YAML: {UNIT_TEST_YAML}")

    def test_every_selected_row_contains_all_source_columns(self):
        problems = validate_unit_test_sources()
        self.assertEqual(problems, [], "\n".join(problems))

    def test_sqft_has_55_independent_row_contracts(self):
        definitions = load_unit_tests()
        sqft_contract_count = sum(
            len(definition["given"]["rows"])
            for definition in definitions.values()
            if definition["kind"] == "sqft"
        )
        self.assertEqual(
            sqft_contract_count,
            EXPECTED_SQFT_UNIT_TESTS,
            "Update the data-analysis report when the representative set changes",
        )


if __name__ == "__main__":
    unittest.main()
