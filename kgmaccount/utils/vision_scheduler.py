import frappe
import logging
from kgmaccount.utils import whatsapp_logger  # configure whatsapp log file

logger = logging.getLogger(__name__)

DEFAULT_MAX_IMAGE_RETRIES = 3

def fetch_and_process_unprocessed_whatsapp_messages():
    """
    Scheduled job that polls for messages, but checks your 
    WhatsApp AI Settings desk configuration before doing anything.
    """
    logger.info("fetch_and_process_unprocessed_whatsapp_messages started")
    print("[kgmaccount] fetch_and_process_unprocessed_whatsapp_messages started")
    # 1. Fetch live user settings from the Desk
    settings = frappe.get_doc("WhatsApp AI Settings")
    max_retries = max(
        1,
        int(getattr(settings, "max_image_processing_retries", 0) or DEFAULT_MAX_IMAGE_RETRIES),
    )
    
    # Check if master switch is turned OFF
    if not settings.enable_ai_worker:
        logger.info("AI worker disabled in WhatsApp AI Settings; aborting")
        print("[kgmaccount] AI worker disabled in WhatsApp AI Settings; aborting")
        return

    # Extract allowed group IDs into a clean Python list
    allowed_group_list = [row.group_id for row in settings.allowed_groups if row.group_id]
    if not allowed_group_list:
        logger.info("No allowed groups configured in WhatsApp AI Settings; aborting")
        print("[kgmaccount] No allowed groups configured; aborting")
        return # No groups configured, safely abort
    print(f"{allowed_group_list}")
    # 2. Query only messages from authorized groups that aren't processed yet
    unprocessed_messages = frappe.get_all(
        "WhatsApp Message",
        filters={
            "media_type": "Image",  # Capital 'I' and correct field name
            "has_media": 1,
            "is_ai_processed": 0,
            "ai_retry_count": ["<", max_retries],
            "whatsapp_group": ["in", allowed_group_list] # Correct field name
        },
        fields=["name"]
    )
    logger.info(f"Found {len(unprocessed_messages)} unprocessed WhatsApp messages")
    print(f"[kgmaccount] Found {len(unprocessed_messages)} unprocessed WhatsApp messages")
    
    # 3. Queue them for AI processing
    for msg in unprocessed_messages:
        # Mark as processed immediately to prevent double-polling collisions
        frappe.db.set_value(
            "WhatsApp Message",
            msg.name,
            {"is_ai_processed": 1, "ai_processing_status": "Processing"},
        )
        frappe.db.commit()
        logger.info(f"Enqueuing message {msg.name} for AI processing")
        print(f"[kgmaccount] Enqueuing message {msg.name} for AI processing")
        frappe.enqueue(
            "kgmaccount.utils.vision_parser.process_order_image",
            queue="long",
            timeout=300,
            whatsapp_message_id=msg.name
        )
