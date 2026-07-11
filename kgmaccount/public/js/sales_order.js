frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		render_ai_image_viewer(frm);
		add_whatsapp_statement_button(frm);
	},

	custom_ai_cropped_image(frm) {
		render_ai_image_viewer(frm);
	},
});

function add_whatsapp_statement_button(frm) {
	if (frm.is_new() || !frm.doc.customer || frm.doc.docstatus === 2) return;

	frm.add_custom_button(
		__("Send WhatsApp Statement"),
		() => open_whatsapp_statement_dialog(frm),
		__("WhatsApp")
	);
}

function open_whatsapp_statement_dialog(frm) {
	frappe.call({
		method: "kgmaccount.whatsapp_suite.statement_sender.get_statement_preview",
		args: { sales_order: frm.doc.name },
		freeze: true,
		freeze_message: __("Preparing statement preview..."),
		callback(r) {
			const preview = r.message;
			if (!preview) return;
			show_whatsapp_statement_dialog(frm, preview);
		},
	});
}

function show_whatsapp_statement_dialog(frm, preview) {
	const recipient = preview.recipient || {};
	const dialog = new frappe.ui.Dialog({
		title: __("Send WhatsApp Statement"),
		fields: [
			{
				fieldname: "customer",
				fieldtype: "Link",
				label: __("Customer"),
				options: "Customer",
				default: preview.customer,
				read_only: 1,
			},
			{
				fieldname: "from_date",
				fieldtype: "Date",
				label: __("From Date"),
				default: preview.from_date,
				reqd: 1,
			},
			{
				fieldname: "to_date",
				fieldtype: "Date",
				label: __("To Date"),
				default: preview.to_date,
				reqd: 1,
			},
			{
				fieldname: "recipient_contact",
				fieldtype: "Link",
				label: __("Resolved Contact"),
				options: "Contact",
				default: recipient.recipient_contact,
				read_only: 1,
			},
			{
				fieldname: "recipient_source",
				fieldtype: "Data",
				label: __("Resolved From"),
				default: recipient.recipient_source,
				read_only: 1,
			},
			{
				fieldname: "recipient_phone",
				fieldtype: "Data",
				label: __("WhatsApp Number"),
				default: recipient.recipient_phone,
				reqd: 1,
			},
			{
				fieldname: "summary_html",
				fieldtype: "HTML",
			},
			{
				fieldname: "message",
				fieldtype: "Small Text",
				label: __("Caption"),
				default: preview.message,
				reqd: 1,
			},
		],
		primary_action_label: __("Send Now"),
		primary_action(values) {
			send_whatsapp_statement(frm, dialog, values);
		},
	});

	let message_touched = false;
	dialog.fields_dict.message.df.onchange = () => {
		message_touched = true;
	};

	const render = (payload) => {
		render_statement_summary(dialog, payload || preview);
	};

	const refresh_summary = frappe.utils.debounce(() => {
		const values = dialog.get_values();
		if (!values || !values.customer || !values.from_date || !values.to_date) return;

		frappe.call({
			method: "kgmaccount.whatsapp_suite.statement_sender.get_statement_summary",
			args: {
				customer: values.customer,
				from_date: values.from_date,
				to_date: values.to_date,
			},
			callback(r) {
				const summary = r.message;
				if (!summary) return;
				render(summary);
				if (!message_touched && summary.message) {
					dialog.set_value("message", summary.message);
				}
			},
		});
	}, 300);

	dialog.fields_dict.from_date.df.onchange = refresh_summary;
	dialog.fields_dict.to_date.df.onchange = refresh_summary;

	dialog.show();
	render(preview);
}

function send_whatsapp_statement(frm, dialog, values) {
	dialog.set_primary_action(__("Sending..."), null);

	frappe.call({
		method: "kgmaccount.whatsapp_suite.statement_sender.prepare_and_send_statement",
		args: {
			customer: values.customer,
			from_date: values.from_date,
			to_date: values.to_date,
			recipient_phone: values.recipient_phone,
			message: values.message,
			source_sales_order: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Sending WhatsApp statement..."),
		callback(r) {
			const result = r.message || {};
			dialog.hide();
			frappe.show_alert({
				message: __("WhatsApp statement sent"),
				indicator: "green",
			});
			if (result.statement) {
				frappe.set_route("Form", "WhatsApp Statement Send", result.statement);
			}
		},
		error() {
			dialog.set_primary_action(__("Send Now"), (retry_values) => {
				send_whatsapp_statement(frm, dialog, retry_values);
			});
		},
	});
}

function render_statement_summary(dialog, payload) {
	const orders = payload.orders || [];
	const total = format_currency(payload.total_amount || 0);
	const rows_html = orders.length
		? orders.map((row) => `
			<tr>
				<td>${escape_statement_html(row.name)}</td>
				<td>${escape_statement_html(row.transaction_date)}</td>
				<td>${escape_statement_html(row.sales_order_status || "")}</td>
				<td class="text-right">${format_currency(row.grand_total || 0)}</td>
			</tr>
		`).join("")
		: `<tr><td colspan="4" class="text-muted">${__("No Sales Orders found for this period.")}</td></tr>`;

	dialog.fields_dict.summary_html.$wrapper.html(`
		<div class="border rounded p-3 mt-2 mb-2">
			<div class="d-flex justify-content-between align-items-center mb-2">
				<strong>${__("Statement Preview")}</strong>
				<span class="text-muted">${__(`${payload.order_count || 0} Sales Order(s)`)} · ${total}</span>
			</div>
			<div style="max-height: 220px; overflow: auto;">
				<table class="table table-bordered table-sm mb-0">
					<thead>
						<tr>
							<th>${__("Sales Order")}</th>
							<th>${__("Date")}</th>
							<th>${__("Status")}</th>
							<th class="text-right">${__("Grand Total")}</th>
						</tr>
					</thead>
					<tbody>${rows_html}</tbody>
				</table>
			</div>
		</div>
	`);
}

function escape_statement_html(value) {
	if (frappe.utils && frappe.utils.escape_html) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	}
	return $("<div>").text(value == null ? "" : String(value)).html();
}

function format_currency(value) {
	if (frappe.format) {
		return frappe.format(value, { fieldtype: "Currency" });
	}
	return value;
}

function render_ai_image_viewer(frm) {
	const field = frm.get_field("custom_ai_cropped_image");
	if (!field || !field.$wrapper) return;

	field.$wrapper.find(".kgm-ai-image-viewer").remove();

	const image_url = frm.doc.custom_ai_cropped_image;
	if (!image_url) return;

	const $viewer = $("<div>", {
		class: "kgm-ai-image-viewer border rounded p-3 text-center mt-3",
	}).css({
		width: "420px",
		height: "420px",
		"max-width": "100%",
		background: "var(--subtle-fg)",
		display: "flex",
		"flex-direction": "column",
		"justify-content": "center",
	}).appendTo(field.$wrapper);

	const $link = $("<a>", {
		href: image_url,
		target: "_blank",
		rel: "noopener noreferrer",
		title: __("Open full-size image"),
	}).appendTo($viewer);

	$("<img>", {
		src: image_url,
		alt: __("Cropped WhatsApp order image"),
		class: "rounded",
	}).css({
		width: "100%",
		height: "350px",
		"object-fit": "contain",
		cursor: "zoom-in",
	}).appendTo($link);

	$("<div>", { class: "mt-2" })
		.append(
			$("<a>", {
				href: image_url,
				target: "_blank",
				rel: "noopener noreferrer",
				class: "btn btn-xs btn-default",
				text: __("Open Full Size"),
			})
		)
		.appendTo($viewer);
}
