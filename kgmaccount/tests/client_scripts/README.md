# Client Script Tests

These tests run exported Frappe Client Scripts from
`kgmaccount/fixtures/client_script.json` inside a small fake browser/Frappe
environment using Node.js.

The shared source-of-truth data is:

```text
/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv
```

## Sales Order dbt-style unit tests

Sales Order tests do not loop all 1,231 CSV rows. The data analysis and the
selected row contracts are:

```text
sales_order/data/sales_order_item_data_analysis.md
sales_order/data/sales_order_unit_tests.yml
```

The analysis divides rows by script branch, height/width boundary, quantity
shape, polish, Rajasthan property, and mould rounding factor. The YAML
contains:

- 55 independently named SQFT calculation tests
- 16 Select Item cases
- 3 mould/running-foot cases

The guard verifies that all 55 SQFT definitions remain present. Select Item and
mould cases are counted separately. Every YAML case embeds all 13 columns from
its source record: order, date, customer, item, dimensions, cut dimensions,
quantity, SQFT, rate, amount, and status. These rows are editable unit-test
contracts: the guard requires all columns but does not reject values changed
for a scenario. When possible, the runner still infers the original CSV row
number for failure reporting. Case-specific inputs absent from the CSV, such
as mould side flags, remain beside the embedded row.

Select Item checks generated `item_code`, `custom_cut_from_height`, and
`custom_cut_from_width`. SQFT checks cut sizes and quantity where those fields
belong to the source branch. Mould tests check running feet. Rates and Item
Prices are outside these scripts' responsibility.

## Run Sales Order Client Script Tests

From `/workspace/development/frappe-bench`:

```sh
./env/bin/python apps/kgmaccount/kgmaccount/tests/client_scripts/sales_order/run_tests.py
```

The runner automatically uses colored output in an interactive terminal. To
force colors when output is being captured or piped:

```sh
./env/bin/python apps/kgmaccount/kgmaccount/tests/client_scripts/sales_order/run_tests.py --color always
```

Run only the 55 named SQFT tests:

```sh
./env/bin/python apps/kgmaccount/kgmaccount/tests/client_scripts/sales_order/run_tests.py --sqft-only
```

The standard `python -m unittest discover ... -v` command remains supported,
but Python's built-in unittest runner does not provide colored statuses.

## Run Quotation Client Script Tests

From `/workspace/development/frappe-bench`:

```sh
./env/bin/python -m unittest discover apps/kgmaccount/kgmaccount/tests/client_scripts/quotation -v
```

## Run Sales Invoice Client Script Tests

From `/workspace/development/frappe-bench`:

```sh
./env/bin/python -m unittest discover apps/kgmaccount/kgmaccount/tests/client_scripts/sales_invoice -v
```

## Run Only Select Item Tests

Sales Order:

```sh
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.sales_order.test_select_item_client_script -v
```

Quotation:

```sh
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.quotation.test_select_item_client_script -v
```

Sales Invoice:

```sh
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.sales_invoice.test_select_item_client_script -v
```

## Run Only Kaddpa Select Item Tests

Sales Order:

```sh
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.sales_order.test_select_item_client_script.TestSalesOrderSelectItemUnitTests.test_kaddpa_categories -v
```

Quotation:

```sh
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.quotation.test_select_item_kaddpa_client_script -v
```

Sales Invoice:

```sh
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.sales_invoice.test_select_item_kaddpa_client_script -v
```

## Failure output

The colored Sales Order runner prints each test once using a compact business
name. Expected CSV mismatches omit the internal Python traceback and show:

- source CSV row and Sales Order;
- item, height, width, and quantity inputs;
- field-level expected, actual, and difference values;
- final passed/failed/error counts grouped by SQFT, Select Item, Mould, and
  Test Data.

A failing row remains a normal test failure; the suite does not hide current
source-versus-script discrepancies.

The older all-row Quotation and Sales Invoice checks write logs under:

```text
/workspace/development/frappe-bench/apps/kgmaccount/kgmaccount/tests/logs/select_item/
/workspace/development/frappe-bench/apps/kgmaccount/kgmaccount/tests/logs/sqft/
/workspace/development/frappe-bench/apps/kgmaccount/kgmaccount/tests/logs/mould/
```

Important Select Item logs:

```text
logs/select_item/quotation_select_item_failed_rows.csv
logs/select_item/sales_invoice_select_item_failed_rows.csv
logs/select_item/quotation_kaddpa_select_item_failed_rows.csv
logs/select_item/sales_invoice_kaddpa_select_item_failed_rows.csv
```

Each failed-row log also keeps comparison files in separate folders:

```text
logs/select_item/*_failed_rows.csv          latest run
logs/select_item/previous/*_failed_rows.csv run before the latest run
logs/select_item/best/*_failed_rows.csv     lowest failure count seen so far
logs/select_item/summary/*_failed_rows.csv  latest, previous, best, and count differences
```

The same `previous`, `best`, and `summary` structure is used under `sqft` and
`mould` logs.

Set `KGM_TEST_DEBUG=1` to print the fake dialog values, output row, Frappe
calls, and messages for focused debugging.
