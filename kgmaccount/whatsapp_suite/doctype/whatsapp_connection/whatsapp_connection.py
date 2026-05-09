import frappe
from frappe.model.document import Document
from waha_python import WAHAClient, WAHAAuthenticationError, WAHANotFoundError

class WhatsAppConnection(Document):
    pass

@frappe.whitelist()
def test_waha_connection(ip, session_name, api_key, docname=None):
    """Pings the WAHA server to check if it is alive and the session exists."""
    logger = frappe.logger("whatsapp_suite")
    
    # --- FRAPPE PASSWORD FIX ---
    # If the frontend sends asterisks, fetch the real decrypted password
    if api_key and "*" in api_key and docname:
        doc = frappe.get_doc("WhatsApp Connection", docname)
        api_key = doc.get_password("api_key")
    # ---------------------------

    logger.info(f"Initiating WAHA connection test for IP: {ip}, Session: {session_name}")
    
    try:
        # Initialize WAHA client
        base_url = f"http://{ip}"
        client = WAHAClient(base_url=base_url, api_key=api_key)
        
        # Try to get the session to verify connection
        session = client.sessions.get(session_name)
        
        logger.info("WAHA connection test successful.")
        return {"status": "success", "message": "Successfully connected to WAHA!"}
            
    except WAHAAuthenticationError as e:
        error_msg = f"Authentication Error: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(title="WAHA Authentication Failed", message=error_msg)
        return {"status": "error", "message": f"Authentication failed: {str(e)}"}
        
    except WAHANotFoundError as e:
        error_msg = f"Session not found: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(title="WAHA Session Not Found", message=error_msg)
        return {"status": "error", "message": f"Session not found: {str(e)}"}
            
    except Exception as e:
        error_msg = f"Network Error: Could not reach WAHA server at {ip}. Error: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(title="WAHA Network Timeout/Error", message=error_msg)
        return {"status": "error", "message": f"Could not reach WAHA server: {str(e)}"}

@frappe.whitelist()
def generate_qr_code(ip, session_name, api_key, docname=None):
    """Fetches the QR code data from the WAHA API."""
    logger = frappe.logger("whatsapp_suite")
    
    # --- FRAPPE PASSWORD FIX ---
    if api_key and "*" in api_key and docname:
        
        doc = frappe.get_doc("WhatsApp Connection", docname)
        api_key = doc.get_password("api_key")
    # ---------------------------

    logger.info(f"Requesting QR Code from WAHA for Session: {session_name}")
    
    try:
        base_url = f"http://{ip}"
        client = WAHAClient(base_url=base_url, api_key=api_key)
        
        # Get QR code from session
        qr_data = client.sessions.get_qr(session_name, accept_json=True)
        
        logger.info("QR Code successfully fetched from WAHA.")
        return {"status": "success", "qr_data": qr_data.get("data")} 
            
    except WAHAAuthenticationError as e:
        error_msg = f"Authentication Error while fetching QR: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(title="WAHA QR Authentication Failed", message=error_msg)
        return {"status": "error", "message": f"Authentication failed: {str(e)}"}
        
    except WAHANotFoundError as e:
        error_msg = f"Session not found for QR: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(title="WAHA QR Session Not Found", message=error_msg)
        return {"status": "error", "message": "Failed to fetch QR code. Is the session running?"}
            
    except Exception as e:
        error_msg = f"Exception during QR fetch: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(title="WAHA QR Fetch Exception", message=error_msg)
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def sync_waha_chats(connection_name=None):
    """Fetches chats from WAHA and upserts them into the Frappe WhatsApp Group DocType."""
    logger = frappe.logger("whatsapp_suite")
    logger.info("Starting WhatsApp Group Sync...")
    
    # 1. Resolve Connection
    if connection_name:
        conn_doc = frappe.get_doc("WhatsApp Connection", connection_name)
    else:
        connections = frappe.get_all("WhatsApp Connection", fields=['name'], limit=1)
        if not connections:
            return {"status": "error", "message": "Please set up a WhatsApp Connection first."}
        conn_doc = frappe.get_doc("WhatsApp Connection", connections[0].name)

    ip = conn_doc.waha_server_ip
    session_name = conn_doc.session_name
    api_key = conn_doc.get_password("api_key") 

    try:
        base_url = f"http://{ip}"
        client = WAHAClient(base_url=base_url, api_key=api_key)
        
        # FIX: Ensure we pass the session keyword
        api_chats = client.chats.list(session=session_name)
        print(api_chats)
        new_count = 0
        updates_count = 0

        for chat in api_chats:
            # FIX: waha-python usually returns objects. Try attribute access first.
            raw_id = getattr(chat, 'id', None)
            if not raw_id and isinstance(chat, dict):
                raw_id = chat.get('id')

            # Handle the '_serialized' nested structure
            if isinstance(raw_id, dict):
                chat_id = raw_id.get('_serialized')
            else:
                chat_id = str(raw_id)

            if not chat_id:
                continue

            # Resolve Name (Name for individuals, Subject for groups)
            name = getattr(chat, 'name', None) or getattr(chat, 'subject', None)
            if not name and isinstance(chat, dict):
                name = chat.get('name') or chat.get('subject')
            
            name = name or "Unknown"

            # 2. Sync Logic
            filters = {"whatsapp_id": chat_id}
            if frappe.db.exists("WhatsApp Group", filters):
                # Using db.set_value is faster for bulk updates
                doc_name = frappe.db.get_value("WhatsApp Group", filters, "name")
                frappe.db.set_value("WhatsApp Group", doc_name, {
                    "group_name": name,
                    "whatsapp_connection": conn_doc.name
                })
                updates_count += 1
            else:
                doc = frappe.new_doc("WhatsApp Group")
                doc.whatsapp_id = chat_id
                doc.group_name = name
                doc.whatsapp_connection = conn_doc.name
                doc.scraping_enabled = 0 
                doc.insert(ignore_permissions=True)
                new_count += 1

        frappe.db.commit()
        return {
            "status": "success", 
            "message": f"Sync Complete! Added {new_count} new, Updated {updates_count} groups."
        }
        
    except Exception as e:
        # Catch-all for debugging
        error_msg = f"WAHA Sync Error: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(title="WAHA Sync Failed", message=frappe.get_traceback())
        return {"status": "error", "message": str(e)}





@frappe.whitelist(allow_guest=True)
def handle_incoming_webhook():
    """
    Receives inbound POST payloads from WAHA and stores each 'message' event
    as a WhatsApp Message document in Frappe.
    """
    logger = frappe.logger("whatsapp_suite")

    try:
        # Frappe natively parses incoming JSON into a dictionary
        payload = frappe.request.get_json(force=True)

        if not payload:
            logger.warning("Webhook received with empty payload.")
            return {"status": "error", "message": "Empty payload"}

        event   = payload.get("event")
        session = payload.get("session")
        msg     = payload.get("payload", {})

        logger.info(f"Webhook received — event: {event}, session: {session}")

        if event != "message":
            logger.info(f"Ignoring non-message event: {event}")
            return {"status": "ignored", "event": event}

        chat_id = msg.get("from") or msg.get("chatId")
        body    = msg.get("body", "")

        doc             = frappe.new_doc("WhatsApp Message")
        doc.whatsapp_id = chat_id
        doc.message     = body
        doc.session     = session
        doc.direction   = "Incoming"
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        logger.info(f"Saved incoming message from {chat_id}.")
        return {"status": "ok", "message": "Saved"}

    except Exception as e:
        error_msg = f"Webhook processing error: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(title="WAHA Webhook Error", message=error_msg)
        return {"status": "error", "message": str(e)}