frappe.ui.form.on("Sales Order Batch Print", {
	refresh(frm) {
		frm.add_custom_button(__("Print Batch"), () => print_batch(frm)).addClass("btn-primary");
		frm.add_custom_button(__("Print Batch with Status"), () => print_batch(frm, {
			print_format: "Sales Order Batch Printing With Status",
		}));
		update_batch_title(frm);
	},

	customer(frm) {
		update_batch_title(frm);
		fetch_sales_orders(frm, { freeze: false });
	},

	from_date(frm) {
		update_batch_title(frm);
		fetch_sales_orders(frm, { freeze: false });
	},

	to_date(frm) {
		update_batch_title(frm);
		fetch_sales_orders(frm, { freeze: false });
	},

	include_draft(frm) {
		fetch_sales_orders(frm, { freeze: false });
	},

	include_submitted(frm) {
		fetch_sales_orders(frm, { freeze: false });
	},
});

function update_batch_title(frm) {
	if (!frm.doc.customer || !frm.doc.from_date || !frm.doc.to_date) {
		return Promise.resolve();
	}

	return get_party_name(frm).then((party_name) => {
		const from_date = frappe.datetime.str_to_user(frm.doc.from_date);
		const to_date = frappe.datetime.str_to_user(frm.doc.to_date);
		const batch_title = [party_name, from_date, to_date].join(" - ");

		if (frm.doc.batch_title !== batch_title) {
			return frm.set_value("batch_title", batch_title);
		}
	});
}

function get_party_name(frm) {
	const customer = frm.doc.customer;

	if (frm._batch_title_customer === customer && frm._batch_title_party_name) {
		return Promise.resolve(frm._batch_title_party_name);
	}

	return frappe.db.get_value("Customer", customer, "customer_name").then((r) => {
		const party_name = (r.message && r.message.customer_name) || customer;

		if (frm.doc.customer === customer) {
			frm._batch_title_customer = customer;
			frm._batch_title_party_name = party_name;
		}

		return party_name;
	});
}

function fetch_sales_orders(frm, opts = {}) {
	if (!frm.doc.customer || !frm.doc.from_date || !frm.doc.to_date) {
		return Promise.resolve([]);
	}

	const include_draft = frm.doc.include_draft !== 0;
	const include_submitted = frm.doc.include_submitted !== 0;

	return frappe.call({
		method: "kgmaccount.auto_filler.doctype.sales_order_batch_print.sales_order_batch_print.get_sales_orders",
		args: {
			customer: frm.doc.customer,
			from_date: frm.doc.from_date,
			to_date: frm.doc.to_date,
			include_draft: include_draft ? 1 : 0,
			include_submitted: include_submitted ? 1 : 0,
		},
		freeze: opts.freeze !== false,
		freeze_message: __("Fetching Sales Orders"),
		callback(r) {
			const sales_orders = r.message || [];

			frm.clear_table("sales_orders");
			sales_orders.forEach((sales_order) => {
				const row = frm.add_child("sales_orders");
				row.sales_order = sales_order.name;
				row.sales_order_status = sales_order.sales_order_status;
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

function print_batch(frm, opts = {}) {
	if (!frm.doc.customer || !frm.doc.from_date || !frm.doc.to_date) {
		frappe.msgprint(__("Select Party Name, From Date, and To Date."));
		return;
	}

	if (frm.doc.include_draft === 0 && frm.doc.include_submitted === 0) {
		frappe.msgprint(__("Select Draft, Approved / Submitted, or both."));
		return;
	}

	update_batch_title(frm).then(() => fetch_sales_orders(frm, { freeze: true })).then(() => {
		if (!frm.doc.sales_orders || !frm.doc.sales_orders.length) {
			frappe.msgprint(__("No Sales Orders found for the selected filters."));
			return;
		}

		const save_batch = frm.is_new() || frm.is_dirty()
			? frm.save()
			: Promise.resolve();

		save_batch.then(() => open_batch_print(frm, opts.print_format));
	});
}

function open_batch_print(frm, print_format) {
	frappe.route_options = {
		print_format: print_format || "Sales Order Batch Printing",
	};
	frappe.set_route("print", frm.doctype, frm.doc.name);
}
