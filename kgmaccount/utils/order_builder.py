import frappe
import json
import os
import logging
import subprocess
from datetime import datetime
from kgmaccount.utils import whatsapp_logger  # configure whatsapp log file
from PIL import Image

logger = logging.getLogger(__name__)

# This Client Script is the source of truth for Sales Order item qty calculation.
# The WhatsApp flow reads it at runtime so Desk-side changes keep applying here.
SALES_ORDER_QTY_CLIENT_SCRIPT = "Sales-Order Kota Kaddpaa Granite Neno Calculation"


def get_sales_order_qty_client_script():
    # Fetch the currently installed Client Script from Frappe, not the fixture file.
    # This keeps the WhatsApp conversion aligned with changes made in Desk.
    script_doc = frappe.db.get_value(
        "Client Script",
        SALES_ORDER_QTY_CLIENT_SCRIPT,
        ["script", "enabled"],
        as_dict=True,
    )

    if not script_doc or not script_doc.script:
        frappe.throw(f"Client Script not found: {SALES_ORDER_QTY_CLIENT_SCRIPT}")

    if not script_doc.enabled:
        frappe.throw(f"Client Script is disabled: {SALES_ORDER_QTY_CLIENT_SCRIPT}")

    return script_doc.script


def calculate_sales_order_item_from_client_script(item):
    script = get_sales_order_qty_client_script()
    quantity = item.get("quantity") or item.get("custom_quantity") or 1

    # Build the same row shape the Sales Order Item Client Script expects in Desk.
    # The LLM uses height/width/quantity; the Client Script uses custom_* fields.
    row = {
        "item_code": item.get("item_code"),
        "custom_height": item.get("height") or item.get("custom_height"),
        "custom_width": item.get("width") or item.get("custom_width"),
        "custom_quantity": quantity,
        "qty": quantity,
        "custom_cut_from_height": item.get("custom_cut_from_height"),
        "custom_cut_from_width": item.get("custom_cut_from_width"),
    }

    # Client Scripts are JavaScript and normally run only in the browser.
    # This Node runner creates a tiny fake Frappe client environment, registers
    # the script's Sales Order Item handlers, triggers item_code, and returns
    # the mutated row containing qty/cut-from values.
    runner = """
const vm = require("vm");
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
const cdt = "Sales Order Item";
const cdn = "WHATSAPP-STAGING-ITEM";
const row = payload.row;
const handlers = {};
const context = {
  console: { log() {}, error() {}, warn() {} },
  locals: { "Sales Order Item": { [cdn]: row } },
  frappe: {
    ui: { form: { on: function(doctype, eventMap) {
      if (doctype === cdt) Object.assign(handlers, eventMap || {});
    }}},
    model: { set_value: function(targetCdt, targetCdn, fieldOrValues, value) {
      if (targetCdt !== cdt || targetCdn !== cdn) return Promise.resolve();
      if (typeof fieldOrValues === "string") {
        row[fieldOrValues] = value;
      } else if (fieldOrValues && typeof fieldOrValues === "object") {
        Object.assign(row, fieldOrValues);
      }
      return Promise.resolve();
    }}
  }
};
vm.createContext(context);
vm.runInContext(payload.script, context, { timeout: 5000 });
if (typeof handlers.item_code !== "function") {
  throw new Error("Client Script did not register Sales Order Item.item_code handler");
}
handlers.item_code({ doc: { items: [row] }, refresh_field() {} }, cdt, cdn);
console.log(JSON.stringify(row));
"""

    try:
        result = subprocess.run(
            [os.environ.get("NODE_BINARY", "node"), "-e", runner],
            input=json.dumps({"script": script, "row": row}),
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        frappe.throw(
            "Failed to run Sales Order Client Script calculation: "
            f"{e.stderr or e.stdout or str(e)}"
        )
    except Exception as e:
        frappe.throw(f"Failed to run Sales Order Client Script calculation: {str(e)}")

    try:
        calculated_row = json.loads(result.stdout)
    except Exception:
        frappe.throw(
            "Sales Order Client Script calculation did not return valid JSON: "
            f"{result.stdout}"
        )

    return {
        "qty": calculated_row.get("qty") or quantity,
        "custom_cut_from_height": calculated_row.get("custom_cut_from_height")
            or calculated_row.get("cut_from_height"),
        "custom_cut_from_width": calculated_row.get("custom_cut_from_width")
            or calculated_row.get("cut_from_width"),
    }


@frappe.whitelist()
def convert_staging_to_sales_order(staging_id):
    """
    Triggered by the user clicking 'Create Sales Order' on a Pending Staging doc.
    Crops the specific item block from the parent image and injects a clean Draft Sales Order.
    """
    try:
        logger.info(f"convert_staging_to_sales_order started for staging {staging_id}")
        print(f"[kgmaccount] convert_staging_to_sales_order started for staging {staging_id}")
        # 1. Fetch Staging Document
        staging_doc = frappe.get_doc("WhatsApp Order Staging", staging_id)
        if staging_doc.status != "Pending":
            frappe.throw(f"This record has already been processed. Current status is: {staging_doc.status}")

        logger.debug(f"Staging status: {staging_doc.status}")
        print(f"[kgmaccount] Staging status: {staging_doc.status}")

        # NEW LOGIC: The JSON is now already isolated to just one order
        order_payload = json.loads(staging_doc.extracted_data_json)
        
        if not order_payload:
            frappe.throw("No valid order payload found inside the extracted JSON.")

        # 2. Handle On-Demand Image Cropping via Pillow
        cropped_file_url = None
        bounding_box = order_payload.get("bounding_box")

        if bounding_box and staging_doc.parent_image:
            logger.info(f"Cropping order snippet for staging {staging_id}")
            print(f"[kgmaccount] Cropping order snippet for staging {staging_id}")
            cropped_file_url = crop_order_snippet(staging_doc.parent_image, bounding_box, staging_id)

        logger.debug(f"Cropped file url: {cropped_file_url}")
        print(f"[kgmaccount] Cropped file url: {cropped_file_url}")

        # Parse transaction date from JSON if present, else use server date
        transaction_date = frappe.utils.today()
        raw_date = order_payload.get("date")
        if raw_date:
            try:
                
                # Expecting format: DD/MM/YY (day, month, 2-digit year)
                parsed = datetime.strptime(raw_date, "%d/%m/%y").date()
                transaction_date = parsed.strftime("%Y-%m-%d")
            except Exception:
                logger.warning(f"Failed to parse date '{raw_date}' as DD/MM/YY; using server date")
                print(f"[kgmaccount] WARNING: Failed to parse date '{raw_date}', using server date")

        delivery_date = transaction_date

        # 3. Build the Core ERPNext Draft Sales Order
        sales_order = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": order_payload.get("customer_name") or "Walk-in Customer", # Fallback default
            "custom_phone_number": order_payload.get("mobile_number"),
            "custom_vehicle_number_": order_payload.get("vehicle_number"),
            "custom_ai_bounding_box": json.dumps(order_payload.get("bounding_box") or []),
            "transaction_date": transaction_date,
            "delivery_date": delivery_date,
            "whatsapp_message_reference": staging_doc.whatsapp_message,
            "custom_is_ai_generated": 1,
            "custom_ai_cropped_image": cropped_file_url,
            "items": []
        })

        # Append item rows parsed from the LLM structure
        for item in order_payload.get("items", []):
            # Run the current Sales Order Client Script calculation before insert.
            # This avoids duplicating the Kota/Kaddpa/Granite/Neno formula in Python.
            calculated_values = calculate_sales_order_item_from_client_script(item)
            sales_order.append("items", {
                "item_code": item.get("item_code"),
                "custom_quantity": item.get("quantity") or 1,
                "rate": 0, # Manual team will fill standard pricing during verification
                "qty": calculated_values["qty"],
                "uom": "Nos",
                "custom_height": item.get("height"),
                "custom_width": item.get("width"),
                "custom_cut_from_height": calculated_values["custom_cut_from_height"],
                "custom_cut_from_width": calculated_values["custom_cut_from_width"],
            })

        # Insert as standard system Draft
        sales_order.insert(ignore_permissions=True)
        logger.info(f"Inserted Sales Order {sales_order.name} for staging {staging_id}")
        print(f"[kgmaccount] Inserted Sales Order {sales_order.name} for staging {staging_id}")

        # 4. Update Staging Record Status & Link Reference
        staging_doc.status = "Converted"
        staging_doc.created_sales_order = sales_order.name
        staging_doc.save(ignore_permissions=True)
        logger.info(f"Updated staging {staging_id} -> Converted, linked Sales Order {sales_order.name}")
        print(f"[kgmaccount] Updated staging {staging_id} -> Converted, linked Sales Order {sales_order.name}")
        
        frappe.db.commit()
        return {"sales_order": sales_order.name}

    except Exception as e:
        frappe.db.rollback()
        logger.exception(f"Staging conversion failed for {staging_id}: {e}")
        print(f"[kgmaccount] ERROR Staging conversion failed for {staging_id}: {e}")
        frappe.log_error(title=f"Staging Conversion Failed: {staging_id}", message=frappe.get_traceback())
        frappe.throw(f"Conversion halted due to processing error: {str(e)}")


def crop_order_snippet(parent_image_url, box, staging_id):
    """
    Translates 0-1000 normalized coordinates into actual pixel dimensions
    and slices out the image snippet using Pillow.
    """
    # Fetch physical path of parent image
    file_doc = frappe.get_doc("File", {"file_url": parent_image_url})
    parent_path = file_doc.get_full_path()
    logger.debug(f"crop_order_snippet parent path: {parent_path}")
    print(f"[kgmaccount] crop_order_snippet parent path: {parent_path}")

    if not os.path.exists(parent_path):
        logger.warning(f"Parent image not found for staging {staging_id}: {parent_path}")
        print(f"[kgmaccount] Parent image not found for staging {staging_id}: {parent_path}")
        return None

    # Load original image
    img = Image.open(parent_path)
    img_width, img_height = img.size

    # Convert 0-1000 normalized coordinates back to absolute pixels
    # box structure: [ymin, xmin, ymax, xmax]
    ymin, xmin, ymax, xmax = box
    
    left = (xmin / 1000.0) * img_width
    top = (ymin / 1000.0) * img_height
    right = (xmax / 1000.0) * img_width
    bottom = (ymax / 1000.0) * img_height

    # Crop out the order block snippet
    cropped_img = img.crop((left, top, right, bottom))

    # Save snippet back into Frappe's Public File system
    filename = f"cropped_{staging_id}.jpg"
    public_path = frappe.get_site_path("public", "files", filename)
    
    cropped_img.save(public_path, "JPEG", quality=95)

    # Register the new snippet into Frappe's File Master
    file_url = f"/files/{filename}"
    if not frappe.db.exists("File", {"file_url": file_url}):
        file_meta = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "file_url": file_url,
            "is_private": 0
        })
        file_meta.insert(ignore_permissions=True)
    logger.info(f"Saved cropped snippet for staging {staging_id} -> {file_url}")
    print(f"[kgmaccount] Saved cropped snippet for staging {staging_id} -> {file_url}")

    return file_url
