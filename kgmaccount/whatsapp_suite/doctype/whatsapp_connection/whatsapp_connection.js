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
						if (success) {
							frappe.msgprint({
								title: __("Session Started"),
								indicator: "green",
								message: message.message || __("WAHA session started."),
							});
							return;
						}

						startSessionFromBrowser(frm, message.message);
					},
				});
			}, __("Actions"));
		});
	},
});

function getWahaBrowserUrls(frm) {
	const value = String(frm.doc.waha_server_ip || "").trim();
	if (!value) return [];

	let parsed;
	try {
		parsed = new URL(value.includes("://") ? value : `http://${value}`);
	} catch (e) {
		return [];
	}

	const port = parsed.port ? `:${parsed.port}` : "";
	const path = parsed.pathname && parsed.pathname !== "/" ? parsed.pathname.replace(/\/$/, "") : "";
	const hosts = [parsed.hostname, "localhost", "127.0.0.1"];
	return [...new Set(hosts.filter(Boolean).map(host => `http://${host}${port}${path}`))];
}

async function startSessionFromBrowser(frm, backendMessage) {
	const sessionName = frm.doc.session_name || "default";
	const urls = getWahaBrowserUrls(frm);
	const headers = {
		"Content-Type": "application/json",
		"Accept": "application/json",
	};
	if (frm.doc.api_key && !String(frm.doc.api_key).includes("*")) {
		headers["X-Api-Key"] = frm.doc.api_key;
	}

	for (const baseUrl of urls) {
		try {
			let response = await fetch(`${baseUrl}/api/sessions/${encodeURIComponent(sessionName)}/start`, {
				method: "POST",
				headers,
			});

			if (response.status === 404) {
				response = await fetch(`${baseUrl}/api/sessions`, {
					method: "POST",
					headers,
					body: JSON.stringify({ name: sessionName }),
				});
			}

			if (response.ok) {
				frappe.msgprint({
					title: __("Session Started"),
					indicator: "green",
					message: __("WAHA session {0} started using {1}.", [sessionName, baseUrl]),
				});
				return;
			}
		} catch (e) {
			// Try the next candidate URL.
		}
	}

	frappe.msgprint({
		title: __("Session Start Failed"),
		indicator: "red",
		message: backendMessage || __("Could not reach WAHA from the server or browser."),
	});
}
