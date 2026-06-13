import frappe
from frappe.utils import getdate
from frappe.model.document import Document


class SalesOrderBatchPrint(Document):
    def validate(self):
        seen = set()
        for row in self.sales_orders:
            if not row.sales_order:
                continue

            if row.sales_order in seen:
                frappe.throw(f"Sales Order {row.sales_order} is selected more than once.")

            seen.add(row.sales_order)


@frappe.whitelist()
def get_sales_orders(customer, from_date, to_date):
    if not customer or not from_date or not to_date:
        return []

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("From Date cannot be after To Date.")

    return frappe.get_all(
        "Sales Order",
        filters={
            "customer": customer,
            "transaction_date": ["between", [from_date, to_date]],
            "docstatus": ["!=", 2],
        },
        fields=["name", "customer", "transaction_date", "grand_total"],
        order_by="transaction_date asc, name asc",
    )
