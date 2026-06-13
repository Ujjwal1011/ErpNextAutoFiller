frappe.ui.form.on("Sales Order Batch Print", {
	customer(frm) {
		fetch_sales_orders(frm);
	},

	from_date(frm) {
		fetch_sales_orders(frm);
	},

	to_date(frm) {
		fetch_sales_orders(frm);
	},
});

function fetch_sales_orders(frm) {
	if (!frm.doc.customer || !frm.doc.from_date || !frm.doc.to_date) {
		return;
	}

	frappe.call({
		method: "kgmaccount.auto_filler.doctype.sales_order_batch_print.sales_order_batch_print.get_sales_orders",
		args: {
			customer: frm.doc.customer,
			from_date: frm.doc.from_date,
			to_date: frm.doc.to_date,
		},
		freeze: true,
		freeze_message: __("Fetching Sales Orders"),
		callback(r) {
			const sales_orders = r.message || [];

			frm.clear_table("sales_orders");
			sales_orders.forEach((sales_order) => {
				const row = frm.add_child("sales_orders");
				row.sales_order = sales_order.name;
				row.customer = sales_order.customer;
				row.transaction_date = sales_order.transaction_date;
				row.grand_total = sales_order.grand_total;
			});

			frm.refresh_field("sales_orders");

			if (!sales_orders.length) {
				frappe.show_alert({
					message: __("No Sales Orders found for the selected filters."),
					indicator: "orange",
				});
			}
		},
	});
}
