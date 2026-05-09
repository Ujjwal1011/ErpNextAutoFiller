import json
import time
import requests
import frappe
from frappe.utils import getdate, nowdate
from frappe.model.document import Document
from frappe.utils.data import get_datetime
from frappe.utils.file_manager import save_file

class WhatsAppGroup(Document): # <--- MUST match Doctype name (no spaces)
    pass




@frappe.whitelist()
def fetch_group_messages(group_docname):
    try:
        group = frappe.get_doc("WhatsApp Group", group_docname)
        if not group.whatsapp_connection:
            frappe.throw("This group is not linked to a WhatsApp Connection.")

        conn_doc = frappe.get_doc("WhatsApp Connection", group.whatsapp_connection)

        # Determine Start Timestamp
        last_message_time = frappe.db.get_value(
            "WhatsApp Message",
            {"whatsapp_group": group.name, "whatsapp_connection": conn_doc.name},
            "timestamp",
            order_by="timestamp desc"
        )

        if last_message_time:
            timestamp_gte = int(time.mktime(get_datetime(last_message_time).timetuple())) + 1
        else:
            fetch_date = group.get("fetch_from_date") or nowdate()
            timestamp_gte = int(time.mktime(getdate(fetch_date).timetuple()))

        base_url = f"http://{conn_doc.waha_server_ip}" # e.g., http://localhost:3000
        api_key = conn_doc.get_password("api_key")
        
        # Initialize your WAHA Client
        from waha_python import WAHAClient # Ensure this path is correct
        client = WAHAClient(base_url=base_url, api_key=api_key)

        all_messages = client.chats.get_messages(
            conn_doc.session_name,
            group.whatsapp_id,
            limit=100
        )

        inserted_count = 0
        for msg in all_messages:
            msg_ts = int(msg.get("timestamp", 0))
            if msg_ts < timestamp_gte:
                continue

            msg_id = msg.get("id")
            if isinstance(msg_id, dict):
                msg_id = msg_id.get("_serialized")

            if frappe.db.exists("WhatsApp Message", {"whatsapp_message_id": msg_id}):
                continue

            # Create the Message Doc
            new_msg = frappe.new_doc("WhatsApp Message")
            new_msg.whatsapp_connection = conn_doc.name
            new_msg.whatsapp_group = group.name
            new_msg.whatsapp_id = msg.get("from")
            new_msg.whatsapp_message_id = msg_id
            new_msg.message = msg.get("body")
            new_msg.direction = "Outgoing" if msg.get("fromMe") else "Incoming"
            new_msg.timestamp = get_datetime(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg_ts)))

            # Handle Media (Image/Audio/Video)
            if msg.get("hasMedia") and msg.get("media"):
                media_info = msg.get("media")
                mimetype = media_info.get("mimetype", "")
                
                # Use the URL from the JSON
                file_url = media_info.get("url")
                
                # If the URL is localhost but the server is remote, 
                # you might need to swap the base URL
                if "localhost" in file_url and conn_doc.waha_server_ip != "localhost":
                    file_url = file_url.replace("localhost:3000", conn_doc.waha_server_ip)

                response = requests.get(file_url, stream=True)
                
                if response.status_code == 200:
                    ext = mimetype.split('/')[-1].split(';')[0] # get 'jpeg' or 'ogg'
                    fname = f"{msg_id}.{ext}"
                    
                    # Save file to Frappe
                    ret_file = save_file(
                        fname,
                        response.content,
                        new_msg.doctype,
                        new_msg.name,
                        is_private=1
                    )
                    
                    new_msg.has_media = 1
                    new_msg.attachment = ret_file.file_url
                    new_msg.media_type = mimetype.split('/')[0].capitalize()

            new_msg.raw_json = json.dumps(msg, indent=4)
            new_msg.insert(ignore_permissions=True)
            inserted_count += 1

        frappe.db.commit()
        return {"status": "success", "message": f"Fetched {inserted_count} new messages."}

    except Exception:
        frappe.log_error(title="WAHA Fetch Group Messages Error", message=frappe.get_traceback())
        raise # Re-raising helps see the error in the console