frappe.listview_settings["WhatsApp Statement Send"] = {
	onload(listview) {
		add_status_refresh_button(listview);

		listview.page.add_action_item(__("Refresh WhatsApp Status"), () => {
			const selected = listview.get_checked_items();
			if (!selected.length) {
				frappe.msgprint(__("Select one or more WhatsApp Statement Send records."));
				return;
			}

			refresh_selected_statement_statuses(listview, selected.map((row) => row.name));
		});
	},

	refresh(listview) {
		add_status_refresh_button(listview);
	},
};

function add_status_refresh_button(listview) {
	if (listview.__wa_status_refresh_button_added) {
		return;
	}

	listview.__wa_status_refresh_button_added = true;
	listview.page.add_inner_button(__("Refresh Sent Statuses"), () => {
		refresh_sent_statement_statuses(listview);
	});
}

function refresh_sent_statement_statuses(listview) {
	frappe.call({
		method: "kgmaccount.whatsapp_suite.statement_sender.refresh_sent_statement_statuses",
		freeze: true,
		freeze_message: __("Refreshing sent WhatsApp statuses..."),
		callback(r) {
			const result = r.message || {};
			frappe.show_alert({
				message: __("{0} refreshed, {1} failed", [result.count || 0, result.failed_count || 0]),
				indicator: result.failed_count ? "orange" : "green",
			});
			listview.refresh();
		},
	});
}

function refresh_selected_statement_statuses(listview, statement_names) {
	let refreshed = 0;
	const failures = [];

	frappe.dom.freeze(__("Refreshing WhatsApp statuses..."));

	const refresh_next = () => {
		const statement_name = statement_names.shift();
		if (!statement_name) {
			frappe.dom.unfreeze();
			listview.refresh();

			if (failures.length) {
				frappe.msgprint({
					title: __("Status Refresh Completed"),
					indicator: "orange",
					message: __("{0} refreshed. {1} failed.", [refreshed, failures.length]),
				});
			} else {
				frappe.show_alert({
					message: __("{0} WhatsApp status(es) refreshed", [refreshed]),
					indicator: "green",
				});
			}
			return;
		}

		frappe.call({
			method: "kgmaccount.whatsapp_suite.statement_sender.refresh_statement_status",
			args: {
				statement_name,
			},
			callback() {
				refreshed += 1;
			},
			error() {
				failures.push(statement_name);
			},
			always: refresh_next,
		});
	};

	refresh_next();
}
