"""Run Sales Order Client Script tests with colored unittest output.

Examples, from the bench directory::

    ./env/bin/python apps/kgmaccount/kgmaccount/tests/client_scripts/sales_order/run_tests.py
    ./env/bin/python apps/kgmaccount/kgmaccount/tests/client_scripts/sales_order/run_tests.py --sqft-only
    ./env/bin/python apps/kgmaccount/kgmaccount/tests/client_scripts/sales_order/run_tests.py --color always
"""

import argparse
import os
import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[4]
SALES_ORDER_TEST_DIR = Path(__file__).resolve().parent
SQFT_TEST_MODULE = (
    "kgmaccount.tests.client_scripts.sales_order.test_sqft_client_script"
)

ANSI = {
    "cyan": "\033[36m",
    "green": "\033[32m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "reset": "\033[0m",
}


class ColorTextTestResult(unittest.TextTestResult):
    """TextTestResult that colors verbose test names and statuses."""

    def __init__(self, stream, descriptions, verbosity, color_enabled):
        super().__init__(stream, descriptions, verbosity)
        self.color_enabled = color_enabled
        self.successful_tests = []

    def _color(self, text, color):
        if not self.color_enabled:
            return text
        return f"{ANSI[color]}{text}{ANSI['reset']}"

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        if self.showAll:
            self.stream.write(self._color(self.getDescription(test), "cyan"))
            self.stream.write(" ... ")
            self.stream.flush()

    def getDescription(self, test):
        """Return a short business-oriented name instead of Python's full ID."""
        method_name = getattr(test, "_testMethodName", str(test))
        readable_name = method_name.removeprefix("test_")

        if "__" in readable_name:
            group, case = readable_name.split("__", 1)
            return f"SQFT | {_humanize(group)} | {_humanize(case)}"

        class_name = test.__class__.__name__
        if "SelectItem" in class_name:
            area = "SELECT ITEM"
        elif "Mould" in class_name:
            area = "MOULD"
        elif "UnitTestData" in class_name:
            area = "TEST DATA"
        else:
            area = "SALES ORDER"
        return f"{area} | {_humanize(readable_name)}"

    def _write_status(self, status, color, dot):
        if self.showAll:
            self.stream.writeln(self._color(status, color))
        elif self.dots:
            self.stream.write(self._color(dot, color))
            self.stream.flush()

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        self.successful_tests.append(test)
        self._write_status("✓ PASS", "green", ".")

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        self._write_status("✗ ERROR", "red", "E")

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        self._write_status("✗ FAIL", "red", "F")

    def addSkip(self, test, reason):
        unittest.TestResult.addSkip(self, test, reason)
        self._write_status(f"skipped {reason!r}", "yellow", "s")

    def addExpectedFailure(self, test, err):
        unittest.TestResult.addExpectedFailure(self, test, err)
        self._write_status("expected failure", "yellow", "x")

    def addUnexpectedSuccess(self, test):
        unittest.TestResult.addUnexpectedSuccess(self, test)
        self._write_status("unexpected success", "red", "u")

    def printErrorList(self, flavour, errors):
        for number, (test, error) in enumerate(errors, start=1):
            self.stream.writeln(self._color(self.separator1, "red"))
            title = f"{number}. {flavour} | {self.getDescription(test)}"
            self.stream.writeln(self._color(title, "red"))
            self.stream.writeln(self._color(self.separator2, "red"))
            self.stream.writeln(_compact_dbt_failure(error))


class ColorTextTestRunner(unittest.TextTestRunner):
    def __init__(self, *args, color_enabled=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.color_enabled = color_enabled

    def _makeResult(self):
        return ColorTextTestResult(
            self.stream,
            self.descriptions,
            self.verbosity,
            self.color_enabled,
        )

    def run(self, test):
        result = super().run(test)
        self._print_area_summary(result)
        return result

    def _print_area_summary(self, result):
        summary = {}

        def add(test, status):
            area = _test_area(test)
            counts = summary.setdefault(
                area,
                {"passed": 0, "failed": 0, "errors": 0, "skipped": 0},
            )
            counts[status] += 1

        for test in result.successful_tests:
            add(test, "passed")
        for test, _error in result.failures:
            add(test, "failed")
        for test, _error in result.errors:
            add(test, "errors")
        for test, _reason in result.skipped:
            add(test, "skipped")

        if not summary:
            return

        self.stream.writeln()
        heading = _ansi_color("RESULTS BY AREA", "cyan", self.color_enabled)
        self.stream.writeln(heading)
        columns = ("area", "passed", "failed", "errors", "skipped", "total")
        rows = []
        preferred_order = ("SQFT", "SELECT ITEM", "MOULD", "TEST DATA", "OTHER")
        for area in preferred_order:
            if area not in summary:
                continue
            counts = summary[area]
            rows.append(
                {
                    "area": area,
                    **counts,
                    "total": sum(counts.values()),
                }
            )

        widths = {
            column: max(len(column), *(len(str(row[column])) for row in rows))
            for column in columns
        }
        self.stream.writeln(
            " | ".join(column.upper().ljust(widths[column]) for column in columns)
        )
        self.stream.writeln(
            "-+-".join("-" * widths[column] for column in columns)
        )
        for row in rows:
            cells = []
            for column in columns:
                value = str(row[column]).ljust(widths[column])
                if column == "passed":
                    value = _ansi_color(value, "green", self.color_enabled)
                elif column in ("failed", "errors") and row[column]:
                    value = _ansi_color(value, "red", self.color_enabled)
                elif column == "skipped" and row[column]:
                    value = _ansi_color(value, "yellow", self.color_enabled)
                cells.append(value)
            self.stream.writeln(" | ".join(cells))


def _humanize(value):
    return value.replace("_", " ").strip().title()


def _test_area(test):
    module_name = test.__class__.__module__
    if module_name.endswith("test_sqft_client_script"):
        return "SQFT"
    if module_name.endswith("test_select_item_client_script"):
        return "SELECT ITEM"
    if module_name.endswith("test_mould_client_scripts"):
        return "MOULD"
    if module_name.endswith("test_csv_test_data"):
        return "TEST DATA"
    return "OTHER"


def _compact_dbt_failure(error):
    """Remove runner internals while preserving the structured dbt diff."""
    marker = "AssertionError: dbt-style unit test failure:"
    marker_index = error.find(marker)
    if marker_index == -1:
        return error
    return error[marker_index + len("AssertionError: ") :].rstrip()


def _ansi_color(text, color, enabled):
    if not enabled:
        return text
    return f"{ANSI[color]}{text}{ANSI['reset']}"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Sales Order Client Script tests with colored output."
    )
    parser.add_argument(
        "--sqft-only",
        action="store_true",
        help="Run only the named SQFT unit tests.",
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="Color mode; auto colors interactive terminals.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Show dots instead of every test name.",
    )
    return parser.parse_args()


def should_use_color(mode):
    if mode == "always":
        return True
    if mode == "never" or os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stderr.isatty()


def build_suite(sqft_only):
    if str(APP_ROOT) not in sys.path:
        sys.path.insert(0, str(APP_ROOT))

    loader = unittest.defaultTestLoader
    if sqft_only:
        return loader.loadTestsFromName(SQFT_TEST_MODULE)
    return loader.discover(str(SALES_ORDER_TEST_DIR), pattern="test_*.py")


def main():
    args = parse_args()
    suite = build_suite(args.sqft_only)
    runner = ColorTextTestRunner(
        verbosity=1 if args.quiet else 2,
        color_enabled=should_use_color(args.color),
    )
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
