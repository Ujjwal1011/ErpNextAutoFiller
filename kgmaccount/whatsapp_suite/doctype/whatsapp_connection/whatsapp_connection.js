// Copyright (c) 2026, Ujjwal  and contributors
// For license information, please see license.txt

frappe.ui.form.on("WhatsApp Connection", {
	refresh(frm) {
		if (!frm.doc.waha_server_ip) return;

		setTimeout(() => {
			const actionButtons = frm.custom_buttons && frm.custom_buttons[__("Actions")];
			if (actionButtons && actionButtons[__("Start Default Session")]) return;

			frm.add_custom_button(__("Start Default Session"), function() {
				frappe.call({
					method: "kgmaccount.whatsapp_suite.doctype.whatsapp_connection.whatsapp_connection.start_default_session",
					args: {
						docname: frm.doc.name,
					},
					freeze: true,
					freeze_message: __("Starting WAHA session..."),
					callback: function(r) {
						const message = r.message || {};
						const success = message.status === "success";
						frappe.msgprint({
							title: success ? __("Session Started") : __("Session Start Failed"),
							indicator: success ? "green" : "red",
							message: message.message || __("No response from WAHA."),
						});
					},
				});
			}, __("Actions"));
		});
	},
});
