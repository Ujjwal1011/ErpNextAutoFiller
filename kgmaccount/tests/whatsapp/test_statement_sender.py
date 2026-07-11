import types
import unittest
from unittest.mock import Mock, patch

from frappe import _dict

from kgmaccount.tests.whatsapp.whatsapp_test_utils import FakeDb, FakeDoc, NoopLogger, call_whitelisted
from kgmaccount.whatsapp_suite import statement_sender


def throw(message, *args, **kwargs):
	raise Exception(message)


class FakeMeta:
	def has_field(self, fieldname):
		return fieldname == "is_billing_contact"


class TestWhatsAppStatementSender(unittest.TestCase):
	def test_resolver_uses_customer_mobile_first(self):
		def get_value(doctype, name, fields=None, as_dict=False):
			self.assertEqual(doctype, "Customer")
			return _dict(
				name="CUST-1",
				customer_name="Alpha Traders",
				mobile_no="9876543210",
				customer_primary_contact="CONT-PRIMARY",
			)

		fake_frappe = types.SimpleNamespace(
			db=types.SimpleNamespace(get_value=get_value),
			get_all=Mock(),
			get_meta=lambda doctype: FakeMeta(),
			throw=throw,
		)

		with patch.object(statement_sender, "frappe", fake_frappe):
			recipient = statement_sender.resolve_customer_whatsapp_recipient("CUST-1")

		self.assertEqual(recipient["recipient_phone"], "919876543210")
		self.assertEqual(recipient["recipient_contact"], "CONT-PRIMARY")
		self.assertEqual(recipient["recipient_source"], "Customer Mobile No")
		fake_frappe.get_all.assert_not_called()

	def test_resolver_links_customer_mobile_to_matching_contact_phone(self):
		def get_value(doctype, name, fields=None, as_dict=False):
			self.assertEqual(doctype, "Customer")
			return _dict(
				name="CUST-1",
				customer_name="Alpha Traders",
				mobile_no="8128091559",
				customer_primary_contact=None,
			)

		def get_all(doctype, **kwargs):
			if doctype == "Dynamic Link":
				return [_dict(parent="CONT-1")]
			if doctype == "Contact":
				return [_dict(name="CONT-1", mobile_no=None, phone=None, is_primary_contact=0, is_billing_contact=0)]
			if doctype == "Contact Phone":
				return [_dict(phone="8128091559", is_primary_mobile_no=0, is_primary_phone=1)]
			raise AssertionError(f"Unexpected doctype {doctype}")

		fake_frappe = types.SimpleNamespace(
			db=types.SimpleNamespace(get_value=get_value),
			get_all=get_all,
			get_meta=lambda doctype: FakeMeta(),
			throw=throw,
		)

		with patch.object(statement_sender, "frappe", fake_frappe):
			recipient = statement_sender.resolve_customer_whatsapp_recipient("CUST-1")

		self.assertEqual(recipient["recipient_phone"], "918128091559")
		self.assertEqual(recipient["recipient_contact"], "CONT-1")
		self.assertEqual(recipient["recipient_source"], "Customer Mobile No")

	def test_resolver_falls_back_to_billing_contact(self):
		def get_value(doctype, name, fields=None, as_dict=False):
			return _dict(
				name="CUST-1",
				customer_name="Alpha Traders",
				mobile_no=None,
				customer_primary_contact="CONT-PRIMARY",
			)

		def get_all(doctype, **kwargs):
			if doctype == "Dynamic Link":
				return [_dict(parent="CONT-PRIMARY"), _dict(parent="CONT-BILLING")]
			if doctype == "Contact":
				return [
					_dict(name="CONT-PRIMARY", mobile_no=None, phone=None, is_primary_contact=1, is_billing_contact=0),
					_dict(name="CONT-BILLING", mobile_no="9000000000", phone=None, is_primary_contact=0, is_billing_contact=1),
				]
			raise AssertionError(f"Unexpected doctype {doctype}")

		fake_frappe = types.SimpleNamespace(
			db=types.SimpleNamespace(get_value=get_value),
			get_all=get_all,
			get_meta=lambda doctype: FakeMeta(),
			throw=throw,
		)

		with patch.object(statement_sender, "frappe", fake_frappe):
			recipient = statement_sender.resolve_customer_whatsapp_recipient("CUST-1")

		self.assertEqual(recipient["recipient_phone"], "919000000000")
		self.assertEqual(recipient["recipient_contact"], "CONT-BILLING")
		self.assertEqual(recipient["recipient_source"], "Billing Contact")

	def test_resolver_uses_linked_contact_primary_phone_row(self):
		def get_value(doctype, name, fields=None, as_dict=False):
			return _dict(
				name="CUST-1",
				customer_name="Alpha Traders",
				mobile_no=None,
				customer_primary_contact=None,
			)

		def get_all(doctype, **kwargs):
			if doctype == "Dynamic Link":
				return [_dict(parent="CONT-1")]
			if doctype == "Contact":
				return [_dict(name="CONT-1", mobile_no=None, phone=None, is_primary_contact=0, is_billing_contact=0)]
			if doctype == "Contact Phone":
				return [_dict(phone="8128091559", is_primary_mobile_no=0, is_primary_phone=1)]
			raise AssertionError(f"Unexpected doctype {doctype}")

		fake_frappe = types.SimpleNamespace(
			db=types.SimpleNamespace(get_value=get_value),
			get_all=get_all,
			get_meta=lambda doctype: FakeMeta(),
			throw=throw,
		)

		with patch.object(statement_sender, "frappe", fake_frappe):
			recipient = statement_sender.resolve_customer_whatsapp_recipient("CUST-1")

		self.assertEqual(recipient["recipient_phone"], "918128091559")
		self.assertEqual(recipient["recipient_contact"], "CONT-1")
		self.assertEqual(recipient["recipient_source"], "First Contact With Phone")

	def test_resolver_raises_when_customer_and_contacts_have_no_phone(self):
		def get_value(doctype, name, fields=None, as_dict=False):
			return _dict(name="CUST-1", customer_name="Alpha Traders", mobile_no=None, customer_primary_contact=None)

		def get_all(doctype, **kwargs):
			if doctype == "Dynamic Link":
				return [_dict(parent="CONT-1")]
			if doctype == "Contact":
				return [_dict(name="CONT-1", mobile_no=None, phone=None, is_primary_contact=0, is_billing_contact=0)]
			if doctype == "Contact Phone":
				return []
			raise AssertionError(f"Unexpected doctype {doctype}")

		fake_frappe = types.SimpleNamespace(
			db=types.SimpleNamespace(get_value=get_value),
			get_all=get_all,
			get_meta=lambda doctype: FakeMeta(),
			throw=throw,
		)

		with patch.object(statement_sender, "frappe", fake_frappe), patch.object(statement_sender, "_", lambda text: text):
			with self.assertRaises(Exception) as ctx:
				statement_sender.resolve_customer_whatsapp_recipient("CUST-1")

		self.assertIn("No Customer or linked Contact mobile number", str(ctx.exception))

	def test_preview_never_reads_sales_order_custom_phone_number(self):
		read_fields = []

		def get_value(doctype, name, fields=None, as_dict=False):
			if doctype == "Sales Order":
				read_fields.extend(fields)
				self.assertNotIn("custom_phone_number", fields)
				return _dict(name="SO-1", customer="CUST-1")
			if doctype == "Customer":
				if isinstance(fields, list):
					return _dict(name="CUST-1", customer_name="Alpha Traders", mobile_no="9876543210", customer_primary_contact=None)
				return "Alpha Traders"
			raise AssertionError(f"Unexpected get_value doctype {doctype}")

		fake_frappe = types.SimpleNamespace(
			db=types.SimpleNamespace(get_value=get_value),
			get_all=Mock(return_value=[]),
			get_meta=lambda doctype: FakeMeta(),
			throw=throw,
			_dict=_dict,
			format_value=lambda value, df: str(value),
		)

		with patch.object(statement_sender, "frappe", fake_frappe), patch.object(
			statement_sender,
			"get_sales_orders",
			lambda *args, **kwargs: [_dict(name="SO-1", transaction_date="2026-07-01", grand_total=100, docstatus=0, sales_order_status="Draft")],
		), patch.object(statement_sender, "_", lambda text: text
		), patch.object(statement_sender, "formatdate", lambda value: value
		):
			preview = call_whitelisted(statement_sender.get_statement_preview, sales_order="SO-1", from_date="2026-07-01", to_date="2026-07-31")

		self.assertEqual(preview["recipient"]["recipient_phone"], "919876543210")
		self.assertEqual(preview["order_count"], 1)
		self.assertIn("customer", read_fields)
		self.assertNotIn("custom_phone_number", read_fields)

	def test_send_statement_validates_number_and_uses_send_file(self):
		fake_db = FakeDb()
		fake_client = Mock()
		fake_client.sessions.get.return_value = {"name": "default"}
		fake_client.contacts.check_exists.return_value = {"numberExists": True, "chatId": "919876543210@c.us"}
		fake_client.messages.send_file.return_value = {"id": {"_serialized": "MSG-1"}}
		inserted_messages = []
		statement = FakeDoc(
			name="WA-STMT-1",
			status="Ready",
			customer="CUST-1",
			from_date="2026-07-01",
			to_date="2026-07-31",
			recipient_phone="9876543210",
			recipient_chat_id="919876543210@c.us",
			message="Statement attached",
			source_batch="SOBP-1",
			whatsapp_connection=None,
		)
		connection = FakeDoc(name="CONN-1", waha_server_ip="localhost:3000", session_name="default", api_key="secret")

		def get_doc(doctype, name=None):
			if doctype == "WhatsApp Statement Send":
				return statement
			if doctype == "WhatsApp Connection":
				return connection
			if isinstance(doctype, dict):
				return FakeDoc(file_url="/private/files/statement.pdf", insert=lambda: None)
			raise AssertionError(f"Unexpected get_doc {doctype}")

		def get_all(doctype, **kwargs):
			if doctype == "WhatsApp Connection":
				return [_dict(name="CONN-1")]
			return []

		def new_doc(doctype):
			doc = FakeDoc(doctype=doctype, name="WA-MSG-1")
			doc.insert = lambda ignore_permissions=False, doc=doc: inserted_messages.append(doc) or doc
			return doc

		fake_frappe = types.SimpleNamespace(
			db=fake_db,
			get_doc=get_doc,
			get_all=get_all,
			new_doc=new_doc,
			session=types.SimpleNamespace(user="Administrator"),
			attach_print=lambda *args, **kwargs: {"fname": "statement.pdf", "fcontent": b"%PDF"},
			throw=throw,
		)

		with patch.object(statement_sender, "frappe", fake_frappe), patch.object(
			statement_sender, "assert_whatsapp_admin", lambda: None
		), patch.object(statement_sender, "WAHAClient", return_value=fake_client), patch.object(
			statement_sender,
			"save_file",
			lambda *args, **kwargs: FakeDoc(file_url="/private/files/statement.pdf"),
		), patch.object(statement_sender, "now", lambda: "2026-07-04 10:00:00"
		):
			result = call_whitelisted(statement_sender.send_statement, "WA-STMT-1")

		self.assertEqual(result["status"], "sent")
		fake_client.contacts.check_exists.assert_called_once_with("default", "919876543210")
		call_kwargs = fake_client.messages.send_file.call_args.kwargs
		self.assertEqual(call_kwargs["chat_id"], "919876543210@c.us")
		self.assertEqual(call_kwargs["file"]["mimetype"], "application/pdf")
		self.assertEqual(call_kwargs["caption"], "Statement attached")
		self.assertEqual(inserted_messages[0].whatsapp_statement_send, "WA-STMT-1")
		self.assertEqual(statement.waha_message_id, "MSG-1")

	def test_message_ack_updates_statement_status(self):
		class AckDb(FakeDb):
			def get_value(self, doctype, filters, fieldname=None):
				if doctype == "WhatsApp Message" and filters == {"message_id": "MSG-1"}:
					return "WA-MSG-1"
				if doctype == "WhatsApp Message" and filters == "WA-MSG-1" and fieldname == "whatsapp_statement_send":
					return "WA-STMT-1"
				return None

		fake_db = AckDb()
		fake_frappe = types.SimpleNamespace(db=fake_db)

		with patch.object(statement_sender, "frappe", fake_frappe), patch.object(
			statement_sender, "now", lambda: "2026-07-04 10:00:00"
		):
			result = statement_sender.handle_message_ack(
				"message.ack",
				"default",
				{"id": {"_serialized": "MSG-1"}, "ack": 3},
			)

		self.assertEqual(result["status"], "Read")
		statement_updates = fake_db.set_values[1][0][2]
		self.assertEqual(statement_updates["status"], "Read")
		self.assertIn("read_at", statement_updates)
		self.assertEqual(fake_db.commits, 1)

	def test_message_ack_does_not_downgrade_statement_status(self):
		class AckDb(FakeDb):
			def get_value(self, doctype, filters, fieldname=None):
				if doctype == "WhatsApp Message" and filters == {"message_id": "MSG-1"}:
					return "WA-MSG-1"
				if doctype == "WhatsApp Message" and filters == "WA-MSG-1" and fieldname == "send_status":
					return "Read"
				if doctype == "WhatsApp Message" and filters == "WA-MSG-1" and fieldname == "whatsapp_statement_send":
					return "WA-STMT-1"
				if doctype == "WhatsApp Statement Send" and filters == "WA-STMT-1" and fieldname == "status":
					return "Read"
				return None

		fake_db = AckDb()
		fake_frappe = types.SimpleNamespace(db=fake_db)

		with patch.object(statement_sender, "frappe", fake_frappe), patch.object(
			statement_sender, "now", lambda: "2026-07-04 10:00:00"
		):
			result = statement_sender.update_statement_from_ack("MSG-1", "Sent", {"ack": 1})

		self.assertEqual(result["status"], "Read")
		message_updates = fake_db.set_values[0][0][2]
		statement_updates = fake_db.set_values[1][0][2]
		self.assertEqual(message_updates["send_status"], "Read")
		self.assertEqual(statement_updates["status"], "Read")

	def test_refresh_statement_status_fetches_waha_message(self):
		fake_db = FakeDb()
		statement = FakeDoc(
			name="WA-STMT-1",
			status="Sent",
			waha_message_id="MSG-1",
			whatsapp_message="WA-MSG-1",
			recipient_chat_id="919876543210@c.us",
			whatsapp_connection="CONN-1",
			session_name="default",
		)
		connection = FakeDoc(name="CONN-1", waha_server_ip="localhost:3000", session_name="default", api_key="secret")
		fake_client = Mock()
		fake_client.sessions.get.return_value = {"name": "default"}
		fake_client.chats.get_message.return_value = {"id": {"_serialized": "MSG-1"}, "ack": 2}

		def get_doc(doctype, name):
			if doctype == "WhatsApp Statement Send":
				return statement
			if doctype == "WhatsApp Connection":
				return connection
			raise AssertionError(f"Unexpected get_doc {doctype}")

		def get_value(doctype, filters, fieldname=None):
			if doctype == "WhatsApp Message" and filters == {"message_id": "MSG-1"}:
				return "WA-MSG-1"
			if doctype == "WhatsApp Message" and filters == "WA-MSG-1" and fieldname == "send_status":
				return "Sent"
			if doctype == "WhatsApp Message" and filters == "WA-MSG-1" and fieldname == "whatsapp_statement_send":
				return "WA-STMT-1"
			if doctype == "WhatsApp Statement Send" and filters == "WA-STMT-1" and fieldname == "status":
				return "Sent"
			return None

		fake_frappe = types.SimpleNamespace(db=fake_db, get_doc=get_doc, throw=throw)
		fake_db.get_value = get_value

		with patch.object(statement_sender, "frappe", fake_frappe), patch.object(
			statement_sender, "assert_whatsapp_admin", lambda: None
		), patch.object(statement_sender, "WAHAClient", return_value=fake_client), patch.object(
			statement_sender, "now", lambda: "2026-07-04 10:00:00"
		):
			result = call_whitelisted(statement_sender.refresh_statement_status, "WA-STMT-1")

		self.assertEqual(result["status"], "Delivered")
		fake_client.chats.get_message.assert_called_once_with("default", "919876543210@c.us", "MSG-1")
		statement_updates = fake_db.set_values[1][0][2]
		self.assertEqual(statement_updates["status"], "Delivered")
		self.assertIn("delivered_at", statement_updates)
		self.assertEqual(fake_db.commits, 1)

	def test_refresh_sent_statement_statuses_refreshes_recent_sent_rows(self):
		def get_all(doctype, **kwargs):
			self.assertEqual(doctype, "WhatsApp Statement Send")
			self.assertIn(["status", "in", ["Sent", "Delivered"]], kwargs["filters"])
			return [
				_dict(name="WA-STMT-1", waha_message_id="MSG-1"),
				_dict(name="WA-STMT-2", waha_message_id=None),
				_dict(name="WA-STMT-3", waha_message_id="MSG-3"),
			]

		refreshed_names = []

		def refresh_statement_status(statement_name):
			refreshed_names.append(statement_name)
			return {"statement": statement_name, "status": "Read"}

		fake_frappe = types.SimpleNamespace(get_all=get_all)

		with patch.object(statement_sender, "frappe", fake_frappe), patch.object(
			statement_sender, "assert_whatsapp_admin", lambda: None
		), patch.object(statement_sender, "refresh_statement_status", refresh_statement_status):
			result = call_whitelisted(statement_sender.refresh_sent_statement_statuses)

		self.assertEqual(refreshed_names, ["WA-STMT-1", "WA-STMT-3"])
		self.assertEqual(result["count"], 2)
		self.assertEqual(result["failed_count"], 0)

	def test_refresh_statement_changes_flags_modified_sales_order(self):
		row = FakeDoc(
			sales_order="SO-1",
			docstatus_at_send=0,
			grand_total_at_send=100,
			modified_at_send="2026-07-01 10:00:00",
		)
		statement = FakeDoc(
			name="WA-STMT-1",
			customer="CUST-1",
			from_date="2026-07-01",
			to_date="2026-07-31",
			sent_at="2026-07-01 11:00:00",
			items=[row],
		)
		statement.get = lambda key, default=None: getattr(statement, key, default)

		def get_doc(doctype, name):
			self.assertEqual(doctype, "WhatsApp Statement Send")
			return statement

		def get_value(doctype, name, fields=None, as_dict=False):
			if doctype == "Sales Order":
				return _dict(docstatus=1, status="To Deliver", grand_total=125, modified="2026-07-01 12:00:00")
			return None

		def get_all(doctype, **kwargs):
			return []

		fake_frappe = types.SimpleNamespace(
			db=types.SimpleNamespace(get_value=get_value),
			get_doc=get_doc,
			get_all=get_all,
		)

		with patch.object(statement_sender, "frappe", fake_frappe), patch.object(statement_sender, "_", lambda text: text):
			refreshed = statement_sender.refresh_statement_changes("WA-STMT-1", save=False)

		self.assertEqual(refreshed.has_changes_after_send, 1)
		self.assertEqual(row.has_changed, 1)
		self.assertIn("grand total changed", row.change_summary)


if __name__ == "__main__":
	unittest.main()
