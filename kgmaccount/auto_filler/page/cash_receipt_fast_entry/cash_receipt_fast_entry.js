frappe.pages["cash-receipt-fast-entry"].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Cash Receipt Fast Entry"),
		single_column: true,
	});
	const method = "kgmaccount.auto_filler.page.cash_receipt_fast_entry.cash_receipt_fast_entry.";
	const $main = $(wrapper).find(".layout-main-section");
	const state = { accountType: "", receiptAccountType: "", invoices: [], invoiceRequest: 0, customerRequest: 0, customerAutoAccount: false, settingAccountFromCustomer: false, saving: false, loadingDefaults: true };
	const controls = {};
	const routes = [
		{ key: "F6", route: "cash-receipt-fast-entry", label: __("Receipt") },
		{ key: "F5", route: "payment-fast-entry", label: __("Payment") },
	];

	$main.html(`
		<style>
			.kgm-receipt { max-width: 1180px; margin: 0 auto; background: #fff; border: 1px solid #dce3e9; border-radius: 8px; overflow: hidden; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
			.kgm-receipt-head { grid-column: 1 / -1; padding: 8px 14px; background: #eaf5f1; border-bottom: 1px solid #cce3da; }
			.kgm-receipt-head h2 { margin: 0 0 2px; font-size: 18px; }
			.kgm-receipt-head p { margin: 0; color: #52665e; }
			.kgm-receipt-switch { grid-column: 1 / -1; display: flex; gap: 6px; flex-wrap: wrap; padding: 6px 14px; background: #f8fafc; border-bottom: 1px solid #e8edf1; }
			.kgm-receipt-switch a { padding: 3px 7px; border: 1px solid #dce3e9; border-radius: 5px; color: #52616f; font-size: 12px; text-decoration: none; }
			.kgm-receipt-switch a.active { background: #eaf5f1; border-color: #94c7b4; color: #143f30; font-weight: 700; }
			.kgm-receipt-key { color: #7a8795; margin-left: 4px; }
			.kgm-receipt-section { padding: 8px 14px; border-bottom: 1px solid #e8edf1; }
			.kgm-receipt-grid { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px 12px; }
			.kgm-receipt-grid .frappe-control { margin-bottom: 0; }
			.kgm-receipt-label { display: block; font-size: 12px; font-weight: 700; color: #52616f; margin-bottom: 3px; }
			.kgm-receipt-input { width: 100%; min-height: 36px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 7px 9px; background: #fff; }
			.kgm-receipt-input:focus { outline: 2px solid #b7ded0; outline-offset: 1px; }
			.kgm-receipt-preview { display: flex; justify-content: space-between; gap: 10px; background: #f8fafc; border: 1px solid #dce3e9; border-radius: 6px; padding: 8px; }
			.kgm-receipt-preview strong { display: block; color: #143f30; font-size: 15px; }
			.kgm-receipt-help { color: #64748b; font-size: 12px; margin: 4px 0 0; }
			.kgm-receipt-selection-help { grid-column: 1 / -1; }
			#kgm-receipt-invoice-section, .kgm-receipt-actions { grid-column: 1 / -1; }
			#kgm-receipt-invoice-section h4 { margin: 0; font-size: 15px; line-height: 20px; }
			#kgm-receipt-invoice-section .kgm-receipt-help { margin: 2px 0 4px; }
			#kgm-receipt-narration-section { grid-column: 1; border-right: 1px solid #e8edf1; }
			#kgm-receipt-preview-section { grid-column: 2; }
			#kgm-receipt-narration { min-height: 54px; }
			.kgm-receipt-invoice-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px 10px; }
			.kgm-receipt-invoice-row { display: grid; grid-template-columns: minmax(0, 1fr) auto 100px; gap: 7px; align-items: center; min-width: 0; padding: 4px 7px; border: 1px solid #dce3e9; border-radius: 6px; }
			.kgm-receipt-invoice-name { min-width: 0; font-size: 12px; line-height: 1.25; }
			.kgm-receipt-invoice-name strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.kgm-receipt-invoice-name small { display: block; color: #64748b; }
			.kgm-receipt-invoice-outstanding { white-space: nowrap; font-size: 12px; text-align: right; }
			.kgm-receipt-invoice-row input { min-height: 28px; padding: 3px 5px; text-align: right; }
			.kgm-receipt-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
			.kgm-receipt-status { color: #64748b; font-size: 12px; }
			@media (max-width: 760px) { .kgm-receipt { grid-template-columns: 1fr; } .kgm-receipt-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .kgm-receipt-invoice-list { grid-template-columns: 1fr; } #kgm-receipt-narration-section, #kgm-receipt-preview-section { grid-column: 1 / -1; border-right: 0; } }
			@media (max-width: 520px) { .kgm-receipt-grid { grid-template-columns: 1fr; } }
		</style>
		<div class="kgm-receipt">
			<div class="kgm-receipt-head">
				<h2>${__("Cash Receipt")}</h2>
				<p>${__("Choose a customer or posting ledger, then enter the amount received. Bank receipts get an internal AUTO-REC reference.")}</p>
			</div>
			<nav class="kgm-receipt-switch" aria-label="${__("Accounting fast-entry pages")}">${routes.map(item => `<a href="/app/${item.route}" class="${item.route === "cash-receipt-fast-entry" ? "active" : ""}">${item.label}<span class="kgm-receipt-key">${item.key}</span></a>`).join("")}</nav>
			<div class="kgm-receipt-section kgm-receipt-grid">
				<div id="kgm-receipt-company"></div>
				<div id="kgm-receipt-date"></div>
				<div id="kgm-receipt-cash"></div>
				<div id="kgm-receipt-customer-field"><div id="kgm-receipt-customer"></div></div>
				<div id="kgm-receipt-account"></div>
				<div><label class="kgm-receipt-label" for="kgm-receipt-amount">${__("Amount received (INR)")}</label><input id="kgm-receipt-amount" class="kgm-receipt-input" type="number" min="0.01" step="0.01" inputmode="decimal"></div>
				<p class="kgm-receipt-help kgm-receipt-selection-help">${__("For a party receipt, choose the customer by name; its receivable account fills automatically. For other receipts, search any posting ledger under the Chart of Accounts groups. Group headings cannot receive entries.")}</p>
			</div>
			<div class="kgm-receipt-section" id="kgm-receipt-invoice-section" style="display:none">
				<h4>${__("Allocate to open Sales Invoices")}</h4>
				<p class="kgm-receipt-help">${__("FIFO: the amount fills the oldest open bill first, then newer bills. You can adjust allocations; any remainder stays unallocated.")}</p>
				<div id="kgm-receipt-invoices"></div>
				<p class="kgm-receipt-help" id="kgm-receipt-allocation-summary"></p>
			</div>
			<div class="kgm-receipt-section" id="kgm-receipt-narration-section">
				<label class="kgm-receipt-label" for="kgm-receipt-narration">${__("Narration")}</label>
				<textarea id="kgm-receipt-narration" class="kgm-receipt-input" rows="2" maxlength="1000"></textarea>
			</div>
			<div class="kgm-receipt-section" id="kgm-receipt-preview-section">
				<div class="kgm-receipt-preview" aria-live="polite">
					<div><span>${__("Debit · Cash")}</span><strong id="kgm-receipt-debit">₹0.00</strong><small id="kgm-receipt-debit-account"></small></div>
					<div><span>${__("Credit · From account")}</span><strong id="kgm-receipt-credit">₹0.00</strong><small id="kgm-receipt-credit-account"></small></div>
				</div>
				<p class="kgm-receipt-help">${__("Draft only. Review and submit the saved voucher to post it.")}</p>
			</div>
			<div class="kgm-receipt-section kgm-receipt-actions">
				<span id="kgm-receipt-status" class="kgm-receipt-status" role="status"></span>
				<button id="kgm-receipt-save" type="button" class="btn btn-primary">${__("Save Draft")}</button>
			</div>
		</div>
	`);

	function makeControl(id, df) {
		const control = frappe.ui.form.make_control({
			parent: $main.find(`#${id}`),
			df,
			render_input: true,
		});
		control.refresh();
		return control;
	}

	controls.company = makeControl("kgm-receipt-company", {
		fieldtype: "Link", fieldname: "company", label: __("Company"), options: "Company", reqd: 1,
	});
	controls.date = makeControl("kgm-receipt-date", {
		fieldtype: "Date", fieldname: "posting_date", label: __("Posting Date"), reqd: 1,
	});
	controls.cash = makeControl("kgm-receipt-cash", {
		fieldtype: "Link", fieldname: "cash_account", label: __("Cash / Bank Account"), options: "Account", reqd: 1,
		get_query: () => ({ filters: { company: controls.company.get_value(), account_type: ["in", ["Cash", "Bank"]], is_group: 0, disabled: 0 } }),
	});
	controls.account = makeControl("kgm-receipt-account", {
		fieldtype: "Link", fieldname: "counterpart_account", label: __("Received From / Transfer From"), options: "Account", reqd: 1,
		get_query: () => ({ filters: { company: controls.company.get_value(), is_group: 0, disabled: 0, account_type: ["not in", ["Payable"]] } }),
	});
	controls.customer = makeControl("kgm-receipt-customer", {
		fieldtype: "Link", fieldname: "customer", label: __("Received From Customer"), options: "Customer",
		get_query: () => ({ filters: { disabled: 0 } }),
	});

	controls.company.$input.on("change", () => {
		if (state.loadingDefaults) return;
		state.customerRequest++;
		state.invoiceRequest++;
		state.customerAutoAccount = false;
		controls.cash.set_value("");
		controls.account.set_value("");
		controls.customer.set_value("");
		state.accountType = "";
		state.receiptAccountType = "";
		state.invoices = [];
		renderCustomer();
		renderReceiptMode();
		renderPreview();
		const company = controls.company.get_value();
		if (company) {
			frappe.call({ method: method + "get_company_defaults", args: { company }, callback(r) {
				if (company === controls.company.get_value()) controls.cash.set_value((r.message || {}).cash_account || "");
			} });
		}
	});
	controls.cash.$input.on("change", receiptAccountChanged);
	controls.account.$input.on("change", accountChanged);
	controls.customer.$input.on("change", customerChanged);
	$main.find("#kgm-receipt-amount").on("input", () => { autoAllocateInvoices(); renderPreview(); renderAllocationSummary(); });
	$main.find("#kgm-receipt-invoices").on("input", "input[data-invoice-index]", renderAllocationSummary);
	$main.find("#kgm-receipt-save").on("click", saveDraft);
	$main.find("#kgm-receipt-save").attr("title", __("Ctrl+S to save draft"));
	function handleTab(event) {
		if (event.key !== "Tab" || event.altKey || event.ctrlKey || event.metaKey || frappe.get_route()[0] !== "cash-receipt-fast-entry") return;
		const fields = $main.find(".kgm-receipt input:not([type=hidden]), .kgm-receipt textarea, #kgm-receipt-save").filter(function() {
			return !this.disabled && this.tabIndex >= 0 && this.getClientRects().length > 0;
		}).toArray();
		const index = fields.indexOf(event.target);
		const next = fields[index + (event.shiftKey ? -1 : 1)];
		if (index < 0 || !next) return;
		event.preventDefault();
		event.stopPropagation();
		const link = Object.values(controls).find(control => control.df.fieldtype === "Link" && control.input === event.target);
		if (link) {
			const dropdown = link.awesomplete;
			const suggestion = dropdown?.opened && dropdown.selected ? dropdown.suggestions[dropdown.index] : null;
			const item = suggestion && dropdown.get_item(suggestion.value);
			const query = (link.get_label_value() || "").trim().toLowerCase();
			dropdown?.close();
			if (item?.value && !item.action && query && link.input_matches_item(query, item)) {
				Promise.resolve(link.set_value(item.value)).then(() => next.focus(), () => next.focus());
				return;
			}
		}
		next.focus();
	}
	if (frappe.pages["cash-receipt-fast-entry"].tabShortcut) {
		document.removeEventListener("keydown", frappe.pages["cash-receipt-fast-entry"].tabShortcut, true);
	}
	frappe.pages["cash-receipt-fast-entry"].tabShortcut = handleTab;
	document.addEventListener("keydown", handleTab, true);
	if (frappe.pages["cash-receipt-fast-entry"].saveShortcut) {
		document.removeEventListener("keydown", frappe.pages["cash-receipt-fast-entry"].saveShortcut, true);
	}
	frappe.pages["cash-receipt-fast-entry"].saveShortcut = function(event) {
		const route = frappe.get_route()[0];
		if (
			(event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey &&
			event.key.toLowerCase() === "s" && route === "cash-receipt-fast-entry"
		) {
			event.preventDefault();
			event.stopPropagation();
			saveDraft();
		}
		const routeConfig = routes.find(item => item.key === event.key && route === "cash-receipt-fast-entry");
		if (!event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && routeConfig) {
			event.preventDefault();
			frappe.set_route(routeConfig.route);
		}
	};
	document.addEventListener("keydown", frappe.pages["cash-receipt-fast-entry"].saveShortcut, true);

	frappe.call({ method: method + "get_page_context", callback(r) {
		const defaults = r.message || {};
		Promise.resolve(controls.company.set_value(defaults.company || "")).then(() => {
			controls.date.set_value(defaults.posting_date || frappe.datetime.get_today());
			Promise.resolve(controls.cash.set_value(defaults.cash_account || "")).then(() => {
				state.loadingDefaults = false;
				receiptAccountChanged();
				controls.customer.$input.trigger("focus");
			});
		});
	} });

	function accountChanged() {
		if (state.settingAccountFromCustomer) return;
		state.customerRequest++;
		state.invoiceRequest++;
		state.customerAutoAccount = false;
		const company = controls.company.get_value();
		const account = controls.account.get_value();
		state.accountType = "";
		state.invoices = [];
		controls.customer.set_value("");
		renderCustomer();
		renderPreview();
		if (!company || !account) return;
		frappe.call({ method: method + "get_counterpart_kind", args: { company, account }, callback(r) {
			if (company !== controls.company.get_value() || account !== controls.account.get_value()) return;
			state.accountType = (r.message || {}).account_type || "";
			renderCustomer();
			renderReceiptMode();
		} });
	}

	function customerChanged() {
		const company = controls.company.get_value();
		const customer = controls.customer.get_value();
		const request = ++state.customerRequest;
		state.invoiceRequest++;
		state.invoices = [];
		state.accountType = "";
		$main.find("#kgm-receipt-invoices").empty();
		renderCustomer();
		renderPreview();
		if (!customer) {
			if (state.customerAutoAccount) {
				state.customerAutoAccount = false;
				controls.account.set_value("");
			}
			return;
		}
		if (!company) return;
		frappe.call({ method: method + "get_customer_receivable_account", args: { company, customer }, callback(r) {
			if (request !== state.customerRequest || company !== controls.company.get_value() || customer !== controls.customer.get_value()) return;
			const account = (r.message || {}).account;
			if (!account) return;
			state.settingAccountFromCustomer = true;
			Promise.resolve(controls.account.set_value(account)).then(() => {
				state.settingAccountFromCustomer = false;
				if (request !== state.customerRequest || company !== controls.company.get_value() || customer !== controls.customer.get_value()) return;
				state.customerAutoAccount = true;
				state.accountType = "Receivable";
				renderCustomer();
				renderPreview();
				loadInvoices();
			}, () => { state.settingAccountFromCustomer = false; });
		} });
	}

	function receiptAccountChanged() {
		const company = controls.company.get_value();
		const account = controls.cash.get_value();
		state.receiptAccountType = "";
		renderReceiptMode();
		renderPreview();
		if (!company || !account) return;
		frappe.call({ method: method + "get_receipt_account_kind", args: { company, account }, callback(r) {
			if (company !== controls.company.get_value() || account !== controls.cash.get_value()) return;
			state.receiptAccountType = (r.message || {}).account_type || "";
			renderReceiptMode();
		} });
	}

	function renderReceiptMode() {
		$main.find("#kgm-receipt-preview-section span").first().text(state.receiptAccountType === "Bank" ? __("Debit · Bank") : __("Debit · Cash"));
	}

	function renderCustomer() {
		const isCustomer = state.accountType === "Receivable" && !!controls.customer.get_value();
		$main.find("#kgm-receipt-invoice-section").toggle(isCustomer);
		if (!isCustomer) $main.find("#kgm-receipt-invoices").empty();
		renderAllocationSummary();
	}

	function loadInvoices() {
		const company = controls.company.get_value();
		const account = controls.account.get_value();
		const customer = controls.customer.get_value();
		const request = ++state.invoiceRequest;
		state.invoices = [];
		$main.find("#kgm-receipt-invoices").empty();
		renderAllocationSummary();
		if (!company || !account || !customer || state.accountType !== "Receivable") return;
		$main.find("#kgm-receipt-invoices").text(__("Loading open invoices..."));
		frappe.call({ method: method + "get_open_invoices", args: { company, account, customer }, callback(r) {
			if (request !== state.invoiceRequest || customer !== controls.customer.get_value() || account !== controls.account.get_value()) return;
			state.invoices = r.message || [];
			renderInvoices();
		} });
	}

	function renderInvoices() {
		const $box = $main.find("#kgm-receipt-invoices");
		if (!state.invoices.length) {
			$box.text(__("No open Sales Invoices found. You can still save an unallocated receipt."));
			return;
		}
		const rows = state.invoices.map((invoice, index) => `
			<div class="kgm-receipt-invoice-row">
				<div class="kgm-receipt-invoice-name"><strong title="${frappe.utils.escape_html(invoice.invoice)}">${frappe.utils.escape_html(invoice.invoice)}</strong><small>${invoice.payment_term ? `${frappe.utils.escape_html(invoice.payment_term)} · ` : ""}${__("Due")} ${frappe.utils.escape_html(invoice.due_date || "")}</small></div>
				<span class="kgm-receipt-invoice-outstanding" title="${__("Outstanding")}">${format_currency(invoice.outstanding_amount, "INR")}</span>
				<input class="kgm-receipt-input" type="number" min="0" step="0.01" max="${invoice.outstanding_amount}" data-invoice-index="${index}" aria-label="${__("Allocation for {0}", [invoice.invoice])}" placeholder="${__("Allocate")}">
			</div>`).join("");
		$box.html(`<div class="kgm-receipt-invoice-list">${rows}</div>`);
		autoAllocateInvoices();
		renderAllocationSummary();
	}

	function autoAllocateInvoices() {
		if (state.accountType !== "Receivable") return;
		let remaining = Math.max(0, Math.round((Number($main.find("#kgm-receipt-amount").val()) || 0) * 100));
		$main.find("input[data-invoice-index]").each(function() {
			const invoice = state.invoices[Number($(this).data("invoice-index"))];
			const allocated = Math.min(remaining, Math.round(Number(invoice.outstanding_amount) * 100));
			$(this).val(allocated ? (allocated / 100).toFixed(2) : "");
			remaining -= allocated;
		});
	}

	function getAllocations() {
		const allocations = [];
		$main.find("input[data-invoice-index]").each(function() {
			const value = Number($(this).val());
			if (value > 0) {
				const invoice = state.invoices[Number($(this).data("invoice-index"))];
				allocations.push({ invoice: invoice.invoice, payment_term: invoice.payment_term, amount: value });
			}
		});
		return allocations;
	}

	function renderAllocationSummary() {
		if (state.accountType !== "Receivable") return;
		const amount = Number($main.find("#kgm-receipt-amount").val()) || 0;
		const allocated = getAllocations().reduce((sum, row) => sum + row.amount, 0);
		const remaining = Math.max(0, amount - allocated);
		$main.find("#kgm-receipt-allocation-summary").text(__("Allocated: {0} · Unallocated: {1}", [format_currency(allocated, "INR"), format_currency(remaining, "INR")]));
	}

	function renderPreview() {
		const amount = Number($main.find("#kgm-receipt-amount").val()) || 0;
		$main.find("#kgm-receipt-debit, #kgm-receipt-credit").text(format_currency(amount, "INR"));
		$main.find("#kgm-receipt-debit-account").text(controls.cash.get_value() || "");
		const account = controls.account.get_value();
		const customer = controls.customer.get_value();
		$main.find("#kgm-receipt-credit-account").text(customer && state.accountType === "Receivable" ? `${customer} · ${account}` : account || "");
	}

	function prepareNextEntry() {
		state.customerRequest++;
		state.invoiceRequest++;
		state.invoices = [];
		state.accountType = "";
		state.customerAutoAccount = false;
		$main.find("#kgm-receipt-amount, #kgm-receipt-narration").val("");
		controls.customer.set_value("");
		renderCustomer();
		renderPreview();
		Promise.resolve(controls.account.set_value("")).then(() => {
			controls.customer.$input.trigger("focus");
		});
	}

	function saveDraft() {
		if (state.saving) return;
		const validMoneyInput = /^(?:\d+(?:\.\d{0,2})?|\.\d{1,2})$/;
		const amountText = $main.find("#kgm-receipt-amount").val();
		const amount = Number(amountText);
		if (!controls.company.get_value() || !controls.date.get_value() || !controls.cash.get_value() || !controls.account.get_value() || !validMoneyInput.test(amountText) || !Number.isFinite(amount) || amount <= 0) {
			frappe.msgprint(__("Choose the date and both accounts, then enter a positive amount with at most two decimal places."));
			return;
		}
		let invalidAllocation = false;
		$main.find("input[data-invoice-index]").each(function() {
			const value = $(this).val();
			if (value !== "" && (!validMoneyInput.test(value) || Number(value) > state.invoices[Number($(this).data("invoice-index"))].outstanding_amount)) {
				invalidAllocation = true;
			}
		});
		if (invalidAllocation) {
			frappe.msgprint(__("Enter a non-negative invoice allocation with at most two decimal places, no greater than the invoice outstanding amount."));
			return;
		}
		if (state.accountType === "Receivable" && !controls.customer.get_value()) {
			frappe.msgprint(__("Select a customer for this receivable account."));
			return;
		}
		if (controls.customer.get_value() && state.accountType !== "Receivable") {
			frappe.msgprint(__("Wait for the customer's receivable account to load."));
			return;
		}
		const allocations = getAllocations();
		if (allocations.reduce((sum, row) => sum + row.amount, 0) > amount + 0.001) {
			frappe.msgprint(__("Invoice allocations cannot exceed the cash received."));
			return;
		}
		state.saving = true;
		$main.find("#kgm-receipt-save").prop("disabled", true);
		$main.find("#kgm-receipt-status").text(__("Saving draft..."));
		frappe.call({
			method: method + "save_cash_receipt_draft",
			args: {
				company: controls.company.get_value(),
				posting_date: controls.date.get_value(),
				cash_account: controls.cash.get_value(),
				counterpart_account: controls.account.get_value(),
				amount: $main.find("#kgm-receipt-amount").val(),
				narration: $main.find("#kgm-receipt-narration").val(),
				customer: state.accountType === "Receivable" ? controls.customer.get_value() : "",
				allocations,
			},
			freeze: true,
			freeze_message: __("Saving cash receipt draft"),
			callback(r) {
				const voucher = r.message || {};
				if (!voucher.name) return;
				const voucherPath = voucher.doctype === "Payment Entry" ? "payment-entry" : "journal-entry";
				const $link = $("<a>", {
					href: `/app/${voucherPath}/${encodeURIComponent(voucher.name)}`,
					text: __("Open voucher"),
					target: "_blank",
					rel: "noopener noreferrer",
				});
				$main.find("#kgm-receipt-status").text(__("Saved draft {0}.", [voucher.name]) + " ").append($link);
				prepareNextEntry();
			},
			always() {
				state.saving = false;
				$main.find("#kgm-receipt-save").prop("disabled", false);
			},
		});
	}
};
