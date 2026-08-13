"""Small dbt-style runner for Sales Order Client Script unit tests.

The YAML fixture starts from rows copied from ``sales order item list.csv``,
but those complete rows are editable unit-test contracts. The runner requires
all source columns without forcing edited values to remain identical to CSV.
"""

import csv
from functools import lru_cache
from pathlib import Path

import yaml

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import (
    CLIENT_SCRIPT_PROFILES,
    SALES_ORDER_ITEM_CSV,
    get_generated_select_item_code,
    get_select_item_dialog_values,
    normalize_select_item_code,
    run_item_client_script,
    to_float,
)


PROFILE = "sales_order"
UNIT_TEST_YAML = Path(__file__).with_name("data") / "sales_order_unit_tests.yml"
SOURCE_COLUMNS = (
    "Sales Order",
    "Order Date",
    "Customer Name",
    "Item Name",
    "Height",
    "Width",
    "Cut From Height",
    "Cut From Width",
    "Quantity",
    "SQFT",
    "Rate",
    "Amount",
    "Status",
)
NUMERIC_SOURCE_COLUMNS = {
    "Height",
    "Width",
    "Cut From Height",
    "Cut From Width",
    "Quantity",
    "SQFT",
    "Rate",
    "Amount",
}


@lru_cache(maxsize=1)
def load_unit_tests():
    """Load and index the dbt-style YAML definitions."""
    with UNIT_TEST_YAML.open(encoding="utf-8") as fixture:
        data = yaml.safe_load(fixture)

    tests = data.get("unit_tests", [])
    indexed = {definition["name"]: definition for definition in tests}
    if len(indexed) != len(tests):
        raise AssertionError(f"Duplicate unit-test name in {UNIT_TEST_YAML}")
    return indexed


@lru_cache(maxsize=1)
def load_source_rows():
    """Index the source-of-truth CSV by its physical, one-based row number."""
    with SALES_ORDER_ITEM_CSV.open(newline="", encoding="utf-8-sig") as csvfile:
        return {
            row_number: dict(row, _csv_row_number=row_number)
            for row_number, row in enumerate(csv.DictReader(csvfile), start=2)
        }


@lru_cache(maxsize=1)
def load_source_rows_by_signature():
    """Index CSV rows by all 13 source columns embedded in the YAML."""
    indexed = {}
    for csv_row in load_source_rows().values():
        indexed.setdefault(_source_signature(csv_row), []).append(csv_row)
    return indexed


def validate_unit_test_sources():
    """Return structural fixture problems before JavaScript is executed."""
    problems = []
    for test_name, definition in load_unit_tests().items():
        cases = definition.get("given", {}).get("rows", [])
        expected_case_names = set()

        for case in cases:
            case_name = case.get("case")
            if not case_name:
                problems.append(f"{test_name}: a given row has no case name")
                continue
            if case_name in expected_case_names:
                problems.append(f"{test_name}: duplicate case name {case_name!r}")
            expected_case_names.add(case_name)

            source_row = case.get("source_row")
            if not isinstance(source_row, dict):
                problems.append(
                    f"{test_name}.{case_name}: missing full source_row mapping"
                )
                continue

            missing_columns = [
                column for column in SOURCE_COLUMNS if column not in source_row
            ]
            extra_columns = [
                column for column in source_row if column not in SOURCE_COLUMNS
            ]
            if missing_columns or extra_columns:
                problems.append(
                    f"{test_name}.{case_name}: source_row columns differ; "
                    f"missing={missing_columns}, extra={extra_columns}"
                )
                continue

        if not cases:
            problems.append(f"{test_name}: no given rows")

    return problems


def assert_dbt_unit_test(test_case, test_name, case_name=None):
    """Run one YAML group or one named row and fail with a dbt-like diff."""
    try:
        definition = load_unit_tests()[test_name]
    except KeyError as exc:
        known = ", ".join(sorted(load_unit_tests()))
        raise AssertionError(f"Unknown unit test {test_name!r}. Known: {known}") from exc

    mismatches = []
    cases = definition["given"]["rows"]
    if case_name is not None:
        cases = [case for case in cases if case["case"] == case_name]
        if not cases:
            raise AssertionError(f"Unknown case {test_name}.{case_name}")
        definition = dict(definition, name=f"{test_name}.{case_name}")
    expected_fields = definition.get("expect", {}).get("fields", {})
    absent_fields = definition.get("expect", {}).get("absent_fields", [])

    for case in cases:
        csv_row = _get_source_row(test_name, case)
        result = _run_case(definition, case, csv_row)
        actual_row = result["row"]

        for output_field, csv_field in expected_fields.items():
            expected = _source_value(csv_row, csv_field)
            actual = _actual_value(definition["kind"], output_field, result)
            if not _values_match(output_field, expected, actual):
                mismatches.append(
                    _mismatch(
                        test_name,
                        case,
                        csv_row,
                        output_field,
                        expected,
                        actual,
                    )
                )

        for output_field in absent_fields:
            if output_field in actual_row:
                mismatches.append(
                    _mismatch(
                        test_name,
                        case,
                        csv_row,
                        output_field,
                        "<absent>",
                        actual_row[output_field],
                    )
                )

    if mismatches:
        test_case.fail(_format_failure(definition, cases, mismatches))


def assert_dbt_unit_case(test_case, test_name, case_name):
    """Run exactly one row contract as an independently reported unittest."""
    assert_dbt_unit_test(test_case, test_name, case_name=case_name)


def get_source_case(test_name, case_name):
    """Return a YAML case and its authoritative CSV row for focused behavior tests."""
    definition = load_unit_tests()[test_name]
    for case in definition["given"]["rows"]:
        if case["case"] == case_name:
            return case, _get_source_row(test_name, case)
    raise AssertionError(f"Case {case_name!r} not found in unit test {test_name!r}")


def _get_source_row(test_name, case):
    source_row = case.get("source_row")
    if not isinstance(source_row, dict):
        raise AssertionError(
            f"{test_name}.{case['case']}: missing full source_row mapping"
        )

    missing_columns = [column for column in SOURCE_COLUMNS if column not in source_row]
    extra_columns = [column for column in source_row if column not in SOURCE_COLUMNS]
    if missing_columns or extra_columns:
        raise AssertionError(
            f"{test_name}.{case['case']}: source_row must contain exactly all CSV "
            f"columns; missing={missing_columns}, extra={extra_columns}"
        )

    fixture_row = dict(source_row)
    fixture_row["_csv_row_number"] = _infer_csv_row_number(source_row)
    return fixture_row


def _infer_csv_row_number(source_row):
    """Best-effort source location for reports; fixture values remain editable."""
    exact_matches = load_source_rows_by_signature().get(
        _source_signature(source_row),
        [],
    )
    if exact_matches:
        return exact_matches[0]["_csv_row_number"]

    identity_columns = (
        "Sales Order",
        "Item Name",
        "Height",
        "Width",
        "Quantity",
    )
    for csv_row in load_source_rows().values():
        if all(
            _canonical_source_value(column, csv_row.get(column))
            == _canonical_source_value(column, source_row.get(column))
            for column in identity_columns
        ):
            return csv_row["_csv_row_number"]
    return "YAML fixture"


def _source_signature(row):
    return tuple(
        _canonical_source_value(column, row.get(column))
        for column in SOURCE_COLUMNS
    )


def _canonical_source_value(column, value):
    if column in NUMERIC_SOURCE_COLUMNS:
        return to_float(value)
    return str(value or "")


def _run_case(definition, case, csv_row):
    kind = definition["kind"]
    profile = CLIENT_SCRIPT_PROFILES[PROFILE]
    row = {
        "item_code": csv_row["Item Name"],
        "custom_height": to_float(csv_row["Height"]),
        "custom_width": to_float(csv_row["Width"]),
        "custom_quantity": to_float(csv_row["Quantity"]),
    }
    row.update(case.get("row", {}))

    dialog_values = None
    available_items = None
    apply_dialog = False
    if kind == "select_item":
        row.pop("item_code")
        row.pop("custom_quantity")
        dialog_values = get_select_item_dialog_values(csv_row)
        dialog_values.update(case.get("dialog", {}))
        available_items = [normalize_select_item_code(csv_row["Item Name"])]
        apply_dialog = True

    return run_item_client_script(
        PROFILE,
        profile[definition["script_key"]],
        case.get("event", definition["event"]),
        row,
        dialog_values=dialog_values,
        available_items=available_items,
        apply_dialog=apply_dialog,
    )


def _source_value(csv_row, csv_field):
    value = csv_row[csv_field]
    if csv_field == "Item Name":
        return normalize_select_item_code(value)
    return to_float(value)


def _actual_value(kind, output_field, result):
    if kind == "select_item" and output_field == "item_code":
        return get_generated_select_item_code(result)
    return result["row"].get(output_field)


def _values_match(output_field, expected, actual):
    if output_field == "item_code":
        return (
            normalize_select_item_code(str(expected)).casefold()
            == normalize_select_item_code(str(actual)).casefold()
        )
    if actual is None:
        return False
    return abs(to_float(actual) - to_float(expected)) <= 0.01


def _mismatch(test_name, case, csv_row, field, expected, actual):
    return {
        "test": test_name,
        "case": case["case"],
        "csv_row": csv_row["_csv_row_number"],
        "sales_order": csv_row["Sales Order"],
        "item": csv_row["Item Name"],
        "height": to_float(csv_row["Height"]),
        "width": to_float(csv_row["Width"]),
        "quantity": to_float(csv_row["Quantity"]),
        "field": field,
        "expected": expected,
        "actual": actual,
        "difference": _numeric_difference(expected, actual),
    }


def _format_failure(definition, cases, mismatches):
    lines = [
        f"dbt-style unit test failure: {definition['name']}",
        f"Rule: {definition.get('description', '')}",
        f"Source: {SALES_ORDER_ITEM_CSV.name}",
        f"Cases tested: {len(cases)} | Mismatched fields: {len(mismatches)}",
    ]

    mismatches_by_case = {}
    for mismatch in mismatches:
        mismatches_by_case.setdefault(mismatch["case"], []).append(mismatch)

    for case_name, case_mismatches in mismatches_by_case.items():
        first = case_mismatches[0]
        lines.extend(
            [
                "",
                f"Case: {case_name}",
                (
                    f"CSV row {first['csv_row']} | Sales Order {first['sales_order']}"
                ),
                f"Item: {first['item']}",
                (
                    "Input: "
                    f"height={_render_cell(first['height'])}, "
                    f"width={_render_cell(first['width'])}, "
                    f"quantity={_render_cell(first['quantity'])}"
                ),
                _format_field_diff_table(case_mismatches),
            ]
        )

    return "\n".join(lines)


def _format_field_diff_table(mismatches):
    columns = ("field", "expected", "actual", "difference")
    rendered = [
        {column: _render_cell(row[column]) for column in columns}
        for row in mismatches
    ]
    widths = {
        column: max(len(column), *(len(row[column]) for row in rendered))
        for column in columns
    }
    header = " | ".join(column.upper().ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)
    body = [
        " | ".join(row[column].ljust(widths[column]) for column in columns)
        for row in rendered
    ]
    return "\n".join([header, separator, *body])


def _numeric_difference(expected, actual):
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return round(actual - expected, 4)
    return ""


def _render_cell(value):
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
