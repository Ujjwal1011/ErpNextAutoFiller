"""Shared helper functions for Sales Order, Quotation, and Sales Invoice Client Script tests.

Input sources:
- Client Scripts are read from `kgmaccount/fixtures/client_script.json`.
- Test examples are read from the user-provided CSV file
  `/workspace/development/frappe-bench/apps/kgmaccount/sales order item list.csv`.
- The CSV fields used by the item tests are `Item Name`, `Height`, `Width`,
  `Quantity`, `SQFT`, `Cut From Height`, `Cut From Width`, and `Rate`.

How checks work:
- `CLIENT_SCRIPT_PROFILES` maps each parent DocType to its child table doctype
  and exact exported Client Script fixture names.
- The helpers convert CSV fields into the row shape expected by Frappe browser
  Client Scripts: `item_code`, `custom_height`, `custom_width`,
  `custom_quantity`, and mould side flags.
- JavaScript is run in Node.js with a fake Frappe browser environment for
  `frappe.ui.form.on`, `frappe.model.set_value`, `frappe.get_doc`,
  `frappe.ui.Dialog`, and the item lookup call used by the select-item dialog.
- Tests compare the mutated row returned by the Client Script with the CSV
  expected values.

Debugging:
- Set `KGM_TEST_DEBUG=1` to print the fake dialog values, Client Script output
  row, Frappe calls, and messages.
- Failed all-row CSV checks write JSON logs to `kgmaccount/tests/logs` by
  default, or to `KGM_TEST_LOG_DIR` when that environment variable is set.
"""

import csv
import json
import os
import shutil
import subprocess
from pathlib import Path


APP_PACKAGE = Path(__file__).resolve().parents[3]
APP_ROOT = APP_PACKAGE.parent
CLIENT_SCRIPT_FIXTURE = APP_PACKAGE / "fixtures" / "client_script.json"
SALES_ORDER_ITEM_CSV = APP_ROOT / "sales order item list.csv"
DEFAULT_TEST_LOG_DIR = APP_PACKAGE / "tests" / "logs"

CLIENT_SCRIPT_PROFILES = {
    "sales_order": {
        "label": "Sales Order",
        "child_doctype": "Sales Order Item",
        "select_script": "Sales-Order Select Item",
        "sqft_script": "Sales-Order Kota Kaddpaa Granite Neno Calculation",
        "mould_script": "Sales-Order Kota Granite Moulding Calculation",
        "mould_dialog_script": "Sales-Order Moulding Dialog Box",
        "select_item_log": "sales_order_select_item_failed_rows.json",
        "sqft_log": "sales_order_sqft_failed_rows.json",
        "mould_log": "sales_order_mould_failed_rows.json",
    },
    "quotation": {
        "label": "Quotation",
        "child_doctype": "Quotation Item",
        "select_script": "Quotation Select Item",
        "sqft_script": "Quotation Kota Kaddpaa Granite Neno Calculation",
        "mould_script": "Qutotation Kota Granite Moulding Calculation",
        "mould_dialog_script": "Quotation Moulding Dialog Box",
        "select_item_log": "quotation_select_item_failed_rows.json",
        "sqft_log": "quotation_sqft_failed_rows.json",
        "mould_log": "quotation_mould_failed_rows.json",
    },
    "sales_invoice": {
        "label": "Sales Invoice",
        "child_doctype": "Sales Invoice Item",
        "select_script": "Sales-Invoice Select Item",
        "sqft_script": "Sales-Invoice Kota Kaddpaa Granite Neno Calculation",
        "mould_script": "Sales-Invoice Kota Granite Moulding Calculation",
        "mould_dialog_script": "Sales-Invoice Moulding Dialog Box",
        "select_item_log": "sales_invoice_select_item_failed_rows.json",
        "sqft_log": "sales_invoice_sqft_failed_rows.json",
        "mould_log": "sales_invoice_mould_failed_rows.json",
    },
}

# Stable examples from `sales order item list.csv` that every DocType-specific
# client-script test can reuse. The CSV remains the single source of expected
# sqft, cut size, and rate data.
REQUIRED_CSV_CASES = {
    "raj_kota": {
        "item_name": "KOTA 24x24 RAJ G",
        "height": 23,
        "width": 23,
        "quantity": 100,
    },
    "kota_without_raj": {
        "item_name": "KOTA 42x24",
        "height": 41,
        "width": 23,
        "quantity": 2,
    },
    "without_kota": {
        "item_name": "Lakha Red",
        "height": 66,
        "width": 12,
        "quantity": 2,
    },
    "kaddpa": {
        "item_name": "Kaddpa 42x24",
        "height": 41,
        "width": 23,
        "quantity": 1,
    },
    "mould": {
        "item_name": "Dhar Mould",
        "height": 35,
        "width": 29,
        "quantity": 1,
    },
    "mouldg": {
        "item_name": "Dhar MouldG",
        "height": 70,
        "width": 3,
        "quantity": 1,
    },
}

# Backward-compatible names for older flat tests or WhatsApp tests that import
# this module through `kgmaccount.tests.client_script_test_utils`.
REQUIRED_SALES_ORDER_CSV_CASES = REQUIRED_CSV_CASES


def to_float(value):
    """Convert CSV text to float using zero for blank values."""
    return float(value or 0)


def get_profile(profile_name):
    """Return the Client Script profile for one tested DocType."""
    try:
        return CLIENT_SCRIPT_PROFILES[profile_name]
    except KeyError as exc:
        known = ", ".join(sorted(CLIENT_SCRIPT_PROFILES))
        raise AssertionError(f"Unknown Client Script test profile {profile_name!r}. Known: {known}") from exc


def iter_item_csv_rows():
    """Yield every row from the user-provided item CSV with a useful row number."""
    with SALES_ORDER_ITEM_CSV.open(newline="") as csvfile:
        for row_number, row in enumerate(csv.DictReader(csvfile), start=2):
            row["_csv_row_number"] = row_number
            yield row


def iter_sales_order_item_csv_rows():
    """Compatibility wrapper for older Sales Order test names."""
    yield from iter_item_csv_rows()


def is_mould_or_mouldg_row(csv_row):
    """Return True for rows handled by the mould running-foot Client Script."""
    item_code = csv_row["Item Name"].lower()
    return "mould" in item_code or "mouldg" in item_code or "tiles" in item_code


def is_sqft_calculation_row(csv_row):
    """Return True for rows handled by the Kota/Kaddpa/default sqft Client Script."""
    item_code = csv_row["Item Name"].lower()
    strict_exclusions = ["mould", "mouldg", "hole", "farma", "tiles"]
    return (
        not any(exclusion in item_code for exclusion in strict_exclusions)
        and to_float(csv_row["Height"]) > 0
        and to_float(csv_row["Width"]) > 0
        and to_float(csv_row["Quantity"]) > 0
    )


def is_kota_item_row(csv_row):
    """Return True when a CSV row is a Kota item handled by the select-item dialog."""
    return csv_row["Item Name"].strip().upper().startswith("KOTA")


def is_kaddpa_item_row(csv_row):
    """Return True when a CSV row is a Kaddpa item handled by the select-item dialog."""
    return csv_row["Item Name"].strip().upper().startswith("KADDPA")


def get_select_item_dialog_values(csv_row):
    """Infer Select Item dialog values from any CSV item code.

    Kota and Kaddpa rows are mapped to the dialog's template controls. Other
    rows are left as the dialog default, which intentionally records them as
    mismatches when the Select Item dialog cannot reproduce the CSV item code.
    """
    item_code = csv_row["Item Name"].strip()
    tokens = item_code.split()
    values = {}
    if tokens and tokens[0].upper().startswith("KADDPA"):
        values["item_template_filter"] = "KADDPA"
        suffix_set = {token.upper() for token in tokens[2:]}
        kaddpa_polish_by_suffix = {
            "FIN": "Fine",
            "DP": "DP",
            "UNC": "Uncut",
            "LDR": "Ledhar",
            "RIV": "River",
            "MIR": "Mirror",
            "RUF": "Rough",
            "ROU": "Rough",
        }
        for suffix, polish_type in kaddpa_polish_by_suffix.items():
            if suffix in suffix_set:
                values["polish_type"] = polish_type
                break
        return values
    if not tokens or not tokens[0].upper().startswith("KOTA"):
        return values

    suffix_tokens = [token.upper() for token in tokens[2:]]
    suffix_set = set(suffix_tokens)

    polish_by_suffix = {
        "FIN": "Fine",
        "DP": "DP",
        "UNC": "Uncut",
        "LDR": "Ledhar",
        "RIV": "River",
        "MIR": "Mirror",
    }

    if "RAJ" in suffix_set:
        values["custom_is_rajsthan"] = 1
        if "G" in suffix_set:
            values["custom_is_gadela"] = 1
        if "P" in suffix_set:
            values["custom_is_patala"] = 1
        if "J" in suffix_set:
            values["custom_is_jada"] = 1
        if "RUF" in suffix_set:
            values["custom_is_rough"] = 1
    else:
        for suffix, polish_type in polish_by_suffix.items():
            if suffix in suffix_set:
                values["polish_type"] = polish_type
                break
        if "RUF" in suffix_set:
            values["polish_type"] = "Rough"

    return values


def get_kota_select_item_dialog_values(csv_row):
    """Compatibility wrapper for older all-Kota Select Item tests."""
    return get_select_item_dialog_values(csv_row)


def get_client_script(script_name):
    """Return the current exported Client Script text by script name."""
    with CLIENT_SCRIPT_FIXTURE.open() as fixture:
        scripts = json.load(fixture)

    for script in scripts:
        if script["name"] == script_name:
            return script["script"]

    raise AssertionError(f"Client Script not found in fixture: {script_name}")


def get_item_csv_row(item_name, height, width, quantity):
    """Find the exact CSV example row used as the expected business result."""
    with SALES_ORDER_ITEM_CSV.open(newline="") as csvfile:
        for row in csv.DictReader(csvfile):
            if (
                row["Item Name"] == item_name
                and float(row["Height"]) == float(height)
                and float(row["Width"]) == float(width)
                and float(row["Quantity"]) == float(quantity)
            ):
                return row

    raise AssertionError(
        f"CSV case not found in {SALES_ORDER_ITEM_CSV} for "
        f"{item_name} height={height} width={width} quantity={quantity}"
    )


def get_sales_order_item_csv_row(item_name, height, width, quantity):
    """Compatibility wrapper for the old Sales Order-specific helper name."""
    return get_item_csv_row(item_name, height, width, quantity)


def get_required_case(case_name):
    """Return one required CSV-backed test case by stable case name."""
    case = REQUIRED_CSV_CASES[case_name]
    row = get_item_csv_row(
        case["item_name"],
        case["height"],
        case["width"],
        case["quantity"],
    )
    return case, row


def get_required_sales_order_case(case_name):
    """Compatibility wrapper for the old Sales Order-specific helper name."""
    return get_required_case(case_name)


def run_item_client_script(
    profile_name,
    script_name,
    event_name,
    row,
    dialog_values=None,
    available_items=None,
    doc_items=None,
    apply_dialog=True,
):
    """Run one exported child-table Client Script in a fake browser/Frappe shell.

    Arguments:
        profile_name: `sales_order` or `quotation`; controls the child doctype.
        script_name: Name of the Client Script in `fixtures/client_script.json`.
        event_name: Child table event to trigger, for example `item_code`.
        row: Initial child-table row values before the script runs.
        dialog_values: Values to place into the fake dialog before pressing Apply.
        available_items: Item codes that the fake `frappe.client.get_list` can find.
        doc_items: Optional full item table, used by mould tests to copy
            dimensions from the previous row.
        apply_dialog: Set to False for calculation scripts that do not open a dialog.
    """
    runner = r"""
const vm = require("vm");
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));

const cdt = payload.child_doctype;
const cdn = payload.row.name || "ROW-1";
const row = Object.assign({ name: cdn }, payload.row);
const handlers = {};
const calls = [];
const messages = [];
let lastDialog = null;

function emptyJquery() {
  return {
    length: 0,
    off() { return this; },
    on() { return this; },
    find() { return this; },
    closest() { return this; },
    first() { return this; },
    attr() { return undefined; },
    focus() {}
  };
}

const docItems = payload.doc_items || [row];
for (const item of docItems) {
  if (!item.name) item.name = item === row ? cdn : `ROW-${docItems.indexOf(item) + 1}`;
}
if (!docItems.some(item => item.name === cdn)) docItems.push(row);

const context = {
  console: { log() {}, warn() {}, error() {} },
  setTimeout(fn) { fn(); return 0; },
  clearTimeout() {},
  __: value => value,
  $: emptyJquery,
  locals: { [cdt]: { [cdn]: row } },
};

for (const item of docItems) {
  context.locals[cdt][item.name] = item.name === cdn ? row : item;
}

const frm = {
  doc: { items: docItems.map(item => item.name === cdn ? row : item) },
  refresh_field(fieldname) { calls.push({ type: "refresh_field", fieldname }); },
  get_field() {
    return {
      df: {},
      set_focus() { calls.push({ type: "focus" }); },
      $wrapper: { find: emptyJquery },
    };
  },
  $wrapper: { find: emptyJquery },
};

class FakeDialog {
  constructor(opts) {
    this.opts = opts;
    this.fieldMap = {};
    this.values = {};
    for (const field of opts.fields || []) {
      if (!field.fieldname) continue;
      this.fieldMap[field.fieldname] = field;
      if (Object.prototype.hasOwnProperty.call(field, "default")) {
        this.values[field.fieldname] = field.default;
      }
    }
    lastDialog = this;
  }
  get_value(fieldname) {
    return this.values[fieldname];
  }
  set_value(fieldname, value) {
    this.values[fieldname] = value;
    const field = this.fieldMap[fieldname];
    if (field && typeof field.onchange === "function") field.onchange();
  }
  get_field(fieldname) {
    const field = this.fieldMap[fieldname] || { fieldname };
    return { df: field, refresh() {} };
  }
  show() { this.shown = true; }
  hide() { this.hidden = true; }
}

context.frappe = {
  ui: {
    form: {
      on(doctype, eventMap) {
        handlers[doctype] = Object.assign(handlers[doctype] || {}, eventMap || {});
      },
    },
    Dialog: FakeDialog,
  },
  get_doc(targetCdt, targetCdn) {
    return context.locals[targetCdt][targetCdn];
  },
  model: {
    set_value(targetCdt, targetCdn, fieldOrValues, value) {
      if (targetCdt !== cdt || targetCdn !== cdn) return Promise.resolve();
      if (typeof fieldOrValues === "string") {
        row[fieldOrValues] = value;
      } else if (fieldOrValues && typeof fieldOrValues === "object") {
        Object.assign(row, fieldOrValues);
      }
      calls.push({ type: "set_value", fieldOrValues, value });
      return Promise.resolve();
    },
  },
  call(opts) {
    const target = opts.args && opts.args.filters && opts.args.filters.item_code;
    const found = (payload.available_items || []).find(item => item === target);
    calls.push({ type: "call", method: opts.method, target });
    if (opts.callback) opts.callback({ message: found ? [{ item_code: found }] : [] });
  },
  msgprint(message) {
    messages.push(String(message));
  },
};

vm.createContext(context);
vm.runInContext(payload.script, context, { timeout: 5000 });

const handler = handlers[cdt] && handlers[cdt][payload.event_name];
if (typeof handler !== "function") {
  throw new Error(`Handler not registered for ${cdt}.${payload.event_name}`);
}

handler(frm, cdt, cdn);

if (lastDialog && payload.dialog_values) {
  for (const [fieldname, value] of Object.entries(payload.dialog_values)) {
    lastDialog.set_value(fieldname, value);
  }
}

if (lastDialog && payload.apply_dialog !== false && typeof lastDialog.opts.primary_action === "function") {
  lastDialog.opts.primary_action(lastDialog.values);
}

console.log(JSON.stringify({
  row,
  dialog_values: lastDialog ? lastDialog.values : null,
  dialog_title: lastDialog ? lastDialog.opts.title : null,
  calls,
  messages,
}));
"""
    profile = get_profile(profile_name)
    payload = {
        "script": get_client_script(script_name),
        "child_doctype": profile["child_doctype"],
        "event_name": event_name,
        "row": row,
        "dialog_values": dialog_values or {},
        "available_items": available_items or [],
        "doc_items": doc_items,
        "apply_dialog": apply_dialog,
    }
    result = subprocess.run(
        [os.environ.get("NODE_BINARY", "node"), "-e", runner],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    result_json = json.loads(result.stdout)
    if os.environ.get("KGM_TEST_DEBUG") == "1":
        print(format_client_script_debug(script_name, event_name, payload, result_json))
    return result_json


def run_sales_order_item_client_script(*args, **kwargs):
    """Compatibility wrapper for existing Sales Order tests."""
    return run_item_client_script("sales_order", *args, **kwargs)


def run_item_client_script_for_rows(profile_name, script_name, event_name, csv_rows):
    """Run a non-dialog child-table Client Script against many CSV rows in Node."""
    runner = r"""
const vm = require("vm");
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
const cdt = payload.child_doctype;
const handlers = {};
const results = [];
const calls = [];

const context = {
  console: { log() {}, warn() {}, error() {} },
  setTimeout(fn) { fn(); return 0; },
  clearTimeout() {},
  locals: { [cdt]: {} },
  frappe: {
    ui: { form: { on(doctype, eventMap) {
      handlers[doctype] = Object.assign(handlers[doctype] || {}, eventMap || {});
    }}},
    get_doc(targetCdt, targetCdn) {
      return context.locals[targetCdt][targetCdn];
    },
    model: { set_value(targetCdt, targetCdn, fieldOrValues, value) {
      const row = context.locals[targetCdt] && context.locals[targetCdt][targetCdn];
      if (!row) return Promise.resolve();
      if (typeof fieldOrValues === "string") {
        row[fieldOrValues] = value;
      } else if (fieldOrValues && typeof fieldOrValues === "object") {
        Object.assign(row, fieldOrValues);
      }
      calls.push({ row: targetCdn, fieldOrValues, value });
      return Promise.resolve();
    }}
  }
};

vm.createContext(context);
vm.runInContext(payload.script, context, { timeout: 5000 });
const handler = handlers[cdt] && handlers[cdt][payload.event_name];
if (typeof handler !== "function") {
  throw new Error(`Handler not registered for ${cdt}.${payload.event_name}`);
}

for (const inputRow of payload.rows) {
  const cdn = inputRow.name;
  const row = Object.assign({}, inputRow);
  context.locals[cdt][cdn] = row;
  const frm = {
    doc: { items: [row] },
    refresh_field(fieldname) { calls.push({ row: cdn, type: "refresh_field", fieldname }); },
  };
  handler(frm, cdt, cdn);
  results.push({ name: cdn, row });
}

console.log(JSON.stringify({ results, calls }));
"""
    rows = []
    for index, csv_row in enumerate(csv_rows):
        rows.append(
            {
                "name": f"CSV-ROW-{csv_row['_csv_row_number']}-{index}",
                "item_code": csv_row["Item Name"],
                "custom_height": to_float(csv_row["Height"]),
                "custom_width": to_float(csv_row["Width"]),
                "custom_quantity": to_float(csv_row["Quantity"]),
                "custom_left": int(csv_row.get("custom_left") or 0),
                "custom_right": int(csv_row.get("custom_right") or 0),
                "custom_top": int(csv_row.get("custom_top") or 0),
                "custom_bottom": int(csv_row.get("custom_bottom") or 0),
            }
        )

    payload = {
        "script": get_client_script(script_name),
        "child_doctype": get_profile(profile_name)["child_doctype"],
        "event_name": event_name,
        "rows": rows,
    }
    result = subprocess.run(
        [os.environ.get("NODE_BINARY", "node"), "-e", runner],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)["results"]


def run_sales_order_item_client_script_for_rows(*args, **kwargs):
    """Compatibility wrapper for existing Sales Order tests."""
    return run_item_client_script_for_rows("sales_order", *args, **kwargs)


def format_client_script_debug(script_name, event_name, payload, result):
    """Build a readable debug block for a client-script test case."""
    return (
        "\n[KGM CLIENT SCRIPT DEBUG]\n"
        f"script: {script_name}\n"
        f"event: {event_name}\n"
        f"child doctype: {payload['child_doctype']}\n"
        f"input row: {json.dumps(payload['row'], indent=2, sort_keys=True)}\n"
        f"dialog input: {json.dumps(payload['dialog_values'], indent=2, sort_keys=True)}\n"
        f"available items: {json.dumps(payload['available_items'], indent=2, sort_keys=True)}\n"
        f"output row: {json.dumps(result['row'], indent=2, sort_keys=True)}\n"
        f"dialog output: {json.dumps(result['dialog_values'], indent=2, sort_keys=True)}\n"
        f"frappe calls: {json.dumps(result['calls'], indent=2, sort_keys=True)}\n"
        f"messages: {json.dumps(result['messages'], indent=2, sort_keys=True)}\n"
    )


def format_csv_expectation(csv_row, result):
    """Return a short assertion message showing CSV input and Client Script output."""
    return (
        f"CSV expected row={dict(csv_row)}; "
        f"client script output row={result['row']}; "
        f"dialog={result.get('dialog_values')}; "
        f"calls={result.get('calls')}; "
        f"messages={result.get('messages')}"
    )


def get_generated_select_item_code(result):
    """Return the item code searched by the dialog, even when item lookup fails."""
    for call in result.get("calls", []):
        if call.get("type") == "call" and call.get("target"):
            return call["target"]
    return result["row"].get("item_code")


def collect_select_item_mismatches(profile_name, csv_rows, case_sensitive_item_code=True):
    """Run Select Item for CSV rows and return rows that do not match expected output."""
    profile = CLIENT_SCRIPT_PROFILES[profile_name]
    mismatches = []
    for csv_row in csv_rows:
        result = run_item_client_script(
            profile_name,
            profile["select_script"],
            "custom_select_item",
            {
                "custom_height": to_float(csv_row["Height"]),
                "custom_width": to_float(csv_row["Width"]),
            },
            dialog_values=get_select_item_dialog_values(csv_row),
            available_items=[csv_row["Item Name"]],
        )
        expected_item_code = csv_row["Item Name"]
        generated_item_code = get_generated_select_item_code(result)
        expected_cut_height = to_float(csv_row["Cut From Height"])
        expected_cut_width = to_float(csv_row["Cut From Width"])
        actual_cut_height = to_float(result["row"].get("custom_cut_from_height"))
        actual_cut_width = to_float(result["row"].get("custom_cut_from_width"))

        if case_sensitive_item_code:
            item_code_matches = generated_item_code == expected_item_code
        else:
            item_code_matches = str(generated_item_code).upper() == str(expected_item_code).upper()

        if (
            not item_code_matches
            or abs(actual_cut_height - expected_cut_height) > 0.01
            or abs(actual_cut_width - expected_cut_width) > 0.01
        ):
            mismatches.append(
                {
                    "csv_row": csv_row["_csv_row_number"],
                    "sales_order": csv_row["Sales Order"],
                    "expected_item_code": expected_item_code,
                    "generated_item_code": generated_item_code,
                    "row_item_code_after_lookup": result["row"].get("item_code"),
                    "height": csv_row["Height"],
                    "width": csv_row["Width"],
                    "expected_cut_height": expected_cut_height,
                    "actual_cut_height": actual_cut_height,
                    "expected_cut_width": expected_cut_width,
                    "actual_cut_width": actual_cut_width,
                    "dialog_values": result.get("dialog_values"),
                    "messages": result.get("messages"),
                }
            )

    return mismatches


def write_failed_rows_log(filename, rows, profile_name=None):
    """Write failed rows plus previous/best comparison logs, then return CSV path.

    Files written for `sales_order_kaddpa_select_item_failed_rows.json`:
    - `select_item/sales_order_kaddpa_select_item_failed_rows.json/csv`: latest run.
    - `select_item/previous/sales_order_kaddpa_select_item_failed_rows.json/csv`:
      run before the latest run.
    - `select_item/best/sales_order_kaddpa_select_item_failed_rows.json/csv`:
      lowest failure count seen so far.
    - `select_item/summary/sales_order_kaddpa_select_item_failed_rows.json/csv`:
      counts and deltas for latest vs previous/best.
    """
    log_dir = Path(os.environ.get("KGM_TEST_LOG_DIR", DEFAULT_TEST_LOG_DIR))
    log_dir = log_dir / get_failed_rows_log_subfolder(filename)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / filename
    csv_log_path = log_path.with_suffix(".csv")
    previous_dir = log_dir / "previous"
    best_dir = log_dir / "best"
    summary_dir = log_dir / "summary"
    for comparison_dir in (previous_dir, best_dir, summary_dir):
        comparison_dir.mkdir(parents=True, exist_ok=True)

    previous_log_path = previous_dir / filename
    previous_csv_log_path = previous_log_path.with_suffix(".csv")
    best_log_path = best_dir / filename
    best_csv_log_path = best_log_path.with_suffix(".csv")
    summary_log_path = summary_dir / filename
    summary_csv_log_path = summary_log_path.with_suffix(".csv")

    previous_count = _read_failed_row_count(log_path)
    if log_path.exists():
        shutil.copyfile(log_path, previous_log_path)
    if csv_log_path.exists():
        shutil.copyfile(csv_log_path, previous_csv_log_path)

    payload = {
        "source_csv": str(SALES_ORDER_ITEM_CSV),
        "profile": profile_name,
        "failed_row_count": len(rows),
        "failed_rows": rows,
    }
    _write_failed_rows_json(log_path, payload)
    _write_failed_rows_csv(csv_log_path, rows)

    best_count = _read_failed_row_count(best_log_path)
    if best_count is None or len(rows) <= best_count:
        _write_failed_rows_json(best_log_path, payload)
        _write_failed_rows_csv(best_csv_log_path, rows)
        best_count = len(rows)

    summary = {
        "source_csv": str(SALES_ORDER_ITEM_CSV),
        "profile": profile_name,
        "latest_failed_count": len(rows),
        "previous_failed_count": previous_count,
        "best_failed_count": best_count,
        "change_from_previous": (
            None if previous_count is None else len(rows) - previous_count
        ),
        "change_from_best": None if best_count is None else len(rows) - best_count,
        "latest_csv": str(csv_log_path),
        "previous_csv": str(previous_csv_log_path) if previous_csv_log_path.exists() else "",
        "best_csv": str(best_csv_log_path) if best_csv_log_path.exists() else "",
    }
    _write_failed_rows_json(summary_log_path, summary)
    _write_summary_csv(summary_csv_log_path, summary)

    return csv_log_path


def _write_failed_rows_json(path, payload):
    """Write one JSON log payload with stable formatting."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_failed_rows_csv(path, rows):
    """Write failed rows as CSV, including a readable zero-failure row."""
    fieldnames = sorted({fieldname for row in rows for fieldname in row}) or ["status"]
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            for row in rows:
                writer.writerow(
                    {
                        fieldname: _format_failed_log_cell(row.get(fieldname, ""))
                        for fieldname in fieldnames
                    }
                )
        else:
            writer.writerow({"status": "no failures"})


def _write_summary_csv(path, summary):
    """Write one-row CSV summary for latest/previous/best failure counts."""
    fieldnames = sorted(summary)
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(summary)


def _read_failed_row_count(path):
    """Read `failed_row_count` from a JSON log, or None when unavailable."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload.get("failed_row_count")


def get_failed_rows_log_subfolder(filename):
    """Return the log subfolder for one generated failure-log filename."""
    if "select_item" in filename:
        return "select_item"
    if "sqft" in filename:
        return "sqft"
    if "mould" in filename:
        return "mould"
    return "other"


def _format_failed_log_cell(value):
    """Convert nested failure-log values into readable CSV cell text."""
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return value
