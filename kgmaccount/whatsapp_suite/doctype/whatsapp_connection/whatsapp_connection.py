import frappe
from frappe.model.document import Document
from waha_python import WAHAClient, WAHAAuthenticationError, WAHANotFoundError
from kgmaccount.whatsapp_suite.permissions import assert_whatsapp_admin
from urllib.parse import urlparse

class WhatsAppConnection(Document):
    pass


def _waha_offline_message(ip):
    return (
        f"Could not reach WhatsApp server at {ip}. "
        "Please start the WAHA server and try again."
    )


def _resolve_api_key(api_key=None, docname=None):
    if api_key and "*" in api_key and docname:
        doc = frappe.get_doc("WhatsApp Connection", docname)
        return doc.get_password("api_key")
    return api_key


def _waha_base_urls(ip):
    """Return reachable candidates for host and Docker-host WAHA setups."""
    value = str(ip or "").strip()
    if not value:
        return []

    parsed = urlparse(value if "://" in value else f"http://{value}")
    host = parsed.hostname or value.split(":")[0]
    port = parsed.port
    path = parsed.path.rstrip("/") if parsed.path and parsed.path != "/" else ""

    candidates = []
    hosts = [host]
    if port:
        hosts.extend(["host.docker.internal", "localhost", "127.0.0.1"])

    for candidate_host in hosts:
        if not candidate_host:
            continue
        netloc = candidate_host
        if port:
            netloc = f"{candidate_host}:{port}"
        url = f"http://{netloc}{path}"
        if url not in candidates:
            candidates.append(url)

    return candidates

@frappe.whitelist()
def test_waha_connection(ip, session_name, api_key, docname=None):
    """Pings the WAHA server to check if it is alive and the session exists."""
    assert_whatsapp_admin()
    logger = frappe.logger("whatsapp_suite")
    
    api_key = _resolve_api_key(api_key, docname)

    logger.info(f"Initiating WAHA connection test for IP: {ip}, Session: {session_name}")

    last_error = None
    for base_url in _waha_base_urls(ip):
        try:
            client = WAHAClient(base_url=base_url, api_key=api_key)
            client.sessions.get(session_name)

            logger.info(f"WAHA connection test successful via {base_url}.")
            return {"status": "success", "message": f"Successfully connected to WAHA using {base_url}!"}

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
            last_error = e
            logger.warning(f"WAHA connection test failed via {base_url}: {str(e)}")

    error_msg = f"Network Error: Could not reach WAHA server at {ip}. Error: {str(last_error)}"
    logger.error(error_msg)
    frappe.log_error(title="WAHA Network Timeout/Error", message=error_msg)
    return {"status": "error", "message": _waha_offline_message(ip), "error": str(last_error)}

@frappe.whitelist()
def generate_qr_code(ip, session_name, api_key, docname=None):
    """Fetches the QR code data from the WAHA API."""
    assert_whatsapp_admin()
    logger = frappe.logger("whatsapp_suite")
    
    api_key = _resolve_api_key(api_key, docname)

    logger.info(f"Requesting QR Code from WAHA for Session: {session_name}")
    
    last_error = None
    for base_url in _waha_base_urls(ip):
        try:
            client = WAHAClient(base_url=base_url, api_key=api_key)
            qr_data = client.sessions.get_qr(session_name, accept_json=True)

            logger.info(f"QR Code successfully fetched from WAHA via {base_url}.")
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
            last_error = e
            logger.warning(f"QR fetch failed via {base_url}: {str(e)}")

    error_msg = f"Exception during QR fetch: {str(last_error)}"
    logger.error(error_msg)
    frappe.log_error(title="WAHA QR Fetch Exception", message=error_msg)
    return {"status": "error", "message": _waha_offline_message(ip), "error": str(last_error)}


@frappe.whitelist()
def start_default_session(ip=None, session_name=None, api_key=None, docname=None):
    """Starts the configured WAHA session, defaulting to the WAHA `default` session."""
    assert_whatsapp_admin()
    logger = frappe.logger("whatsapp_suite")

    if docname:
        doc = frappe.get_doc("WhatsApp Connection", docname)
        ip = ip or doc.waha_server_ip
        session_name = session_name or doc.session_name
        api_key = doc.get_password("api_key")
    else:
        api_key = _resolve_api_key(api_key, docname)

    session_name = session_name or "default"

    attempted_urls = _waha_base_urls(ip)
    last_error = None

    for base_url in attempted_urls:
        try:
            client = WAHAClient(base_url=base_url, api_key=api_key)
            try:
                client.sessions.start(session_name)
                action = "started"
            except WAHANotFoundError:
                client.sessions.create(name=session_name, start=True)
                action = "created and started"

            logger.info(f"WAHA session {action}: {session_name} via {base_url}")
            return {
                "status": "success",
                "message": f"WAHA session '{session_name}' {action} successfully using {base_url}.",
                "base_url": base_url,
            }

        except WAHAAuthenticationError as e:
            error_msg = f"Authentication Error while starting session: {str(e)}"
            logger.error(error_msg)
            frappe.log_error(title="WAHA Session Start Authentication Failed", message=error_msg)
            return {"status": "error", "message": f"Authentication failed: {str(e)}"}

        except Exception as e:
            last_error = e
            logger.warning(f"Could not start WAHA session {session_name} via {base_url}: {str(e)}")

    error_msg = f"Exception while starting WAHA session {session_name}: {str(last_error)}"
    logger.error(error_msg)
    frappe.log_error(title="WAHA Session Start Failed", message=frappe.get_traceback())
    return {
        "status": "error",
        "message": (
            f"Could not reach/start WAHA using: {', '.join(attempted_urls) or ip}. "
            "Make sure the WAHA container/server is running, then try again."
        ),
        "error": str(last_error) if last_error else None,
    }

@frappe.whitelist()
def sync_waha_chats(connection_name=None):
    """Fetches chats from WAHA and upserts them into the Frappe WhatsApp Group DocType."""
    assert_whatsapp_admin()
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

    last_error = None
    for base_url in _waha_base_urls(ip):
        try:
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
                "message": (
                    f"Sync Complete using {base_url}! "
                    f"Added {new_count} new, Updated {updates_count} groups."
                )
            }

        except Exception as e:
            last_error = e
            logger.warning(f"WAHA sync failed via {base_url}: {str(e)}")

    error_msg = f"WAHA Sync Error: {str(last_error)}"
    logger.error(error_msg)
    frappe.log_error(title="WAHA Sync Failed", message=frappe.get_traceback())
    return {"status": "error", "message": _waha_offline_message(ip), "error": str(last_error)}





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
        msg_id  = msg.get("id")
        if isinstance(msg_id, dict):
            msg_id = msg_id.get("_serialized")

        doc             = frappe.new_doc("WhatsApp Message")
        doc.whatsapp_id = chat_id
        doc.message_id  = msg_id
        doc.message     = body
        doc.session_name = session
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
