import base64
import json
import re
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate, get_first_day, get_datetime, getdate, now, now_datetime, today
from frappe.utils.file_manager import save_file
from waha_python import WAHAClient

from kgmaccount.auto_filler.doctype.sales_order_batch_print.sales_order_batch_print import get_sales_orders
from kgmaccount.whatsapp_suite.doctype.whatsapp_connection.whatsapp_connection import _waha_base_urls
from kgmaccount.whatsapp_suite.permissions import assert_whatsapp_admin


DEFAULT_COUNTRY_CODE = "91"
PRINT_FORMAT = "Sales Order Batch Printing With Status"
STATEMENT_STATUSES = ("Draft", "Ready", "Sending", "Sent", "Delivered", "Read", "Replied", "Failed")
STATUS_RANK = {
	"Draft": 0,
	"Ready": 0,
	"Sending": 1,
	"Failed": 1,
	"Sent": 2,
	"Delivered": 3,
	"Read": 4,
	"Replied": 5,
}


def _get_value(row, key, default=None):
	if row is None:
		return default
	if isinstance(row, dict):
		return row.get(key, default)
	return getattr(row, key, default)


def _as_json(data):
	try:
		return json.dumps(data, default=str)
	except Exception:
		return frappe.as_json(data)


def normalize_phone(phone, default_country_code=DEFAULT_COUNTRY_CODE):
	"""Return WhatsApp-ready digits. Ten-digit numbers default to India."""
	digits = re.sub(r"\D", "", str(phone or ""))
	if digits.startswith("00"):
		digits = digits[2:]
	if len(digits) == 10:
		digits = f"{default_country_code}{digits}"
	return digits


def chat_id_from_phone(phone):
	digits = normalize_phone(phone)
	return f"{digits}@c.us" if digits else ""


def _resolve_contact_name(contact):
	name = _get_value(contact, "name")
	full_name = _get_value(contact, "full_name")
	first_name = _get_value(contact, "first_name")
	last_name = _get_value(contact, "last_name")
	return full_name or " ".join(part for part in [first_name, last_name] if part) or name


def _contact_fields():
	fields = ["name", "first_name", "last_name", "full_name", "mobile_no", "phone", "is_primary_contact"]
	try:
		if frappe.get_meta("Contact").has_field("is_billing_contact"):
			fields.append("is_billing_contact")
	except Exception:
		fields.append("is_billing_contact")
	return fields


def _linked_customer_contacts(customer):
	if not customer:
		return []

	links = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"},
		fields=["parent"],
		order_by="idx asc",
	)
	contact_names = []
	for link in links:
		parent = _get_value(link, "parent")
		if parent and parent not in contact_names:
			contact_names.append(parent)

	if not contact_names:
		return []

	contacts = frappe.get_all(
		"Contact",
		filters={"name": ["in", contact_names]},
		fields=_contact_fields(),
	)
	contact_by_name = {_get_value(contact, "name"): contact for contact in contacts}
	return [contact_by_name[name] for name in contact_names if name in contact_by_name]


def _contact_primary_phone(contact_name):
	if not contact_name:
		return None

	phones = frappe.get_all(
		"Contact Phone",
		filters={"parenttype": "Contact", "parent": contact_name},
		fields=["phone", "is_primary_mobile_no", "is_primary_phone"],
		order_by="idx asc",
	)
	if not phones:
		return None

	for phone in phones:
		if cint(_get_value(phone, "is_primary_mobile_no")) and _get_value(phone, "phone"):
			return _get_value(phone, "phone")
	for phone in phones:
		if cint(_get_value(phone, "is_primary_phone")) and _get_value(phone, "phone"):
			return _get_value(phone, "phone")
	for phone in phones:
		if _get_value(phone, "phone"):
			return _get_value(phone, "phone")

	return None


def _pick_contact_phone(contact):
	return _get_value(contact, "mobile_no") or _get_value(contact, "phone") or _contact_primary_phone(_get_value(contact, "name"))


def _find_contact_for_phone(contacts, phone, primary_contact=None):
	target = normalize_phone(phone)
	if not target:
		return None

	for contact in contacts:
		if primary_contact and _get_value(contact, "name") == primary_contact and normalize_phone(_pick_contact_phone(contact)) == target:
			return contact

	for contact in contacts:
		if normalize_phone(_pick_contact_phone(contact)) == target:
			return contact

	return None


def _recipient_payload(customer, customer_name, phone, source, contact=None):
	digits = normalize_phone(phone)
	if not digits:
		frappe.throw(_("No WhatsApp phone number found for customer {0}.").format(customer_name or customer))

	contact_name = _get_value(contact, "name")
	return {
		"customer": customer,
		"customer_name": customer_name or customer,
		"recipient_contact": contact_name,
		"recipient_contact_name": _resolve_contact_name(contact) if contact else None,
		"recipient_phone": digits,
		"recipient_chat_id": chat_id_from_phone(digits),
		"recipient_source": source,
	}


def resolve_customer_whatsapp_recipient(customer):
	"""Resolve the default WhatsApp recipient from Customer/Contact only.

	Sales Order custom fields are intentionally not read here.
	"""
	if not customer:
		frappe.throw(_("Customer is required to resolve WhatsApp recipient."))

	customer_row = frappe.db.get_value(
		"Customer",
		customer,
		["name", "customer_name", "mobile_no", "customer_primary_contact"],
		as_dict=True,
	)
	if not customer_row:
		frappe.throw(_("Customer {0} was not found.").format(customer))

	customer_name = _get_value(customer_row, "customer_name") or customer
	primary_contact = _get_value(customer_row, "customer_primary_contact")
	customer_mobile = _get_value(customer_row, "mobile_no")
	if customer_mobile:
		contact = {"name": primary_contact} if primary_contact else None
		if not contact:
			contact = _find_contact_for_phone(_linked_customer_contacts(customer), customer_mobile)
		return _recipient_payload(
			customer,
			customer_name,
			customer_mobile,
			"Customer Mobile No",
			contact,
		)

	contacts = _linked_customer_contacts(customer)
	for contact in contacts:
		if cint(_get_value(contact, "is_billing_contact")) and _pick_contact_phone(contact):
			return _recipient_payload(customer, customer_name, _pick_contact_phone(contact), "Billing Contact", contact)

	for contact in contacts:
		is_primary = cint(_get_value(contact, "is_primary_contact")) or _get_value(contact, "name") == primary_contact
		if is_primary and _pick_contact_phone(contact):
			return _recipient_payload(customer, customer_name, _pick_contact_phone(contact), "Primary Contact", contact)

	for contact in contacts:
		if _pick_contact_phone(contact):
			return _recipient_payload(customer, customer_name, _pick_contact_phone(contact), "First Contact With Phone", contact)

	frappe.throw(_("No Customer or linked Contact mobile number found for {0}.").format(customer_name))


def _date_string(value):
	if not value:
		return None
	return str(getdate(value))


def _get_statement_orders(customer, from_date, to_date, include_draft=1, include_submitted=1):
	orders = get_sales_orders(customer, from_date, to_date, include_draft, include_submitted)
	return [frappe._dict(order) for order in orders]


def _statement_total(orders):
	return sum(flt(_get_value(order, "grand_total")) for order in orders)


def build_statement_message(customer_name, from_date, to_date, order_count, total_amount):
	return _(
		"Hello {0}, please find attached your Sales Order statement for {1} to {2}. "
		"It includes {3} Sales Order(s), total {4}."
	).format(
		customer_name,
		formatdate(from_date),
		formatdate(to_date),
		cint(order_count),
		frappe.format_value(total_amount, {"fieldtype": "Currency"}),
	)


def _order_rows_for_response(orders):
	rows = []
	for order in orders:
		name = _get_value(order, "name")
		rows.append(
			{
				"name": name,
				"customer": _get_value(order, "customer"),
				"transaction_date": _date_string(_get_value(order, "transaction_date")),
				"grand_total": flt(_get_value(order, "grand_total")),
				"docstatus": cint(_get_value(order, "docstatus")),
				"sales_order_status": _get_value(order, "sales_order_status"),
				"modified": frappe.db.get_value("Sales Order", name, "modified") if name else None,
			}
		)
	return rows


@frappe.whitelist()
def get_statement_preview(sales_order=None, customer=None, from_date=None, to_date=None):
	if sales_order:
		sales_order_row = frappe.db.get_value("Sales Order", sales_order, ["name", "customer"], as_dict=True)
		if not sales_order_row:
			frappe.throw(_("Sales Order {0} was not found.").format(sales_order))
		customer = _get_value(sales_order_row, "customer")

	if not customer:
		frappe.throw(_("Customer is required."))

	to_date = _date_string(to_date or today())
	from_date = _date_string(from_date or get_first_day(to_date))
	recipient = resolve_customer_whatsapp_recipient(customer)
	orders = _get_statement_orders(customer, from_date, to_date)
	total_amount = _statement_total(orders)
	message = build_statement_message(recipient["customer_name"], from_date, to_date, len(orders), total_amount)

	return {
		"customer": customer,
		"customer_name": recipient["customer_name"],
		"from_date": from_date,
		"to_date": to_date,
		"recipient": recipient,
		"message": message,
		"order_count": len(orders),
		"total_amount": total_amount,
		"orders": _order_rows_for_response(orders),
		"print_format": PRINT_FORMAT,
	}


@frappe.whitelist()
def get_statement_summary(customer, from_date, to_date):
	if not customer:
		frappe.throw(_("Customer is required."))
	orders = _get_statement_orders(customer, from_date, to_date)
	total_amount = _statement_total(orders)
	return {
		"order_count": len(orders),
		"total_amount": total_amount,
		"orders": _order_rows_for_response(orders),
		"message": build_statement_message(
			frappe.db.get_value("Customer", customer, "customer_name") or customer,
			from_date,
			to_date,
			len(orders),
			total_amount,
		),
	}


@frappe.whitelist()
def get_statement_form_data(customer, from_date, to_date):
	if not customer:
		frappe.throw(_("Customer is required."))

	from_date = _date_string(from_date)
	to_date = _date_string(to_date)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
	orders = _get_statement_orders(customer, from_date, to_date)
	total_amount = _statement_total(orders)
	recipient = None
	recipient_error = None

	try:
		recipient = resolve_customer_whatsapp_recipient(customer)
	except Exception as exc:
		recipient_error = str(exc)

	return {
		"customer": customer,
		"customer_name": customer_name,
		"from_date": from_date,
		"to_date": to_date,
		"recipient": recipient,
		"recipient_error": recipient_error,
		"order_count": len(orders),
		"total_amount": total_amount,
		"orders": _order_rows_for_response(orders),
		"message": build_statement_message(customer_name, from_date, to_date, len(orders), total_amount),
	}


def _make_batch_print(customer, from_date, to_date, orders):
	batch = frappe.new_doc("Sales Order Batch Print")
	batch.customer = customer
	batch.from_date = from_date
	batch.to_date = to_date
	batch.include_draft = 1
	batch.include_submitted = 1
	for order in orders:
		batch.append(
			"sales_orders",
			{
				"sales_order": _get_value(order, "name"),
				"sales_order_status": _get_value(order, "sales_order_status"),
				"customer": _get_value(order, "customer"),
				"transaction_date": _get_value(order, "transaction_date"),
				"grand_total": _get_value(order, "grand_total"),
			},
		)
	batch.insert(ignore_permissions=True)
	return batch


def _ensure_statement_batch(statement):
	if statement.source_batch:
		return

	items = statement.get("items", [])
	if not items:
		frappe.throw(_("Fetch Sales Orders before sending this WhatsApp statement."))

	batch = frappe.new_doc("Sales Order Batch Print")
	batch.customer = statement.customer
	batch.from_date = statement.from_date
	batch.to_date = statement.to_date
	batch.include_draft = 1
	batch.include_submitted = 1
	for item in items:
		if not item.sales_order:
			continue
		batch.append(
			"sales_orders",
			{
				"sales_order": item.sales_order,
				"sales_order_status": item.sales_order_status,
				"customer": statement.customer,
				"transaction_date": item.transaction_date,
				"grand_total": item.grand_total_at_send,
			},
		)

	batch.insert(ignore_permissions=True)
	statement.source_batch = batch.name
	statement.save(ignore_permissions=True)


def _snapshot_statement_items(statement, orders):
	for order in orders:
		name = _get_value(order, "name")
		modified = frappe.db.get_value("Sales Order", name, "modified")
		statement.append(
			"items",
			{
				"sales_order": name,
				"transaction_date": _get_value(order, "transaction_date"),
				"docstatus_at_send": cint(_get_value(order, "docstatus")),
				"sales_order_status": _get_value(order, "sales_order_status"),
				"grand_total_at_send": flt(_get_value(order, "grand_total")),
				"modified_at_send": modified,
			},
		)


@frappe.whitelist()
def prepare_statement(customer, from_date, to_date, recipient_phone, message=None, source_sales_order=None):
	assert_whatsapp_admin()
	if not customer:
		frappe.throw(_("Customer is required."))
	if not recipient_phone:
		frappe.throw(_("Recipient phone is required."))
	from_date = _date_string(from_date)
	to_date = _date_string(to_date)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	orders = _get_statement_orders(customer, from_date, to_date)
	if not orders:
		frappe.throw(_("No Sales Orders found for the selected customer and date range."))

	customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
	total_amount = _statement_total(orders)
	message = message or build_statement_message(customer_name, from_date, to_date, len(orders), total_amount)
	recipient_digits = normalize_phone(recipient_phone)
	default_recipient = None
	try:
		default_recipient = resolve_customer_whatsapp_recipient(customer)
	except Exception:
		default_recipient = None

	batch = _make_batch_print(customer, from_date, to_date, orders)

	statement = frappe.new_doc("WhatsApp Statement Send")
	statement.customer = customer
	statement.customer_name = customer_name
	statement.from_date = from_date
	statement.to_date = to_date
	statement.recipient_phone = recipient_digits
	statement.recipient_chat_id = chat_id_from_phone(recipient_digits)
	if default_recipient and default_recipient.get("recipient_phone") == recipient_digits:
		statement.recipient_contact = default_recipient.get("recipient_contact")
	statement.message = message
	statement.status = "Ready"
	statement.source_sales_order = source_sales_order
	statement.source_batch = batch.name
	statement.order_count = len(orders)
	statement.total_amount = total_amount
	statement.sent_by = frappe.session.user
	_snapshot_statement_items(statement, orders)
	statement.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"status": "ready",
		"statement": statement.name,
		"batch": batch.name,
		"order_count": len(orders),
		"total_amount": total_amount,
		"print_format": PRINT_FORMAT,
	}


def _get_default_connection():
	connections = frappe.get_all("WhatsApp Connection", fields=["name"], limit=1)
	if not connections:
		frappe.throw(_("Please set up a WhatsApp Connection first."))
	name = _get_value(connections[0], "name")
	return frappe.get_doc("WhatsApp Connection", name)


def _get_waha_client(connection):
	api_key = connection.get_password("api_key")
	last_error = None
	for base_url in _waha_base_urls(connection.waha_server_ip):
		try:
			client = WAHAClient(base_url=base_url, api_key=api_key)
			client.sessions.get(connection.session_name)
			return client, base_url
		except Exception as exc:
			last_error = exc

	frappe.throw(
		_("Could not reach WhatsApp server {0}: {1}").format(connection.waha_server_ip, str(last_error))
	)


def _validate_waha_number(client, session_name, recipient_phone):
	digits = normalize_phone(recipient_phone)
	if not digits:
		frappe.throw(_("Recipient phone is required."))
	result = client.contacts.check_exists(session_name, digits)
	number_exists = bool(_get_value(result, "numberExists"))
	chat_id = _get_value(result, "chatId") or chat_id_from_phone(digits)
	if not number_exists:
		frappe.throw(_("WAHA could not find a WhatsApp account for {0}.").format(digits))
	return digits, chat_id, result


def _attach_statement_pdf(statement):
	if not statement.source_batch:
		frappe.throw(_("Statement {0} is not linked to a Sales Order Batch Print.").format(statement.name))

	attachment = frappe.attach_print(
		"Sales Order Batch Print",
		statement.source_batch,
		file_name=f"{statement.customer}-{statement.from_date}-{statement.to_date}-Sales-Order-Statement",
		print_format=PRINT_FORMAT,
	)
	file_doc = save_file(
		attachment["fname"],
		attachment["fcontent"],
		"WhatsApp Statement Send",
		statement.name,
		is_private=1,
	)
	statement.pdf_file = file_doc.file_url
	statement.save(ignore_permissions=True)
	return attachment, file_doc


def _create_outgoing_message(statement, connection, attachment):
	doc = frappe.new_doc("WhatsApp Message")
	doc.whatsapp_connection = connection.name
	doc.whatsapp_id = statement.recipient_chat_id
	doc.to_chat_id = statement.recipient_chat_id
	doc.direction = "Outgoing"
	doc.message = statement.message
	doc.timestamp = now()
	doc.session_name = connection.session_name
	doc.has_media = 1
	doc.media_type = "Document"
	doc.attachment = statement.pdf_file
	doc.send_status = "Sending"
	doc.reference_doctype = "WhatsApp Statement Send"
	doc.reference_name = statement.name
	doc.whatsapp_statement_send = statement.name
	doc.raw_json = _as_json({"filename": attachment["fname"]})
	doc.insert(ignore_permissions=True)
	return doc


def extract_waha_message_id(payload):
	if not payload:
		return None
	for key in ("message_id", "messageId", "id"):
		value = _get_value(payload, key)
		if not value:
			continue
		if isinstance(value, dict):
			return value.get("_serialized") or value.get("id") or value.get("serialized")
		return str(value)
	data = _get_value(payload, "_data")
	if isinstance(data, dict):
		return extract_waha_message_id(data)
	return None


def _mark_failed(statement, error):
	statement.status = "Failed"
	statement.last_error = str(error)
	statement.last_status_at = now()
	statement.save(ignore_permissions=True)
	frappe.db.commit()


@frappe.whitelist()
def send_statement(statement_name):
	assert_whatsapp_admin()
	statement = frappe.get_doc("WhatsApp Statement Send", statement_name)
	if statement.status not in ("Ready", "Draft", "Failed"):
		frappe.throw(_("Statement {0} is already {1}.").format(statement.name, statement.status))

	try:
		connection = frappe.get_doc("WhatsApp Connection", statement.whatsapp_connection) if statement.whatsapp_connection else _get_default_connection()
		_ensure_statement_batch(statement)
		client, base_url = _get_waha_client(connection)
		recipient_phone, chat_id, validation = _validate_waha_number(client, connection.session_name, statement.recipient_phone)

		statement.status = "Sending"
		statement.recipient_phone = recipient_phone
		statement.recipient_chat_id = chat_id
		statement.whatsapp_connection = connection.name
		statement.session_name = connection.session_name
		statement.last_error = None
		statement.last_status_at = now()
		statement.save(ignore_permissions=True)

		attachment, _file_doc = _attach_statement_pdf(statement)
		message_doc = _create_outgoing_message(statement, connection, attachment)
		response = client.messages.send_file(
			session=connection.session_name,
			chat_id=chat_id,
			file={
				"data": base64.b64encode(attachment["fcontent"]).decode("utf-8"),
				"mimetype": "application/pdf",
				"filename": attachment["fname"],
			},
			caption=statement.message,
		)
		message_id = extract_waha_message_id(response)

		message_doc.message_id = message_id
		message_doc.send_status = "Sent"
		message_doc.raw_json = _as_json(response)
		message_doc.save(ignore_permissions=True)

		statement.whatsapp_message = message_doc.name
		statement.waha_message_id = message_id
		statement.status = "Sent"
		statement.sent_at = now()
		statement.last_status_at = statement.sent_at
		statement.raw_response = _as_json({"base_url": base_url, "validation": validation, "send": response})
		statement.save(ignore_permissions=True)
		frappe.db.commit()
		return {"status": "sent", "statement": statement.name, "message_id": message_id}
	except Exception as exc:
		_mark_failed(statement, exc)
		raise


@frappe.whitelist()
def prepare_and_send_statement(customer, from_date, to_date, recipient_phone, message=None, source_sales_order=None):
	prepared = prepare_statement(customer, from_date, to_date, recipient_phone, message, source_sales_order)
	return send_statement(prepared["statement"])


def _ack_to_status(payload):
	ack = _get_value(payload, "ack")
	ack_name = _get_value(payload, "ackName") or _get_value(payload, "status")
	text = str(ack_name or ack or "").lower()
	if text in ("read", "played"):
		return "Read"
	if text in ("delivered", "delivery"):
		return "Delivered"
	if text in ("sent", "server", "device"):
		return "Sent"
	if text in ("error", "failed"):
		return "Failed"

	try:
		value = int(ack)
	except Exception:
		return None
	if value >= 3:
		return "Read"
	if value == 2:
		return "Delivered"
	if value >= 0:
		return "Sent"
	return "Failed"


def _timestamp_for_status(status):
	if status == "Read":
		return "read_at"
	if status == "Delivered":
		return "delivered_at"
	if status == "Replied":
		return "replied_at"
	if status == "Failed":
		return "failed_at"
	return "sent_at"


def _best_status(current_status, incoming_status):
	if not incoming_status:
		return current_status
	if incoming_status == "Failed" and current_status not in ("Delivered", "Read", "Replied"):
		return "Failed"
	if not current_status:
		return incoming_status
	current_rank = STATUS_RANK.get(current_status, 0)
	incoming_rank = STATUS_RANK.get(incoming_status, 0)
	return incoming_status if incoming_rank >= current_rank else current_status


def _status_from_waha_message(payload):
	status = _ack_to_status(payload)
	if status:
		return status

	for key in ("_data", "data", "message"):
		nested = _get_value(payload, key)
		if isinstance(nested, dict):
			status = _ack_to_status(nested)
			if status:
				return status

	if _get_value(payload, "fromMe") or _get_value(payload, "from_me"):
		return "Sent"

	return None


def _matches_waha_message_id(payload, message_id):
	if not payload or not message_id:
		return False

	extracted = extract_waha_message_id(payload)
	if extracted == message_id:
		return True

	for key in ("id", "message_id", "messageId"):
		value = _get_value(payload, key)
		if value == message_id:
			return True
		if isinstance(value, dict) and message_id in (
			value.get("_serialized"),
			value.get("id"),
			value.get("serialized"),
		):
			return True

	nested = _get_value(payload, "_data")
	return isinstance(nested, dict) and _matches_waha_message_id(nested, message_id)


def _fetch_waha_message_payload(client, session_name, chat_id, message_id):
	errors = []

	if chat_id and message_id:
		try:
			return client.chats.get_message(session_name, chat_id, message_id)
		except Exception as exc:
			errors.append(str(exc))

	if chat_id:
		try:
			for message in client.chats.get_messages(session_name, chat_id, limit=50) or []:
				if _matches_waha_message_id(message, message_id):
					return message
		except Exception as exc:
			errors.append(str(exc))

	frappe.throw(_("Could not fetch message status from WAHA: {0}").format("; ".join(errors) or _("message not found")))


def update_statement_from_ack(message_id, status, payload=None):
	if not message_id or not status:
		return None

	message_name = frappe.db.get_value("WhatsApp Message", {"message_id": message_id}, "name")
	if not message_name:
		return None

	current_message_status = frappe.db.get_value("WhatsApp Message", message_name, "send_status")
	message_status = _best_status(current_message_status, status)
	updates = {"send_status": message_status, "ack_status": status, "raw_json": _as_json(payload or {})}
	timestamp_field = _timestamp_for_status(message_status)
	if timestamp_field != "sent_at":
		updates[timestamp_field] = now()
	frappe.db.set_value("WhatsApp Message", message_name, updates)

	statement_name = frappe.db.get_value("WhatsApp Message", message_name, "whatsapp_statement_send")
	if statement_name:
		current_statement_status = frappe.db.get_value("WhatsApp Statement Send", statement_name, "status")
		statement_status = _best_status(current_statement_status, status)
		statement_updates = {"status": statement_status, "last_status_at": now(), "raw_ack_payload": _as_json(payload or {})}
		timestamp_field = _timestamp_for_status(statement_status)
		if statement_status in ("Delivered", "Read"):
			statement_updates[timestamp_field] = statement_updates["last_status_at"]
		frappe.db.set_value("WhatsApp Statement Send", statement_name, statement_updates)

	return {"message": message_name, "statement": statement_name, "status": statement_status if statement_name else message_status}


@frappe.whitelist()
def refresh_statement_status(statement_name):
	assert_whatsapp_admin()
	statement = frappe.get_doc("WhatsApp Statement Send", statement_name)
	message_id = statement.waha_message_id or (
		frappe.db.get_value("WhatsApp Message", statement.whatsapp_message, "message_id")
		if statement.whatsapp_message
		else None
	)
	if not message_id:
		frappe.throw(_("Statement {0} does not have a WAHA message id yet. Send it first.").format(statement.name))

	chat_id = statement.recipient_chat_id or (
		frappe.db.get_value("WhatsApp Message", statement.whatsapp_message, "to_chat_id")
		if statement.whatsapp_message
		else None
	)
	if not chat_id:
		frappe.throw(_("Statement {0} does not have a recipient chat id.").format(statement.name))

	connection = frappe.get_doc("WhatsApp Connection", statement.whatsapp_connection) if statement.whatsapp_connection else _get_default_connection()
	client, _base_url = _get_waha_client(connection)
	payload = _fetch_waha_message_payload(client, statement.session_name or connection.session_name, chat_id, message_id)
	status = _status_from_waha_message(payload) or statement.status or "Sent"
	result = update_statement_from_ack(message_id, status, payload)
	frappe.db.commit()
	return result or {"statement": statement.name, "message_id": message_id, "status": status}


def _parse_names(names):
	if not names:
		return []
	if isinstance(names, str):
		try:
			parsed = json.loads(names)
			if isinstance(parsed, list):
				return [name for name in parsed if name]
		except Exception:
			return [name.strip() for name in names.split(",") if name.strip()]
	if isinstance(names, (list, tuple, set)):
		return [name for name in names if name]
	return []


@frappe.whitelist()
def refresh_sent_statement_statuses(names=None, from_date=None, to_date=None, customer=None, status=None, limit=50):
	assert_whatsapp_admin()
	statement_names = _parse_names(names)

	if not statement_names:
		filters = []
		if from_date:
			filters.append(["creation", ">=", f"{_date_string(from_date)} 00:00:00"])
		if to_date:
			filters.append(["creation", "<=", f"{_date_string(to_date)} 23:59:59"])
		if customer:
			filters.append(["customer", "=", customer])
		if status:
			filters.append(["status", "=", status])
		else:
			filters.append(["status", "in", ["Sent", "Delivered"]])

		rows = frappe.get_all(
			"WhatsApp Statement Send",
			filters=filters,
			fields=["name", "waha_message_id"],
			order_by="modified desc",
			limit_page_length=cint(limit) or 50,
		)
		statement_names = [_get_value(row, "name") for row in rows if _get_value(row, "waha_message_id")]

	refreshed = []
	failed = []
	for statement_name in statement_names:
		try:
			refreshed.append(refresh_statement_status(statement_name))
		except Exception as exc:
			failed.append({"statement": statement_name, "error": str(exc)})

	return {"refreshed": refreshed, "failed": failed, "count": len(refreshed), "failed_count": len(failed)}


def handle_message_ack(event, session, payload):
	status = _ack_to_status(payload)
	message_id = extract_waha_message_id(payload)
	result = update_statement_from_ack(message_id, status, payload)
	frappe.db.commit()
	return result or {"status": "ignored", "event": event, "message_id": message_id}


def store_incoming_message_from_payload(event, session, payload):
	chat_id = _get_value(payload, "from") or _get_value(payload, "chatId")
	body = _get_value(payload, "body") or _get_value(payload, "caption") or ""
	message_id = extract_waha_message_id(payload)

	doc = frappe.new_doc("WhatsApp Message")
	doc.whatsapp_id = chat_id
	doc.message_id = message_id
	doc.message = body
	doc.session_name = session
	doc.direction = "Incoming"
	doc.timestamp = now()
	doc.raw_json = _as_json(payload)

	statement = _latest_statement_for_reply(chat_id)
	if statement:
		doc.reference_doctype = "WhatsApp Statement Send"
		doc.reference_name = statement.name
		doc.whatsapp_statement_send = statement.name

	doc.insert(ignore_permissions=True)

	if statement:
		status_at = now()
		frappe.db.set_value(
			"WhatsApp Statement Send",
			statement.name,
			{"status": "Replied", "replied_at": status_at, "last_status_at": status_at},
		)
		frappe.db.set_value(
			"WhatsApp Message",
			{"name": statement.whatsapp_message},
			{"send_status": "Replied", "replied_at": status_at},
		)

	return doc


def _latest_statement_for_reply(chat_id):
	if not chat_id:
		return None
	statements = frappe.get_all(
		"WhatsApp Statement Send",
		filters={
			"recipient_chat_id": chat_id,
			"status": ["in", ["Sent", "Delivered", "Read"]],
		},
		fields=["name", "whatsapp_message"],
		order_by="sent_at desc",
		limit_page_length=1,
	)
	return statements[0] if statements else None


def handle_incoming_message(event, session, payload):
	doc = store_incoming_message_from_payload(event, session, payload)
	frappe.db.commit()
	return {"status": "ok", "message": "Saved", "whatsapp_message": doc.name}


def _values_changed(before, after, fieldtype=None):
	if fieldtype == "Currency":
		return Decimal(str(flt(before))) != Decimal(str(flt(after)))
	return str(before or "") != str(after or "")


def refresh_statement_changes(statement_name, save=True):
	statement = frappe.get_doc("WhatsApp Statement Send", statement_name)
	changes = []
	included_orders = []

	for row in statement.get("items", []):
		if not row.sales_order:
			continue
		included_orders.append(row.sales_order)
		current = frappe.db.get_value(
			"Sales Order",
			row.sales_order,
			["docstatus", "status", "grand_total", "modified"],
			as_dict=True,
		)
		if not current:
			row.has_changed = 1
			row.change_summary = _("Sales Order missing after send")
			changes.append(f"{row.sales_order}: missing")
			continue

		row.current_status = _get_value(current, "status") or (
			"Approved / Submitted" if cint(_get_value(current, "docstatus")) == 1 else "Draft"
		)
		row.current_grand_total = flt(_get_value(current, "grand_total"))
		row.has_changed = 0
		row.change_summary = None

		row_changes = []
		if cint(row.docstatus_at_send) != cint(_get_value(current, "docstatus")):
			row_changes.append(_("document status changed"))
		if _values_changed(row.grand_total_at_send, _get_value(current, "grand_total"), "Currency"):
			row_changes.append(_("grand total changed"))
		if row.modified_at_send and _get_value(current, "modified"):
			if get_datetime(_get_value(current, "modified")) > get_datetime(row.modified_at_send):
				row_changes.append(_("modified after send"))

		if row_changes:
			row.has_changed = 1
			row.change_summary = ", ".join(row_changes)
			changes.append(f"{row.sales_order}: {row.change_summary}")

	if statement.sent_at:
		new_orders = frappe.get_all(
			"Sales Order",
			filters={
				"customer": statement.customer,
				"transaction_date": ["between", [statement.from_date, statement.to_date]],
				"docstatus": ["in", [0, 1]],
				"modified": [">", statement.sent_at],
			},
			fields=["name"],
			limit_page_length=50,
		)
		new_order_names = [_get_value(order, "name") for order in new_orders if _get_value(order, "name") not in included_orders]
		if new_order_names:
			changes.append(_("New Sales Order(s) after send: {0}").format(", ".join(new_order_names[:10])))

		try:
			payments = frappe.get_all(
				"Payment Entry",
				filters={
					"party_type": "Customer",
					"party": statement.customer,
					"docstatus": 1,
					"modified": [">", statement.sent_at],
				},
				fields=["name"],
				limit_page_length=10,
			)
			if payments:
				changes.append(_("Payment update after send: {0} payment entry(s)").format(len(payments)))
		except Exception:
			pass

	statement.has_changes_after_send = 1 if changes else 0
	statement.change_summary = "\n".join(changes[:20])
	if save:
		statement.save(ignore_permissions=True)
	return statement


@frappe.whitelist()
def refresh_statement_change_status(statement_name):
	assert_whatsapp_admin()
	statement = refresh_statement_changes(statement_name)
	frappe.db.commit()
	return {
		"statement": statement.name,
		"has_changes_after_send": cint(statement.has_changes_after_send),
		"change_summary": statement.change_summary,
	}


@frappe.whitelist()
def get_dashboard_data(from_date=None, to_date=None, customer=None, status=None):
	assert_whatsapp_admin()
	filters = []
	if from_date:
		filters.append(["creation", ">=", f"{_date_string(from_date)} 00:00:00"])
	if to_date:
		filters.append(["creation", "<=", f"{_date_string(to_date)} 23:59:59"])
	if customer:
		filters.append(["customer", "=", customer])
	if status:
		filters.append(["status", "=", status])

	rows = frappe.get_all(
		"WhatsApp Statement Send",
		filters=filters,
		fields=[
			"name",
			"customer",
			"customer_name",
			"from_date",
			"to_date",
			"recipient_phone",
			"status",
			"order_count",
			"total_amount",
			"sent_at",
			"delivered_at",
			"read_at",
			"replied_at",
			"has_changes_after_send",
			"change_summary",
			"last_error",
			"pdf_file",
			"whatsapp_message",
		],
		order_by="creation desc",
		limit_page_length=200,
	)

	normalized_rows = []
	for row in rows:
		if _get_value(row, "sent_at"):
			try:
				refreshed = refresh_statement_changes(_get_value(row, "name"), save=True)
				row.has_changes_after_send = refreshed.has_changes_after_send
				row.change_summary = refreshed.change_summary
			except Exception:
				pass
		normalized_rows.append(row)

	cards = {
		"sent": sum(1 for row in normalized_rows if _get_value(row, "status") in ("Sent", "Delivered", "Read", "Replied")),
		"delivered": sum(1 for row in normalized_rows if _get_value(row, "status") in ("Delivered", "Read", "Replied")),
		"read": sum(1 for row in normalized_rows if _get_value(row, "status") in ("Read", "Replied")),
		"replied": sum(1 for row in normalized_rows if _get_value(row, "status") == "Replied"),
		"failed": sum(1 for row in normalized_rows if _get_value(row, "status") == "Failed"),
		"changed": sum(1 for row in normalized_rows if cint(_get_value(row, "has_changes_after_send"))),
	}
	frappe.db.commit()
	return {"cards": cards, "rows": normalized_rows, "statuses": STATEMENT_STATUSES}
