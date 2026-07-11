frappe.pages["whatsapp-statement-dashboard"].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("WhatsApp Statement Dashboard"),
		single_column: true,
	});

	const state = {
		from_date: frappe.datetime.month_start(),
		to_date: frappe.datetime.get_today(),
		customer: null,
		status: null,
	};

	const $main = $(wrapper).find(".layout-main-section");
	$main.html(`
		<style>
			.wa-statement-filters { display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 12px; margin-bottom: 14px; }
			.wa-statement-cards { display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 10px; margin-bottom: 14px; }
			.wa-statement-card { border: 1px solid #dfe5eb; border-radius: 8px; padding: 12px; background: #ffffff; min-height: 76px; }
			.wa-statement-card .label { color: #64748b; font-size: 12px; font-weight: 700; }
			.wa-statement-card .value { color: #1f2933; font-size: 24px; font-weight: 800; margin-top: 4px; }
			.wa-statement-table-wrap { border: 1px solid #dfe5eb; border-radius: 8px; overflow: auto; background: #ffffff; }
			.wa-statement-table { width: 100%; margin: 0; }
			.wa-statement-table th { white-space: nowrap; background: #f8fafc; }
			.wa-statement-table td { vertical-align: top; }
			.wa-status { display: inline-flex; align-items: center; min-height: 22px; padding: 3px 8px; border-radius: 999px; background: #eef2f7; color: #334155; font-size: 11px; font-weight: 700; }
			.wa-status.Failed { background: #fee2e2; color: #991b1b; }
			.wa-status.Read, .wa-status.Replied { background: #dcfce7; color: #166534; }
			.wa-status.Delivered, .wa-status.Sent { background: #dbeafe; color: #1e40af; }
			.wa-change { color: #92400e; font-weight: 700; }
			.wa-error { color: #991b1b; max-width: 260px; overflow-wrap: anywhere; }
			@media (max-width: 1000px) {
				.wa-statement-filters { grid-template-columns: repeat(2, minmax(160px, 1fr)); }
				.wa-statement-cards { grid-template-columns: repeat(3, minmax(120px, 1fr)); }
			}
			@media (max-width: 640px) {
				.wa-statement-filters, .wa-statement-cards { grid-template-columns: 1fr; }
			}
		</style>
		<div class="wa-statement-filters" id="wa-statement-filters"></div>
		<div class="wa-statement-cards" id="wa-statement-cards"></div>
		<div class="wa-statement-table-wrap">
			<table class="table table-bordered wa-statement-table">
				<thead>
					<tr>
						<th>${__("Statement")}</th>
						<th>${__("Customer")}</th>
						<th>${__("Period")}</th>
						<th>${__("Recipient")}</th>
						<th>${__("Status")}</th>
						<th>${__("Sent")}</th>
						<th>${__("Read")}</th>
						<th>${__("Reply")}</th>
						<th>${__("Change")}</th>
						<th>${__("PDF")}</th>
					</tr>
				</thead>
				<tbody id="wa-statement-rows">
					<tr><td colspan="10" class="text-muted">${__("Loading...")}</td></tr>
				</tbody>
			</table>
		</div>
	`);

	page.add_inner_button(__("Refresh"), load_dashboard);
	page.add_inner_button(__("Refresh Sent Statuses"), refresh_sent_statuses);
	make_filters();
	load_dashboard();

	function make_filters() {
		const $filters = $("#wa-statement-filters");
		const from = frappe.ui.form.make_control({
			parent: $filters,
			df: { fieldtype: "Date", label: __("From Date"), fieldname: "from_date" },
			render_input: true,
		});
		from.set_value(state.from_date);
		from.$input.on("change", () => {
			state.from_date = from.get_value();
			load_dashboard();
		});

		const to = frappe.ui.form.make_control({
			parent: $filters,
			df: { fieldtype: "Date", label: __("To Date"), fieldname: "to_date" },
			render_input: true,
		});
		to.set_value(state.to_date);
		to.$input.on("change", () => {
			state.to_date = to.get_value();
			load_dashboard();
		});

		const customer = frappe.ui.form.make_control({
			parent: $filters,
			df: { fieldtype: "Link", label: __("Customer"), fieldname: "customer", options: "Customer" },
			render_input: true,
		});
		customer.$input.on("change", () => {
			state.customer = customer.get_value();
			load_dashboard();
		});

		const status = frappe.ui.form.make_control({
			parent: $filters,
			df: {
				fieldtype: "Select",
				label: __("Status"),
				fieldname: "status",
				options: "\nDraft\nReady\nSending\nSent\nDelivered\nRead\nReplied\nFailed",
			},
			render_input: true,
		});
		status.$input.on("change", () => {
			state.status = status.get_value();
			load_dashboard();
		});
	}

	function load_dashboard() {
		frappe.call({
			method: "kgmaccount.whatsapp_suite.statement_sender.get_dashboard_data",
			args: {
				from_date: state.from_date,
				to_date: state.to_date,
				customer: state.customer,
				status: state.status,
			},
			callback(r) {
				const payload = r.message || {};
				render_cards(payload.cards || {});
				render_rows(payload.rows || []);
			},
		});
	}

	function refresh_sent_statuses() {
		frappe.call({
			method: "kgmaccount.whatsapp_suite.statement_sender.refresh_sent_statement_statuses",
			args: {
				from_date: state.from_date,
				to_date: state.to_date,
				customer: state.customer,
				status: state.status,
			},
			freeze: true,
			freeze_message: __("Refreshing sent WhatsApp statuses..."),
			callback(r) {
				const result = r.message || {};
				frappe.show_alert({
					message: __("{0} refreshed, {1} failed", [result.count || 0, result.failed_count || 0]),
					indicator: result.failed_count ? "orange" : "green",
				});
				load_dashboard();
			},
		});
	}

	function render_cards(cards) {
		const card_defs = [
			["sent", __("Sent")],
			["delivered", __("Delivered")],
			["read", __("Read")],
			["replied", __("Replied")],
			["failed", __("Failed")],
			["changed", __("Changed")],
		];
		$("#wa-statement-cards").html(card_defs.map(([key, label]) => `
			<div class="wa-statement-card">
				<div class="label">${label}</div>
				<div class="value">${cards[key] || 0}</div>
			</div>
		`).join(""));
	}

	function render_rows(rows) {
		if (!rows.length) {
			$("#wa-statement-rows").html(`<tr><td colspan="10" class="text-muted">${__("No statements found.")}</td></tr>`);
			return;
		}

		$("#wa-statement-rows").html(rows.map((row) => `
			<tr>
				<td>${link_to_form("WhatsApp Statement Send", row.name, row.name)}</td>
				<td>${escape_html(row.customer_name || row.customer || "")}</td>
				<td>${escape_html(row.from_date || "")} - ${escape_html(row.to_date || "")}</td>
				<td>${escape_html(row.recipient_phone || "")}</td>
				<td><span class="wa-status ${escape_html(row.status || "")}">${escape_html(row.status || "")}</span>${row.last_error ? `<div class="wa-error">${escape_html(row.last_error)}</div>` : ""}</td>
				<td>${format_datetime(row.sent_at)}</td>
				<td>${format_datetime(row.read_at)}</td>
				<td>${format_datetime(row.replied_at)}</td>
				<td>${row.has_changes_after_send ? `<span class="wa-change">${__("Changed")}</span><div class="text-muted">${escape_html(row.change_summary || "")}</div>` : ""}</td>
				<td>${row.pdf_file ? `<a href="${escape_html(row.pdf_file)}" target="_blank">${__("Open")}</a>` : ""}</td>
			</tr>
		`).join(""));
	}

	function link_to_form(doctype, name, label) {
		const route = frappe.router.slug(doctype);
		return `<a href="/app/${route}/${encodeURIComponent(name)}">${escape_html(label || name)}</a>`;
	}

	function format_datetime(value) {
		return value ? moment(value).format("MMM D, HH:mm") : "";
	}

	function escape_html(value) {
		if (frappe.utils && frappe.utils.escape_html) {
			return frappe.utils.escape_html(value == null ? "" : String(value));
		}
		return $("<div>").text(value == null ? "" : String(value)).html();
	}
};
