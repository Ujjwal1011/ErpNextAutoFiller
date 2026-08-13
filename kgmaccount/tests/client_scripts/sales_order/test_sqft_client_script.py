"""Fifty-five named dbt-style unit tests for the Sales Order SQFT script."""

import unittest

from kgmaccount.tests.client_scripts.sales_order.dbt_unit_test_utils import (
    assert_dbt_unit_case,
    load_unit_tests,
)


class TestSalesOrderSqftUnitTests(unittest.TestCase):
    """Methods are attached below so each YAML row is reported separately."""


def _make_sqft_test(group_name, case_name):
    def test(self):
        assert_dbt_unit_case(self, group_name, case_name)

    test.__name__ = f"test_{group_name.removeprefix('sqft_')}__{case_name}"
    test.__doc__ = f"CSV-backed SQFT contract: {group_name}.{case_name}."
    return test


for _group_name, _definition in load_unit_tests().items():
    if _definition["kind"] != "sqft":
        continue
    for _case in _definition["given"]["rows"]:
        _method = _make_sqft_test(_group_name, _case["case"])
        setattr(TestSalesOrderSqftUnitTests, _method.__name__, _method)


if __name__ == "__main__":
    unittest.main()
