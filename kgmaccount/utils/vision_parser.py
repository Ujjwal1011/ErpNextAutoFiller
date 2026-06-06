import frappe
import requests
import json
import base64
import os
import logging
from kgmaccount.utils import whatsapp_logger  # configures file handler

logger = logging.getLogger(__name__)

def process_order_image(whatsapp_message_id):
    try:
        logger.info(f"Processing WhatsApp message: {whatsapp_message_id}")
        print(f"[kgmaccount] Processing WhatsApp message: {whatsapp_message_id}")
        # Fetch live configuration values
        settings = frappe.get_doc("WhatsApp AI Settings")
        
        api_key = settings.get_password("openrouter_api_key")
        system_prompt = settings.system_prompt
        
        if not api_key or not system_prompt:
            raise ValueError("API Key or System Prompt missing in WhatsApp AI Settings")

        # Fetch message file attachment
        msg_doc = frappe.get_doc("WhatsApp Message", whatsapp_message_id)
        file_doc = frappe.get_doc("File", {"file_url": msg_doc.attachment})
        file_path = file_doc.get_full_path()
        logger.debug(f"Found attachment for message {whatsapp_message_id}: {file_path}")
        print(f"[kgmaccount] Found attachment: {file_path}")

        with open(file_path, "rb") as image_file:
            raw = image_file.read()
            base64_image = base64.b64encode(raw).decode('utf-8')
            logger.debug(f"Encoded image for message {whatsapp_message_id}, bytes={len(raw)}")
            print(f"[kgmaccount] Encoded image bytes={len(raw)}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "google/gemma-4-31b-it", 
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract the orders from this image."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        }

        logger.info(f"Sending image to OpenRouter for message {whatsapp_message_id}")
        print(f"[kgmaccount] Sending image to OpenRouter for message {whatsapp_message_id}")
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        logger.debug(f"OpenRouter response status: {response.status_code}")
        print(f"[kgmaccount] OpenRouter response status: {response.status_code}")

        response_json = response.json()
        # Try to extract model content safely
        llm_text_output = response_json.get('choices', [{}])[0].get('message', {}).get('content')

        # Strip potential markdown formatting if the model disobeys the prompt
        if isinstance(llm_text_output, str) and llm_text_output.startswith("```json"):
            llm_text_output = llm_text_output.replace("```json", "").replace("```", "").strip()
            logger.debug("Stripped markdown code fences from LLM output")

        # Attempt to parse LLM output to JSON, with several fallbacks
        extracted_data = None
        try:
            extracted_data = json.loads(llm_text_output)
        except Exception:
            import re
            # 1) Try fenced ```json blocks
            m = re.search(r"```(?:json\n)?(.*?)```", llm_text_output, re.S)
            if m:
                candidate = m.group(1).strip()
                try:
                    extracted_data = json.loads(candidate)
                except Exception:
                    logger.debug("Failed to parse fenced JSON block from LLM output")

            # 2) Try to find first {...} JSON object
            if extracted_data is None:
                m2 = re.search(r"(\{.*\})", llm_text_output, re.S)
                if m2:
                    candidate = m2.group(1)
                    try:
                        extracted_data = json.loads(candidate)
                    except Exception:
                        logger.debug("Failed to parse first {...} JSON substring from LLM output")

            # 3) Try to find a top-level array [ ... ]
            if extracted_data is None:
                m3 = re.search(r"(\[\s*\{.*\}\s*\])", llm_text_output, re.S)
                if m3:
                    candidate = m3.group(1)
                    try:
                        extracted_data = json.loads(candidate)
                    except Exception:
                        logger.debug("Failed to parse array JSON substring from LLM output")

            if extracted_data is None:
                # Log raw response for debugging and raise
                logger.error(f"Failed to parse LLM output as JSON. raw_output=\n{llm_text_output}")
                logger.debug(f"Full response JSON from OpenRouter: {json.dumps(response_json, indent=2)}")
                raise

        # Normalize extracted_data into a list of orders
        orders_list = []
        if isinstance(extracted_data, list):
            # Assume list is either list of orders or list containing a single dict
            orders_list = extracted_data
        elif isinstance(extracted_data, dict):
            # Preferred explicit key
            if "orders" in extracted_data and isinstance(extracted_data["orders"], list):
                orders_list = extracted_data["orders"]
            elif "order" in extracted_data and isinstance(extracted_data["order"], dict):
                orders_list = [extracted_data["order"]]
            else:
                # Heuristic: if dict looks like a single order (has 'items' or 'customer_name'), treat as single order
                if "items" in extracted_data or "customer_name" in extracted_data:
                    orders_list = [extracted_data]
                else:
                    # Search nested values for the first list-of-dicts
                    found = False
                    for v in extracted_data.values():
                        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                            orders_list = v
                            found = True
                            break
                    if not found:
                        orders_list = []

        # If still empty, log and raise with diagnostics
        if not orders_list:
            logger.error(f"LLM returned JSON but no 'orders' array was found. raw_output=\n{llm_text_output}")
            logger.debug(f"Parsed JSON from LLM: {json.dumps(extracted_data, indent=2)}")
            raise ValueError("LLM returned JSON, but no 'orders' array was found.")

        created = []
        for single_order in orders_list:
            # Create a SEPARATE staging document for each order
            staging_doc = frappe.get_doc({
                "doctype": "WhatsApp Order Staging",
                "whatsapp_message": whatsapp_message_id,
                "parent_image": msg_doc.attachment,
                "status": "Pending",
                # Save ONLY this specific order's data, not the whole array
                "extracted_data_json": json.dumps(single_order, indent=4)
            })
            staging_doc.insert(ignore_permissions=True)
            created.append(staging_doc.name)

        # Commit all new staging documents to the database at once
        frappe.db.commit()

        logger.info(f"Created {len(created)} WhatsApp Order Staging docs for message {whatsapp_message_id}: {', '.join(created)}")
        print(f"[kgmaccount] Created {len(created)} staging docs for message {whatsapp_message_id}")

    except Exception as e:
        frappe.db.rollback()
        logger.exception(f"Failed to process WhatsApp message {whatsapp_message_id}: {e}")
        print(f"[kgmaccount] ERROR processing message {whatsapp_message_id}: {e}")
        # Mark back to 0 if parsing failed so it can be retried later
        try:
            frappe.db.set_value("WhatsApp Message", whatsapp_message_id, "is_ai_processed", 0)
            frappe.db.commit()
        except Exception:
            logger.exception("Failed to reset is_ai_processed flag")
            print("[kgmaccount] ERROR resetting is_ai_processed flag")
        frappe.log_error(title=f"Vision Extraction Failure: {whatsapp_message_id}", message=frappe.get_traceback())