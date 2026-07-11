import frappe
from frappe.model.document import Document


class WhatsAppStatementSend(Document):
	def validate(self):
		if self.customer and not self.customer_name:
			self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name") or self.customer

