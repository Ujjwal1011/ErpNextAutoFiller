"""dbt-style unit tests for the Sales Order Select Item Client Script."""

import unittest

from kgmaccount.tests.client_scripts.sales_order.dbt_unit_test_utils import (
    assert_dbt_unit_test,
)


class TestSalesOrderSelectItemUnitTests(unittest.TestCase):
    def test_kota_dimension_boundaries(self):
        assert_dbt_unit_test(self, "select_item_kota_dimension_boundaries")

    def test_kota_finish_categories(self):
        assert_dbt_unit_test(self, "select_item_kota_finish_categories")

    def test_rajasthan_property_categories(self):
        assert_dbt_unit_test(self, "select_item_rajasthan_property_categories")

    def test_kaddpa_categories(self):
        assert_dbt_unit_test(self, "select_item_kaddpa_categories")


if __name__ == "__main__":
    unittest.main()
