# WhatsApp Suite Documentation

This module connects ERPNext/Frappe with WhatsApp through WAHA, stores WhatsApp
groups and messages, downloads media, and supports an AI order-extraction flow
that can turn WhatsApp image orders into draft Sales Orders.

## Main Flow

1. Create a `WhatsApp Connection` with WAHA server details.
2. Test the WAHA connection or generate a QR code from the connection form.
3. Sync WAHA chats into `WhatsApp Group`.
4. Enable scraping for the groups that should be monitored.
5. Fetch messages for a group from the `WhatsApp Chat UI` page or the group form.
6. Image messages are stored as `WhatsApp Message` records with private file
   attachments.
7. The scheduled AI worker checks `WhatsApp AI Settings` and queues unprocessed
   image messages from allowed groups.
8. The vision parser sends the image to OpenRouter and creates one
   `WhatsApp Order Staging` record per extracted order.
9. A staging record can be converted into a draft ERPNext `Sales Order`.

## DocTypes

### WhatsApp Connection

Path:
`whatsapp_suite/doctype/whatsapp_connection`

Purpose:
Stores the WAHA server connection used to access a WhatsApp session.

Important fields:

- `waha_server_ip`: WAHA server host/IP. The Python code builds
  `http://{waha_server_ip}`.
- `session_name`: WAHA session name.
- `api_key`: API key used by WAHA.
- `qr_code_display`: HTML area used by the client script to display a QR code.

Backend functions:

- `test_waha_connection(ip, session_name, api_key, docname=None)`
  - Whitelisted.
  - Connects to WAHA and checks whether the session exists.
  - If Frappe sends a masked password value and `docname` is provided, it reads
    the real password using `get_password("api_key")`.
  - Returns a dictionary with `status` and `message`.
  - Handles WAHA authentication errors, missing sessions, and network/general
    errors.

- `generate_qr_code(ip, session_name, api_key, docname=None)`
  - Whitelisted.
  - Calls WAHA to get QR code data for the session.
  - Uses the same masked-password handling as `test_waha_connection`.
  - Returns `{"status": "success", "qr_data": ...}` when WAHA provides QR data.

- `sync_waha_chats(connection_name=None)`
  - Whitelisted.
  - Fetches chat records from WAHA and upserts them into `WhatsApp Group`.
  - If `connection_name` is not supplied, it uses the first available
    `WhatsApp Connection`.
  - New groups are inserted with `scraping_enabled = 0` so they must be enabled
    deliberately.
  - Existing groups are updated with the latest group name and connection.

- `handle_incoming_webhook()`
  - Whitelisted with `allow_guest=True`.
  - Receives WAHA webhook payloads.
  - Only stores events where `event == "message"`.
  - Creates a `WhatsApp Message` with `whatsapp_id`, `message`, `session`, and
    `direction = "Incoming"`.

Client behavior:
The exported Client Script fixture adds buttons for `Test Connection`,
`Generate QR Code`, and `Sync WAHA Groups`.

### WhatsApp Group

Path:
`whatsapp_suite/doctype/whatsapp_group`

Purpose:
Represents a WhatsApp chat/group that can be scraped for messages.

Important fields:

- `group_name`: Display name from WAHA.
- `whatsapp_id`: WAHA/WhatsApp chat ID. This is read-only in the DocType.
- `whatsapp_connection`: Link to the `WhatsApp Connection` used for scraping.
- `scraping_enabled`: Controls whether the chat appears in the main chat UI and
  whether it is considered active.
- `scrape_start_date`: Optional lower bound for message scraping.

Backend functions:

- `fetch_group_messages(group_docname)`
  - Whitelisted.
  - Loads the selected `WhatsApp Group` and its linked `WhatsApp Connection`.
  - Determines the scraping start point from the newest stored message timestamp
    and/or `scrape_start_date`.
  - Calls WAHA `client.chats.get_messages(...)` for the group.
  - Skips system/protocol/call-log message types.
  - Skips messages older than the calculated start timestamp.
  - Skips messages already stored by message ID.
  - Inserts each message as a `WhatsApp Message`.
  - For media messages, downloads the media from WAHA, stores it as a private
    Frappe File attached to the message, and maps the MIME type into
    `Image`, `Video`, `Audio`, or `Document`.
  - Returns a success dictionary with the number of inserted messages.

Client behavior:
The exported Client Script fixture adds a `Fetch New Messages` action on the
group form.

### WhatsApp Message

Path:
`whatsapp_suite/doctype/whatsapp_message`

Purpose:
Stores individual messages fetched from WAHA or received by webhook.

Important fields:

- `whatsapp_connection`: Link to the connection used to fetch the message.
- `whatsapp_group`: Link to the group/chat.
- `whatsapp_id`: Sender/chat ID from WAHA.
- `message_id`: Message identifier field defined in the DocType.
- `direction`: `Incoming` or `Outgoing`.
- `message`: Text body.
- `timestamp`: Message time.
- `session_name`: Session name field defined in the DocType.
- `media_url`: Original media URL field, if used.
- `has_media`: Whether the message has an attachment.
- `media_type`: `Image`, `Video`, `Audio`, or `Document`.
- `attachment`: Frappe File attachment URL.
- `raw_json`: Raw WAHA message payload for debugging.
- `is_ai_processed`: Prevents repeat AI processing.

Controller:
`WhatsAppMessage` currently uses the base Frappe `Document` behavior only.

### WhatsApp AI Settings

Path:
`whatsapp_suite/doctype/whatsapp_ai_settings`

Purpose:
Single settings document that controls the AI image-processing worker.

Important fields:

- `enable_ai_worker`: Master switch for scheduled AI processing.
- `openrouter_api_key`: Password field used by the vision parser.
- `allowed_groups`: Child table of allowed WhatsApp group IDs.
- `system_prompt`: Prompt sent to the AI model before the order image.

Controller:
`WhatsAppAISettings` currently uses the base Frappe `Document` behavior only.

### WhatsApp Allowed Group

Path:
`whatsapp_suite/doctype/whatsapp_allowed_group`

Purpose:
Child table used inside `WhatsApp AI Settings` to decide which groups are
eligible for AI order extraction.

Important fields:

- `group_id`: Group identifier. It is unique in the child table.

Controller:
`WhatsAppAllowedGroup` currently uses the base Frappe `Document` behavior only.

### WhatsApp Order Staging

Path:
`whatsapp_suite/doctype/whatsapp_order_staging`

Purpose:
Temporary review/conversion record created from AI-extracted image order data.
Each staging record represents one extracted order from a WhatsApp image.

Important fields:

- `whatsapp_message`: Source `WhatsApp Message`.
- `parent_image`: Original image attachment.
- `status`: `Pending`, `Converted`, or `Failed`.
- `extracted_data_json`: AI-extracted order JSON for one order.
- `created_sales_order`: Link to the Sales Order created from this staging row.

Controller:
`WhatsAppOrderStaging` currently uses the base Frappe `Document` behavior only.

## Pages

### WhatsApp Chat UI

Path:
`whatsapp_suite/page/whatsapp_chat_ui`

Purpose:
Main chat viewing page for enabled groups.

Python functions:

- `get_groups()`
  - Whitelisted.
  - Returns groups where `scraping_enabled = 1`.
  - Fields returned: `name`, `group_name`, `whatsapp_connection`.

- `get_chat_history(group_name)`
  - Whitelisted.
  - Returns the latest 100 messages for a group.
  - Fields returned: `message`, `direction`, `timestamp`, `has_media`,
    `media_type`, `attachment`.
  - Results are fetched newest-first and reversed so the UI shows oldest to
    newest.

Client behavior:
The page builds a WhatsApp-style split layout with a group sidebar and chat
area. Selecting a group loads message bubbles and media previews. The page also
has a `Fetch New Messages` button that calls `fetch_group_messages`.

### WhatsApp Dashboard

Path:
`whatsapp_suite/page/whatsapp_dashboard`

Purpose:
Older dashboard/chat page that reads all groups, not only scraping-enabled
groups.

Python functions:

- `get_groups()`
  - Whitelisted.
  - Returns all `WhatsApp Group` records with `name`, `group_name`, and
    `whatsapp_connection`.

- `get_chat_history(group_name)`
  - Whitelisted.
  - Same message-history behavior as `WhatsApp Chat UI`.

Implementation note:
The current `whatsapp_dashboard.js` appears to be an older draft. It has code
outside the `on_page_load` wrapper and calls method paths under
`kgmaccount.kgmaccount.page...`, while the Python file is located under
`kgmaccount.whatsapp_suite.page...`.

## Supporting Utility Modules

These files are outside the `whatsapp_suite` folder but are part of the
WhatsApp order-processing flow.

### `kgmaccount/utils/vision_scheduler.py`

- `fetch_and_process_unprocessed_whatsapp_messages()`
  - Registered in `hooks.py` under `scheduler_events["all"]`.
  - Reads `WhatsApp AI Settings`.
  - Stops immediately when `enable_ai_worker` is off.
  - Builds an allowed group list from `settings.allowed_groups`.
  - Finds `WhatsApp Message` rows where:
    - `media_type = "Image"`
    - `has_media = 1`
    - `is_ai_processed = 0`
    - `whatsapp_group` is in the allowed list
  - Marks each message as processed before enqueueing to reduce duplicate work.
  - Enqueues `kgmaccount.utils.vision_parser.process_order_image` on the long
    queue.

### `kgmaccount/utils/vision_parser.py`

- `process_order_image(whatsapp_message_id)`
  - Loads `WhatsApp AI Settings`.
  - Requires `openrouter_api_key` and `system_prompt`.
  - Loads the source `WhatsApp Message` and its attached image file.
  - Encodes the image as base64.
  - Sends the prompt and image to OpenRouter using model
    `google/gemma-4-31b-it`.
  - Parses the AI response as JSON, with fallbacks for fenced JSON and embedded
    object/array JSON.
  - Normalizes the response into a list of orders.
  - Creates one `WhatsApp Order Staging` record per order.
  - On failure, rolls back and resets `is_ai_processed` to `0` so the message
    can be retried.

Expected extracted order shape:

```json
{
  "customer_name": "Customer Name",
  "mobile_number": "9999999999",
  "vehicle_number": "AB12CD1234",
  "date": "31/05/26",
  "bounding_box": [0, 0, 1000, 1000],
  "items": [
    {
      "item_code": "ITEM-001",
      "quantity": 1,
      "height": 10,
      "width": 20
    }
  ]
}
```

### `kgmaccount/utils/order_builder.py`

- `convert_staging_to_sales_order(staging_id)`
  - Whitelisted.
  - Loads a `WhatsApp Order Staging` record.
  - Allows conversion only when `status == "Pending"`.
  - Parses `extracted_data_json`.
  - If a `bounding_box` exists, calls `crop_order_snippet`.
  - Parses `date` as `DD/MM/YY`; falls back to the server date if parsing
    fails.
  - Sets delivery date to three days after the transaction date.
  - Creates a draft `Sales Order` with customer, phone, vehicle number, AI
    flags, cropped image, bounding box, WhatsApp message reference, and item
    rows.
  - Calculates item `qty` by fetching and running the current
    `Sales-Order Kota Kaddpaa Granite Neno Calculation` Client Script from
    Frappe, so the Sales Order form and WhatsApp staging conversion use the
    same source of truth.
  - Inserts Sales Order items with `item_code`, `custom_quantity`, `rate = 0`,
    calculated `qty`, `uom = "Nos"`, `custom_height`, and `custom_width`.
  - Updates staging status to `Converted` and links `created_sales_order`.
  - Returns the created Sales Order name.

- `calculate_sales_order_item_from_client_script(item)`
  - Loads `Sales-Order Kota Kaddpaa Granite Neno Calculation` from the
    `Client Script` DocType.
  - Runs the script with a small mocked Frappe client context and invokes its
    `Sales Order Item.item_code` handler.
  - Returns the row values produced by the Client Script, including `qty` and
    cut-from dimensions.

- `crop_order_snippet(parent_image_url, box, staging_id)`
  - Loads the source Frappe File from `parent_image_url`.
  - Expects `box` in normalized 0-1000 format: `[ymin, xmin, ymax, xmax]`.
  - Converts the normalized coordinates to real image pixels.
  - Crops the image with Pillow.
  - Saves the snippet to the current site public files folder as
    `cropped_{staging_id}.jpg`.
  - Registers a public Frappe File if one does not already exist.
  - Returns the new `/files/...` URL.

### `kgmaccount/utils/whatsapp_logger.py`

- `get_logger(name=None)`
  - Configures a rotating log file at `logs/whatsapp_suitee.log`.
  - Adds a stdout stream handler.
  - Returns the configured logger, or a named logger when `name` is provided.

### `kgmaccount/api.py`

- `sync_all_active_groups()`
  - Finds all `WhatsApp Group` records where `scraping_enabled = 1`.
  - Calls `fetch_group_messages` for each group.

## External Services and Packages

- WAHA server, accessed through `waha_python.WAHAClient`.
- OpenRouter chat completions API for image-to-order extraction.
- `requests` for media downloads and OpenRouter calls.
- Pillow (`PIL.Image`) for order snippet cropping.
- Frappe background jobs through `frappe.enqueue`.
- Node.js for executing the current Sales Order Client Script during WhatsApp
  staging conversion.

## Current Implementation Notes

- `whatsapp_group.py` writes `new_msg.whatsapp_message_id`, but the
  `WhatsApp Message` DocType currently defines the field as `message_id`.
  This can affect duplicate detection and message ID storage.
- `handle_incoming_webhook()` writes `doc.session`, but the DocType field is
  `session_name`.
- `order_builder.py` writes `whatsapp_message_reference` on `Sales Order`, while
  the exported custom field appears to be `custom_source_whatsapp_message`.
- `api.py` imports `fetch_group_messages` from
  `whatsapp_suite.doctype...` without the `kgmaccount.` package prefix.
- `whatsapp_dashboard.js` has likely stale paths and wrapper-scope issues.
- `whatsapp_logger.py` writes to `whatsapp_suitee.log`; the double `e` may be
  intentional, but it is worth confirming.
- `WhatsApp Connection.api_key` is defined as `Data`, while the code treats it
  like a password in some places. Consider changing it to `Password` if masked
  password handling is desired consistently.
