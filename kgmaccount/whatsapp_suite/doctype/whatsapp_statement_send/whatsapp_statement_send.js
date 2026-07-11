frappe.ui.form.on("WhatsApp Statement Send", {
	refresh(frm) {
		if (can_offer_send_statement(frm)) {
			frm.add_custom_button(__("Send WhatsApp"), () => send_whatsapp_statement(frm), __("Actions"));
			frm.add_custom_button(__("Send WhatsApp"), () => send_whatsapp_statement(frm)).addClass("btn-primary");
		}

		if (can_refresh_whatsapp_status(frm)) {
			frm.add_custom_button(__("Refresh WhatsApp Status"), () => refresh_whatsapp_status(frm), __("Actions"));
		}

		if (can_fetch_statement_orders(frm)) {
			frm.add_custom_button(__("Fetch Sales Orders"), () => fetch_statement_orders(frm), __("Actions"));
		}
	},

	customer(frm) {
		queue_fetch_statement_orders(frm);
	},

	from_date(frm) {
		queue_fetch_statement_orders(frm);
	},

	to_date(frm) {
		queue_fetch_statement_orders(frm);
	},
});

const queue_fetch_statement_orders = frappe.utils.debounce((frm) => {
	if (can_fetch_statement_orders(frm)) {
		fetch_statement_orders(frm, true);
	}
}, 350);

function can_fetch_statement_orders(frm) {
	return Boolean(
		frm.doc.customer
		&& frm.doc.from_date
		&& frm.doc.to_date
		&& ["Draft", "Ready", undefined, null, ""].includes(frm.doc.status)
	);
}

function can_offer_send_statement(frm) {
	return Boolean(
		!frm.is_new()
		&& ["Ready", "Draft", "Failed"].includes(frm.doc.status)
		&& frm.doc.customer
		&& frm.doc.from_date
		&& frm.doc.to_date
	);
}

function can_refresh_whatsapp_status(frm) {
	return Boolean(
		!frm.is_new()
		&& frm.doc.waha_message_id
		&& ["Sent", "Delivered", "Read", "Replied", "Failed"].includes(frm.doc.status)
	);
}

function refresh_whatsapp_status(frm) {
	frappe.call({
		method: "kgmaccount.whatsapp_suite.statement_sender.refresh_statement_status",
		args: {
			statement_name: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Refreshing WhatsApp status..."),
		callback(r) {
			const result = r.message || {};
			frappe.show_alert({
				message: __("WhatsApp status: {0}", [result.status || __("Updated")]),
				indicator: "green",
			});
			frm.reload_doc();
		},
	});
}

function send_whatsapp_statement(frm) {
	if (!frm.doc.items || !frm.doc.items.length) {
		frappe.msgprint({
			title: __("Fetch Sales Orders"),
			indicator: "orange",
			message: __("Fetch Sales Orders before sending this WhatsApp statement."),
		});
		return;
	}
	if (!frm.doc.recipient_phone) {
		frappe.msgprint({
			title: __("Recipient Required"),
			indicator: "orange",
			message: __("Set the recipient phone before sending this WhatsApp statement."),
		});
		return;
	}

	const run_send = () => {
		frappe.confirm(
			__("Send this statement to {0} on WhatsApp?", [frm.doc.recipient_phone]),
			() => {
				frappe.call({
					method: "kgmaccount.whatsapp_suite.statement_sender.send_statement",
					args: {
						statement_name: frm.doc.name,
					},
					freeze: true,
					freeze_message: __("Sending WhatsApp statement..."),
					callback(r) {
						const result = r.message || {};
						frappe.show_alert({
							message: result.message_id
								? __("WhatsApp statement sent")
								: __("WhatsApp statement queued"),
							indicator: "green",
						});
						frm.reload_doc();
					},
				});
			}
		);
	};

	if (frm.is_dirty()) {
		frm.save().then(run_send);
	} else {
		run_send();
	}
}

function fetch_statement_orders(frm, silent) {
	frappe.call({
		method: "kgmaccount.whatsapp_suite.statement_sender.get_statement_form_data",
		args: {
			customer: frm.doc.customer,
			from_date: frm.doc.from_date,
			to_date: frm.doc.to_date,
		},
		freeze: !silent,
		freeze_message: __("Fetching Sales Orders..."),
		callback(r) {
			const payload = r.message;
			if (!payload) return;

			apply_statement_form_data(frm, payload);
			if (payload.recipient_error) {
				frappe.show_alert({
					message: payload.recipient_error,
					indicator: "orange",
				});
			}
			if (!silent) {
				frappe.show_alert({
					message: __("{0} Sales Order(s) fetched", [payload.order_count || 0]),
					indicator: payload.order_count ? "green" : "orange",
				});
			}
		},
	});
}

function apply_statement_form_data(frm, payload) {
	const orders = payload.orders || [];
	const recipient = payload.recipient || {};

	frm.set_value("customer_name", payload.customer_name || frm.doc.customer);
	frm.set_value("order_count", payload.order_count || 0);
	frm.set_value("total_amount", payload.total_amount || 0);

	if (recipient.recipient_contact && !frm.doc.recipient_contact) {
		frm.set_value("recipient_contact", recipient.recipient_contact || "");
	}

	if (recipient.recipient_phone && should_replace_auto_value(frm.doc.recipient_phone, frm.__auto_recipient_phone)) {
		frm.set_value("recipient_phone", recipient.recipient_phone || "");
		frm.set_value("recipient_chat_id", recipient.recipient_chat_id || "");
		frm.__auto_recipient_phone = recipient.recipient_phone || "";
	}

	if (payload.message && should_replace_auto_value(frm.doc.message, frm.__auto_message)) {
		frm.set_value("message", payload.message || "");
		frm.__auto_message = payload.message || "";
	}

	frm.clear_table("items");
	orders.forEach((order) => {
		const row = frm.add_child("items");
		row.sales_order = order.name;
		row.transaction_date = order.transaction_date;
		row.docstatus_at_send = order.docstatus;
		row.sales_order_status = order.sales_order_status;
		row.grand_total_at_send = order.grand_total;
		row.modified_at_send = order.modified;
	});
	frm.refresh_field("items");

	if (orders.length && frm.doc.recipient_phone && frm.doc.status === "Draft") {
		frm.set_value("status", "Ready");
	}
}

function should_replace_auto_value(current_value, previous_auto_value) {
	return !current_value || current_value === previous_auto_value;
}
