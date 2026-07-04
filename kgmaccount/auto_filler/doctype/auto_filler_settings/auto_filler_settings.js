// Copyright (c) 2026, Ujjwal  and contributors
// For license information, please see license.txt

frappe.ui.form.on("Auto Filler Settings", {
	refresh(frm) {
		frm.trigger("set_intro");
		frm.trigger("add_default_button");
	},

	set_intro(frm) {
		frm.set_intro(
			__(
				"Settings here apply only to Sales Order, Quotation, and Sales Invoice item automation."
			),
			"blue"
		);
	},

	add_default_button(frm) {
		frm.add_custom_button(__("Load Missing Defaults"), () => {
			frappe.call({
				method:
					"kgmaccount.auto_filler.doctype.auto_filler_settings.auto_filler_settings.load_missing_defaults",
				freeze: true,
				freeze_message: __("Loading default values..."),
				callback(r) {
					const message =
						(r.message && r.message.message) ||
						__("Default values checked.");

					frappe.show_alert({
						message: __(message),
						indicator: r.message && r.message.updated ? "green" : "blue",
					});

					frm.reload_doc();
				},
			});
		});
	},
});
