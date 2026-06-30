import json
import os
import subprocess

import frappe
from frappe.utils import flt, today


SQFT_CLIENT_SCRIPT = "Sales-Order Kota Kaddpaa Granite Neno Calculation"
MOULD_CLIENT_SCRIPT = "Sales-Order Kota Granite Moulding Calculation"
CHILD_DOCTYPE = "Sales Order Item"
DEFAULT_PRICE_LIST = "Standard Selling"


def _as_dict(value):
    if not value:
        return {}
    if isinstance(value, str):
        return frappe.parse_json(value)
    return frappe._dict(value)


def _as_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return frappe.parse_json(value)
    return value


def _positive_float(value, default=0):
    value = flt(value)
    return value if value > 0 else default


def _to_check(value):
    return 1 if str(value or "").lower() in ("1", "true", "yes", "on") or value is True else 0


def _get_client_script(script_name):
    script_doc = frappe.db.get_value(
        "Client Script",
        script_name,
        ["script", "enabled"],
        as_dict=True,
    )
    if not script_doc or not script_doc.script:
        frappe.throw(f"Client Script not found: {script_name}")
    if not script_doc.enabled:
        frappe.throw(f"Client Script is disabled: {script_name}")
    return script_doc.script


def _run_sales_order_item_script(script_name, event_name, row, doc_items=None):
    script = _get_client_script(script_name)
    runner = r"""
const vm = require("vm");
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
const cdt = "Sales Order Item";
const cdn = payload.row.name || "FAST-ROW";
const row = Object.assign({ name: cdn }, payload.row);
const handlers = {};
const calls = [];
const messages = [];

function emptyJquery() {
  return {
    length: 0,
    off() { return this; },
    on() { return this; },
    one() { return this; },
    find() { return this; },
    closest() { return this; },
    first() { return this; },
    attr() { return undefined; },
    focus() {}
  };
}

const docItems = payload.doc_items && payload.doc_items.length ? payload.doc_items : [row];
for (const item of docItems) {
  if (!item.name) item.name = item === row ? cdn : `FAST-ROW-${docItems.indexOf(item) + 1}`;
}
if (!docItems.some(item => item.name === cdn)) docItems.push(row);

const context = {
  console: { log() {}, warn() {}, error() {} },
  document: { addEventListener() {}, removeEventListener() {} },
  setTimeout(fn) { fn(); return 0; },
  clearTimeout() {},
  __: value => value,
  $: emptyJquery,
  locals: { [cdt]: {} },
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

context.frappe = {
  ui: {
    form: {
      on(doctype, eventMap) {
        handlers[doctype] = Object.assign(handlers[doctype] || {}, eventMap || {});
      },
    },
    Dialog: class FakeDialog {
      constructor(opts) {
        this.opts = opts;
        this.values = {};
        this.$wrapper = emptyJquery();
        for (const field of opts.fields || []) {
          if (field.fieldname && Object.prototype.hasOwnProperty.call(field, "default")) {
            this.values[field.fieldname] = field.default;
          }
        }
      }
      show() {}
      hide() {}
      get_value(fieldname) { return this.values[fieldname]; }
      set_value(fieldname, value) { this.values[fieldname] = value; }
      get_field(fieldname) { return { df: { fieldname }, refresh() {} }; }
      get_primary_btn() { return { trigger() {} }; }
    },
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
  msgprint(message) { messages.push(String(message)); },
};

vm.createContext(context);
vm.runInContext(payload.script, context, { timeout: 5000 });

const handler = handlers[cdt] && handlers[cdt][payload.event_name];
if (typeof handler !== "function") {
  throw new Error(`Handler not registered for ${cdt}.${payload.event_name}`);
}

handler(frm, cdt, cdn);
console.log(JSON.stringify({ row, calls, messages }));
"""
    payload = {
        "script": script,
        "event_name": event_name,
        "row": row,
        "doc_items": doc_items or [],
    }
    try:
        result = subprocess.run(
            [os.environ.get("NODE_BINARY", "node"), "-e", runner],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        frappe.throw(exc.stderr or exc.stdout or f"Failed to run {script_name}")
    except Exception as exc:
        frappe.throw(f"Failed to run {script_name}: {exc}")

    try:
        return frappe.parse_json(result.stdout)
    except Exception:
        frappe.throw(f"{script_name} did not return valid JSON: {result.stdout}")


def _sync_cut_fields(row):
    cut_height = row.get("cut_from_height") or row.get("custom_cut_from_height")
    cut_width = row.get("cut_from_width") or row.get("custom_cut_from_width")
    row["custom_cut_from_height"] = flt(cut_height)
    row["custom_cut_from_width"] = flt(cut_width)
    return row


def _get_standard_rate(item_code, price_list=DEFAULT_PRICE_LIST):
    prices = frappe.get_all(
        "Item Price",
        filters={
            "item_code": item_code,
            "price_list": price_list,
            "selling": 1,
        },
        fields=["price_list_rate"],
        order_by="valid_from desc, modified desc",
        limit_page_length=1,
    )
    return flt(prices[0].price_list_rate) if prices else 0


def _validate_item(item_code):
    if not item_code:
        frappe.throw("Item Code is required.")
    if not frappe.db.exists("Item", item_code):
        frappe.throw(f"Item not found: {item_code}")


def _item_summary(item_code, price_list=DEFAULT_PRICE_LIST):
    _validate_item(item_code)
    item = frappe.db.get_value(
        "Item",
        item_code,
        ["item_code", "item_name", "stock_uom"],
        as_dict=True,
    )
    return {
        "item_code": item.item_code,
        "item_name": item.item_name,
        "stock_uom": item.stock_uom,
        "rate": _get_standard_rate(item_code, price_list),
    }


def _get_company_default_cost_center(company):
    if not company:
        return None
    company_meta = frappe.get_meta("Company")
    if company_meta.has_field("default_cost_center"):
        return frappe.db.get_value("Company", company, "default_cost_center")
    if company_meta.has_field("cost_center"):
        return frappe.db.get_value("Company", company, "cost_center")
    return None


def _base_row(raw, name):
    raw = frappe._dict(raw or {})
    quantity = _positive_float(raw.get("custom_quantity") or raw.get("quantity"), 1)
    return {
        "name": name,
        "item_code": raw.get("item_code"),
        "custom_height": _positive_float(raw.get("custom_height") or raw.get("height")),
        "custom_width": _positive_float(raw.get("custom_width") or raw.get("width")),
        "custom_quantity": quantity,
        "qty": _positive_float(raw.get("qty"), quantity),
        "custom_cut_from_height": flt(raw.get("custom_cut_from_height")),
        "custom_cut_from_width": flt(raw.get("custom_cut_from_width")),
        "custom_top": _to_check(raw.get("custom_top")),
        "custom_left": _to_check(raw.get("custom_left")),
        "custom_right": _to_check(raw.get("custom_right")),
        "custom_bottom": _to_check(raw.get("custom_bottom")),
        "rate": flt(raw.get("rate")),
    }


def _with_display_fields(row, price_list=DEFAULT_PRICE_LIST):
    summary = _item_summary(row["item_code"], price_list)
    rate = flt(row.get("rate"))
    if not rate:
        rate = summary["rate"]
    qty = flt(row.get("qty"))
    row.update(
        {
            "item_name": summary["item_name"],
            "uom": summary["stock_uom"],
            "rate": rate,
            "amount": round(qty * rate, 2),
        }
    )
    return row


def _is_job_work_item(item_code):
    return "job work" in (item_code or "").lower()


def _is_piece_qty_item(item_code):
    return "paati" in (item_code or "").lower()


def _calculate_stone_row(raw, index=1, price_list=DEFAULT_PRICE_LIST):
    raw = frappe._dict(raw or {})
    row = _base_row(raw, f"STONE-{index}")
    _validate_item(row["item_code"])
    manual_qty = _to_check(raw.get("manual_qty"))

    if _is_piece_qty_item(row["item_code"]):
        row["qty"] = flt(row.get("custom_quantity"))
        row["custom_cut_from_height"] = 0
        row["custom_cut_from_width"] = 0
        return _with_display_fields(row, price_list)

    if _is_job_work_item(row["item_code"]):
        if not any(row.get(field) for field in ("custom_top", "custom_left", "custom_right", "custom_bottom")):
            frappe.throw(f"Select at least one side for {row['item_code']}.")
        row["qty"] = 0
        result = _run_sales_order_item_script(MOULD_CLIENT_SCRIPT, "custom_quantity", row)
        calculated = _sync_cut_fields(dict(result.get("row") or row))
        if manual_qty:
            calculated["qty"] = flt(raw.get("qty"))
        return _with_display_fields(calculated, price_list)

    result = _run_sales_order_item_script(SQFT_CLIENT_SCRIPT, "item_code", row)
    calculated = _sync_cut_fields(dict(result.get("row") or row))
    if manual_qty:
        calculated["qty"] = flt(raw.get("qty"))
    return _with_display_fields(calculated, price_list)


def _calculate_operation_row(raw, stone_row, index=1, price_list=DEFAULT_PRICE_LIST):
    raw = frappe._dict(raw or {})
    row = _base_row(raw, f"WORK-{index}")
    row["custom_height"] = _positive_float(row["custom_height"], flt(stone_row.get("custom_height")))
    row["custom_width"] = _positive_float(row["custom_width"], flt(stone_row.get("custom_width")))
    if not (raw.get("custom_quantity") or raw.get("quantity")):
        row["custom_quantity"] = flt(stone_row.get("custom_quantity"))
    row["custom_quantity"] = _positive_float(row["custom_quantity"], flt(stone_row.get("custom_quantity")))
    row["qty"] = 0
    _validate_item(row["item_code"])

    if not any(row.get(field) for field in ("custom_top", "custom_left", "custom_right", "custom_bottom")):
        frappe.throw(f"Select at least one side for {row['item_code']}.")

    result = _run_sales_order_item_script(MOULD_CLIENT_SCRIPT, "custom_quantity", row)
    calculated = _sync_cut_fields(dict(result.get("row") or row))
    return _with_display_fields(calculated, price_list)


def _build_entry_rows(entry, price_list=DEFAULT_PRICE_LIST):
    entry = _as_dict(entry)
    stone = _calculate_stone_row(entry.get("stone"), 1, price_list)
    rows = [stone]

    operations = entry.get("operations")
    if operations is None and entry.get("operation"):
        operations = [entry.get("operation")]

    for index, operation in enumerate(operations or [], start=1):
        operation = _as_dict(operation)
        if operation.get("item_code"):
            rows.append(_calculate_operation_row(operation, stone, index, price_list))

    return rows


def _get_saved_entry_rows(entry, price_list=DEFAULT_PRICE_LIST):
    entry = _as_dict(entry)
    cached_rows = _as_list(entry.get("rows"))
    if cached_rows:
        return [frappe._dict(row) for row in cached_rows]

    return _build_entry_rows(entry.get("input") or entry, price_list)


def _missing_entry_items(entry):
    entry = _as_dict(entry)
    missing = []
    stone = _as_dict(entry.get("stone"))
    if stone.get("item_code") and not frappe.db.exists("Item", stone.get("item_code")):
        missing.append(stone.get("item_code"))

    operations = entry.get("operations")
    if operations is None and entry.get("operation"):
        operations = [entry.get("operation")]

    for operation in operations or []:
        operation = _as_dict(operation)
        if operation.get("item_code") and not frappe.db.exists("Item", operation.get("item_code")):
            missing.append(operation.get("item_code"))

    return missing


@frappe.whitelist()
def get_item_details(item_code, price_list=DEFAULT_PRICE_LIST):
    if not item_code:
        return {}
    if not frappe.db.exists("Item", item_code):
        return {"exists": False, "item_code": item_code}
    details = _item_summary(item_code, price_list)
    details["exists"] = True
    return details


@frappe.whitelist()
def get_work_items(price_list=DEFAULT_PRICE_LIST):
    items = frappe.get_all(
        "Item",
        filters={"disabled": 0},
        or_filters=[
            ["item_code", "like", "%mould%"],
            ["item_name", "like", "%mould%"],
        ],
        fields=["item_code", "item_name", "stock_uom"],
        order_by="item_code asc",
        limit_page_length=500,
    )
    return [
        {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "stock_uom": item.stock_uom,
            "rate": _get_standard_rate(item.item_code, price_list),
        }
        for item in items
    ]


@frappe.whitelist()
def preview_entry(entry, price_list=DEFAULT_PRICE_LIST, quiet_missing=0):
    if _to_check(quiet_missing):
        missing_items = _missing_entry_items(entry)
        if missing_items:
            return {"rows": [], "missing_items": missing_items}

    rows = _build_entry_rows(entry, price_list)
    return {"rows": rows}


@frappe.whitelist()
def get_defaults():
    latest = frappe.get_all(
        "Sales Order",
        fields=["transaction_date", "delivery_date"],
        order_by="creation desc",
        limit_page_length=1,
    )
    default_date = latest[0].transaction_date if latest else today()
    return {
        "transaction_date": default_date,
        "delivery_date": latest[0].delivery_date if latest else default_date,
        "company": frappe.defaults.get_user_default("Company")
        or frappe.db.get_single_value("Global Defaults", "default_company"),
        "price_list": DEFAULT_PRICE_LIST,
    }


def _set_if_field(target, meta, fieldname, value):
    if meta.has_field(fieldname):
        target[fieldname] = value


def _sales_order_item_payload(row, delivery_date):
    meta = frappe.get_meta(CHILD_DOCTYPE)
    qty = flt(row.get("qty"))
    rate = flt(row.get("rate"))
    amount = flt(row.get("amount")) or round(qty * rate, 2)
    payload = {
        "item_code": row["item_code"],
        "delivery_date": delivery_date,
        "qty": qty,
        "rate": rate,
        "amount": amount,
    }
    display_fields = {
        "item_name": row.get("item_name"),
        "description": row.get("item_name") or row.get("item_code"),
        "uom": row.get("uom"),
        "stock_uom": row.get("uom"),
        "conversion_factor": 1,
        "stock_qty": qty,
        "price_list_rate": rate,
        "base_price_list_rate": rate,
        "base_rate": rate,
        "base_amount": amount,
        "net_rate": rate,
        "net_amount": amount,
        "base_net_rate": rate,
        "base_net_amount": amount,
    }
    for fieldname, value in display_fields.items():
        _set_if_field(payload, meta, fieldname, value)

    for fieldname in (
        "custom_height",
        "custom_width",
        "custom_quantity",
        "custom_cut_from_height",
        "custom_cut_from_width",
        "custom_top",
        "custom_left",
        "custom_right",
        "custom_bottom",
    ):
        _set_if_field(payload, meta, fieldname, row.get(fieldname))

    return payload


def _sales_tax_payload(raw, company):
    raw = _as_dict(raw)
    account_head = raw.get("account_head")
    if not account_head:
        frappe.throw("Tax account is required.")
    if not frappe.db.exists("Account", account_head):
        frappe.throw(f"Tax account not found: {account_head}")

    charge_type = raw.get("charge_type") or "On Net Total"
    payload = {
        "charge_type": charge_type,
        "account_head": account_head,
        "description": raw.get("description") or account_head,
    }

    if charge_type == "Actual":
        payload["tax_amount"] = flt(raw.get("tax_amount"))
    else:
        payload["rate"] = flt(raw.get("rate"))

    cost_center = raw.get("cost_center") or _get_company_default_cost_center(company)
    if cost_center:
        payload["cost_center"] = cost_center

    return payload


@frappe.whitelist()
def save_sales_order(header, entries, taxes=None, price_list=DEFAULT_PRICE_LIST):
    header = _as_dict(header)
    entries = _as_list(entries)
    taxes = _as_list(taxes)
    if not entries:
        frappe.throw("Add at least one entry before saving.")

    customer = header.get("customer")
    if not customer:
        frappe.throw("Customer is required.")
    if not frappe.db.exists("Customer", customer):
        frappe.throw(f"Customer not found: {customer}")

    transaction_date = header.get("transaction_date") or today()
    delivery_date = header.get("delivery_date") or transaction_date
    company = (
        header.get("company")
        or frappe.defaults.get_user_default("Company")
        or frappe.db.get_single_value("Global Defaults", "default_company")
    )
    company_currency = frappe.db.get_value("Company", company, "default_currency")
    price_list_currency = frappe.db.get_value("Price List", price_list, "currency") or company_currency

    sales_order = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "customer": customer,
            "company": company,
            "currency": price_list_currency,
            "conversion_rate": 1,
            "transaction_date": transaction_date,
            "delivery_date": delivery_date,
            "selling_price_list": price_list,
            "price_list_currency": price_list_currency,
            "plc_conversion_rate": 1,
            "ignore_pricing_rule": 1,
            "items": [],
        }
    )

    if header.get("custom_cash_customer_name"):
        sales_order.custom_cash_customer_name = header.get("custom_cash_customer_name")
    if header.get("custom_phone_number"):
        sales_order.custom_phone_number = header.get("custom_phone_number")
    if header.get("custom_vehicle_number_"):
        sales_order.custom_vehicle_number_ = header.get("custom_vehicle_number_")

    for entry in entries:
        for row in _get_saved_entry_rows(entry, price_list):
            sales_order.append("items", _sales_order_item_payload(row, delivery_date))

    for tax in taxes:
        sales_order.append("taxes", _sales_tax_payload(tax, sales_order.company))

    sales_order.insert()
    frappe.db.commit()
    return {
        "name": sales_order.name,
        "route": f"/app/sales-order/{sales_order.name}",
        "total_qty": sales_order.total_qty,
        "grand_total": sales_order.grand_total,
    }
