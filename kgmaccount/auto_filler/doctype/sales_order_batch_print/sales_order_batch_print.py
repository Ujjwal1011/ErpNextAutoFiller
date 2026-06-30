import frappe
from frappe.utils import formatdate, getdate
from frappe.model.document import Document


class SalesOrderBatchPrint(Document):
    def validate(self):
        self.set_batch_title()
        seen = set()
        for row in self.sales_orders:
            if not row.sales_order:
                continue

            if row.sales_order in seen:
                frappe.throw(f"Sales Order {row.sales_order} is selected more than once.")

            docstatus = frappe.db.get_value("Sales Order", row.sales_order, "docstatus")
            if docstatus == 2:
                frappe.throw(f"Cancelled Sales Order {row.sales_order} cannot be included in batch print.")

            row.sales_order_status = "Approved / Submitted" if docstatus == 1 else "Draft"
            seen.add(row.sales_order)

    def set_batch_title(self):
        if not self.customer or not self.from_date or not self.to_date:
            return

        party_name = frappe.db.get_value("Customer", self.customer, "customer_name") or self.customer
        self.batch_title = f"{party_name} - {formatdate(self.from_date)} - {formatdate(self.to_date)}"


@frappe.whitelist()
def get_sales_orders(customer, from_date, to_date, include_draft=1, include_submitted=1):
    if not customer or not from_date or not to_date:
        return []

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("From Date cannot be after To Date.")

    docstatuses = []
    if frappe.utils.cint(include_draft):
        docstatuses.append(0)
    if frappe.utils.cint(include_submitted):
        docstatuses.append(1)

    if not docstatuses:
        return []

    sales_orders = frappe.get_all(
        "Sales Order",
        filters={
            "customer": customer,
            "transaction_date": ["between", [from_date, to_date]],
            "docstatus": ["in", docstatuses],
        },
        fields=["name", "customer", "transaction_date", "grand_total", "docstatus"],
        order_by="transaction_date asc, name asc",
    )

    for sales_order in sales_orders:
        sales_order.sales_order_status = "Approved / Submitted" if sales_order.docstatus == 1 else "Draft"

    return sales_orders
