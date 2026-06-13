# Client Script Tests

These tests run exported Frappe Client Scripts from
`kgmaccount/fixtures/client_script.json` inside a small fake browser/Frappe
environment using Node.js.

The shared input data is:

```text
/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv
```

## What Is Checked

`custom_select_item` tests loop every Kota row and every Kaddpa row in the
shared CSV. Kota and Kaddpa are kept in separate test files/logs because both
are selectable from the dialog, but they can fail for different reasons.

The Select Item checks cover only the item-selection responsibility:

- dialog inputs from CSV `Height` and `Width`
- generated `item_code`
- generated `custom_cut_from_height`
- generated `custom_cut_from_width`

They do not check Item Price or price list rates. Development server price
data can be wrong, and the Select Item Client Script only chooses the item code.

Sqft and mould tests compare the Client Script output with the CSV `SQFT` and
cut-size columns.

## Run Sales Order Client Script Tests

From `/workspace/development/frappe-bench`:

```sh
./env/bin/python -m unittest discover apps/kgmaccount/kgmaccount/tests/client_scripts/sales_order -v
```

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
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.sales_order.test_select_item_kaddpa_client_script -v
```

Quotation:

```sh
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.quotation.test_select_item_kaddpa_client_script -v
```

Sales Invoice:

```sh
./env/bin/python -m unittest apps.kgmaccount.kgmaccount.tests.client_scripts.sales_invoice.test_select_item_kaddpa_client_script -v
```

## Logs

Failed all-row checks write JSON and CSV logs here:

```text
/workspace/development/frappe-bench/apps/kgmaccount/kgmaccount/tests/logs/select_item/
/workspace/development/frappe-bench/apps/kgmaccount/kgmaccount/tests/logs/sqft/
/workspace/development/frappe-bench/apps/kgmaccount/kgmaccount/tests/logs/mould/
```

Important Select Item logs:

```text
logs/select_item/sales_order_select_item_failed_rows.csv
logs/select_item/quotation_select_item_failed_rows.csv
logs/select_item/sales_invoice_select_item_failed_rows.csv
logs/select_item/sales_order_kaddpa_select_item_failed_rows.csv
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
