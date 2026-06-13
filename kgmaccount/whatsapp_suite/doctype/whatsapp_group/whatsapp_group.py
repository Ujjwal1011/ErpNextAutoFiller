import json
import time
import requests
import frappe
from frappe.utils import getdate, nowdate
from frappe.model.document import Document
from frappe.utils.data import get_datetime
from frappe.utils.file_manager import save_file
from waha_python import WAHAClient
from kgmaccount.whatsapp_suite.permissions import assert_can_access_whatsapp_group

class WhatsAppGroup(Document):
    pass


def _waha_offline_message(conn_doc):
    server = conn_doc.waha_server_ip or "the configured WAHA server"
    return (
        f"Could not reach WhatsApp server at {server}. "
        "Please start the WAHA server and try again."
    )


@frappe.whitelist()
def fetch_group_messages(group_docname):
    assert_can_access_whatsapp_group(group_docname)

    try:
        group = frappe.get_doc("WhatsApp Group", group_docname)
        if not group.whatsapp_connection:
            return {
                "status": "error",
                "message": "This group is not linked to a WhatsApp Connection.",
            }

        conn_doc = frappe.get_doc("WhatsApp Connection", group.whatsapp_connection)

        # Determine Start Timestamp
        last_message_time = frappe.db.get_value(
            "WhatsApp Message",
            {"whatsapp_group": group.name, "whatsapp_connection": conn_doc.name},
            "timestamp",
            order_by="timestamp desc"
        )

        scrape_start_date = group.get("scrape_start_date")  # Ensure this matches your exact fieldname

        # Store valid timestamps here to find the max later
        available_timestamps = []

        if last_message_time:
            # +1 second to avoid fetching the exact same last message again
            db_ts = int(time.mktime(get_datetime(last_message_time).timetuple())) + 1
            available_timestamps.append(db_ts)
            
        if scrape_start_date:
            scrape_ts = int(time.mktime(get_datetime(scrape_start_date).timetuple()))
            available_timestamps.append(scrape_ts)

        # Take the max of the available timestamps, or default to today if both are empty
        if available_timestamps:
            timestamp_gte = max(available_timestamps)
        else:
            timestamp_gte = int(time.mktime(get_datetime(nowdate()).timetuple()))

        base_url = f"http://{conn_doc.waha_server_ip}" # e.g., http://localhost:3000
        
        # Ensure API key defaults to a string instead of None if not set
        api_key = conn_doc.get_password("api_key") or ""

        client = WAHAClient(base_url=base_url, api_key=api_key)

        # Try block added: Some versions of waha_python may reject kwargs they don't recognize
        try:
            all_messages = client.chats.get_messages(
                conn_doc.session_name,
                group.whatsapp_id,
                limit=100,
                downloadMedia=True
            )
        except TypeError:
            # Fallback if downloadMedia is not supported natively by your wrapper version
            all_messages = client.chats.get_messages(
                conn_doc.session_name,
                group.whatsapp_id,
                limit=100
            )

        inserted_count = 0
        for msg in all_messages:


            # --- ADD THIS NEW FILTER ---
            # Extract the internal message type (default to 'chat' if missing)
            msg_type = msg.get("_data", {}).get("type", "chat")
            
            # Skip system notifications, protocol messages, or call logs
            if msg_type in ["e2e_notification", "protocol", "call_log"]:
                continue
            # ---------------------------

            msg_ts = int(msg.get("timestamp", 0))
            if msg_ts < timestamp_gte:
                continue

            msg_id = msg.get("id")
            if isinstance(msg_id, dict):
                msg_id = msg_id.get("_serialized")

            if frappe.db.exists("WhatsApp Message", {"message_id": msg_id}):
                continue

            # 1. Create and INSERT the Message Doc FIRST
            new_msg = frappe.new_doc("WhatsApp Message")
            new_msg.whatsapp_connection = conn_doc.name
            new_msg.whatsapp_group = group.name
            new_msg.whatsapp_id = msg.get("from")
            new_msg.message_id = msg_id
            new_msg.session_name = conn_doc.session_name
            new_msg.message = msg.get("body")
            new_msg.direction = "Outgoing" if msg.get("fromMe") else "Incoming"
            new_msg.timestamp = get_datetime(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg_ts)))
            new_msg.raw_json = json.dumps(msg, indent=4)
            
            # Insert so the document gets a real ID in the database (new_msg.name)
            new_msg.insert(ignore_permissions=True)

            # 2. Handle Media AFTER the document exists
            if msg.get("hasMedia") and msg.get("media"):
                media_info = msg.get("media")
                # Safety fallback in case mimetype is None
                mimetype = media_info.get("mimetype") or "" 
                
                file_url = media_info.get("url")
                
                if file_url:
                    if "localhost" in file_url and conn_doc.waha_server_ip != "localhost":
                        file_url = file_url.replace("localhost:3000", conn_doc.waha_server_ip)

                    headers = {
                        "X-Api-Key": api_key
                    }
                    
                    try:
                        # Added timeout to prevent worker locking if the media server hangs
                        response = requests.get(file_url, headers=headers, stream=True, timeout=15)
                        
                        if response.status_code == 200:
                            # Safely extract extension
                            ext = mimetype.split('/')[-1].split(';')[0] if '/' in mimetype else "bin"
                            fname = f"{msg_id}.{ext}"
                            
                            ret_file = save_file(
                                fname,
                                response.content,
                                new_msg.doctype,
                                new_msg.name, # This is now a valid ID!
                                is_private=1
                            )
                            
                            # Update the already-inserted document
                            new_msg.has_media = 1
                            new_msg.attachment = ret_file.file_url
                            # Safely map the MIME-type to your Frappe Select Options
                            if 'image' in mimetype:
                                new_msg.media_type = "Image"
                            elif 'video' in mimetype:
                                new_msg.media_type = "Video"
                            elif 'audio' in mimetype:
                                new_msg.media_type = "Audio"
                            else:
                                # Catch-all for application/pdf, text/csv, zip files, etc.
                                new_msg.media_type = "Document"
                            new_msg.save(ignore_permissions=True)
                        else:
                            frappe.log_error(
                                title="WAHA Media Download Failed", 
                                message=f"Status: {response.status_code} | URL: {file_url}"
                            )
                    except Exception as e:
                        frappe.log_error(title="WAHA Media Request Exception", message=str(e))

            inserted_count += 1

        frappe.db.commit()
        return {"status": "success", "message": f"Fetched {inserted_count} new messages."}

    except (requests.exceptions.RequestException, ConnectionError, TimeoutError, OSError) as e:
        frappe.log_error(title="WAHA Server Unavailable", message=frappe.get_traceback())
        return {
            "status": "error",
            "message": _waha_offline_message(conn_doc) if "conn_doc" in locals() else "Could not reach WhatsApp server. Please start WAHA and try again.",
            "error": str(e),
        }
    except Exception as e:
        frappe.log_error(title="WAHA Fetch Group Messages Error", message=frappe.get_traceback())
        return {
            "status": "error",
            "message": "Could not fetch WhatsApp messages right now. Please check the WhatsApp server and Error Log.",
            "error": str(e),
        }
