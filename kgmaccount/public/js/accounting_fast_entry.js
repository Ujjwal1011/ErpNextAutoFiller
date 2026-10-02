window.kgmaccount = window.kgmaccount || {};

window.kgmaccount.accountingFastEntry = {
	make(wrapper, config) {
		const page = frappe.ui.make_app_page({ parent: wrapper, title: __(config.title), single_column: true });
		const method = "kgmaccount.auto_filler.utils.accounting_fast_entry.";
		const $main = $(wrapper).find(".layout-main-section");
		const state = { counterpartType: "", invoices: [], invoiceRequest: 0, customerRequest: 0, customerAutoAccount: false, settingAccountFromCustomer: false, saving: false, loadingDefaults: true };
		const controls = {};
		const routes = [
			{ key: "F6", route: "cash-receipt-fast-entry", label: __("Receipt") },
			{ key: "F5", route: "payment-fast-entry", label: __("Payment") },
		];

		$main.html(`
			<style>
				.kgm-fast-entry { max-width: 1180px; margin: 0 auto; background: #fff; border: 1px solid #dce3e9; border-radius: 8px; overflow: hidden; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
				.kgm-fast-head, .kgm-fast-switch, .kgm-fast-grid, .kgm-fast-invoice-section, .kgm-fast-actions { grid-column: 1 / -1; }
				.kgm-fast-head { padding: 8px 14px; background: #eaf5f1; border-bottom: 1px solid #cce3da; }
				.kgm-fast-head h2 { margin: 0 0 2px; font-size: 18px; }
				.kgm-fast-head p { margin: 0; color: #52665e; }
				.kgm-fast-switch { display: flex; gap: 6px; flex-wrap: wrap; padding: 6px 14px; background: #f8fafc; border-bottom: 1px solid #e8edf1; }
				.kgm-fast-switch a { padding: 3px 7px; border: 1px solid #dce3e9; border-radius: 5px; color: #52616f; font-size: 12px; text-decoration: none; }
				.kgm-fast-switch a.active { background: #eaf5f1; border-color: #94c7b4; color: #143f30; font-weight: 700; }
				.kgm-fast-key { color: #7a8795; margin-left: 4px; }
				.kgm-fast-section { padding: 8px 14px; border-bottom: 1px solid #e8edf1; }
				.kgm-fast-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px 12px; }
				.kgm-fast-grid .frappe-control { margin-bottom: 0; }
				.kgm-fast-label { display: block; font-size: 12px; font-weight: 700; color: #52616f; margin-bottom: 3px; }
				.kgm-fast-input { width: 100%; min-height: 36px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 7px 9px; background: #fff; }
				.kgm-fast-input:focus { outline: 2px solid #b7ded0; outline-offset: 1px; }
				.kgm-fast-invoice-section h4 { margin: 0; font-size: 15px; line-height: 20px; }
				.kgm-fast-help { color: #64748b; font-size: 12px; margin: 3px 0 4px; }
				.kgm-fast-invoice-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px 10px; }
				.kgm-fast-invoice-row { display: grid; grid-template-columns: minmax(0, 1fr) auto 100px; gap: 7px; align-items: center; min-width: 0; padding: 4px 7px; border: 1px solid #dce3e9; border-radius: 6px; }
				.kgm-fast-invoice-name { min-width: 0; font-size: 12px; line-height: 1.25; }
				.kgm-fast-invoice-name strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
				.kgm-fast-invoice-name small { display: block; color: #64748b; }
				.kgm-fast-invoice-outstanding { white-space: nowrap; font-size: 12px; text-align: right; }
				.kgm-fast-invoice-row input { min-height: 28px; padding: 3px 5px; text-align: right; }
				.kgm-fast-narration { grid-column: 1; border-right: 1px solid #e8edf1; }
				.kgm-fast-preview-section { grid-column: 2; }
				#kgm-fast-narration { min-height: 54px; }
				.kgm-fast-preview { display: flex; justify-content: space-between; gap: 10px; background: #f8fafc; border: 1px solid #dce3e9; border-radius: 6px; padding: 8px; }
				.kgm-fast-preview strong { display: block; color: #143f30; font-size: 15px; }
				.kgm-fast-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
				.kgm-fast-status { color: #64748b; font-size: 12px; }
				@media (max-width: 760px) { .kgm-fast-entry { grid-template-columns: 1fr; } .kgm-fast-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .kgm-fast-invoice-list { grid-template-columns: 1fr; } .kgm-fast-narration, .kgm-fast-preview-section { grid-column: 1 / -1; border-right: 0; } }
				@media (max-width: 520px) { .kgm-fast-grid { grid-template-columns: 1fr; } }
			</style>
			<div class="kgm-fast-entry">
				<div class="kgm-fast-head"><h2>${__(config.title)}</h2><p>${__(config.subtitle)}</p></div>
				<nav class="kgm-fast-switch" aria-label="${__("Accounting fast-entry pages")}">${routes.map(item => `<a href="/app/${item.route}" class="${item.route === config.route ? "active" : ""}">${item.label}<span class="kgm-fast-key">${item.key}</span></a>`).join("")}</nav>
				<div class="kgm-fast-section kgm-fast-grid">
					<div id="kgm-fast-company"></div><div id="kgm-fast-date"></div><div id="kgm-fast-source"></div>
					${config.customerPayment ? `<div id="kgm-fast-customer"></div>` : ""}
					<div id="kgm-fast-counterpart"></div>
					<div><label class="kgm-fast-label" for="kgm-fast-amount">${__("Amount (INR)")}</label><input id="kgm-fast-amount" class="kgm-fast-input" type="number" min="0.01" step="0.01" inputmode="decimal"></div>
					<div id="kgm-fast-party-field" style="display:none"><div id="kgm-fast-party"></div></div>
					${config.referenceFields ? `<div><label class="kgm-fast-label" for="kgm-fast-reference-no">${__("Bank Reference No")}</label><input id="kgm-fast-reference-no" class="kgm-fast-input" maxlength="140"></div><div id="kgm-fast-reference-date"></div>` : ""}
				</div>
				<div class="kgm-fast-section kgm-fast-invoice-section" id="kgm-fast-invoice-section" style="display:none"><h4>${__(config.invoiceTitle || "Allocate to open invoices")}</h4><p class="kgm-fast-help">${__(config.invoiceHelp || "Enter allocations. Any remainder remains unallocated.")}</p><div id="kgm-fast-invoices"></div><p class="kgm-fast-help" id="kgm-fast-allocation-summary"></p></div>
				<div class="kgm-fast-section kgm-fast-narration"><label class="kgm-fast-label" for="kgm-fast-narration">${__("Narration")}</label><textarea id="kgm-fast-narration" class="kgm-fast-input" rows="2" maxlength="1000"></textarea></div>
				<div class="kgm-fast-section kgm-fast-preview-section"><div class="kgm-fast-preview"><div><span>${__(config.debitLabel)}</span><strong id="kgm-fast-debit">₹0.00</strong><small id="kgm-fast-debit-account"></small></div><div><span>${__(config.creditLabel)}</span><strong id="kgm-fast-credit">₹0.00</strong><small id="kgm-fast-credit-account"></small></div></div><p class="kgm-fast-help">${__("Draft only. Review and submit the saved voucher to post it.")}</p></div>
				<div class="kgm-fast-section kgm-fast-actions"><span id="kgm-fast-status" class="kgm-fast-status" role="status"></span><button id="kgm-fast-save" type="button" class="btn btn-primary">${__("Save Draft")}</button></div>
			</div>
		`);

		function makeControl(id, df) {
			const control = frappe.ui.form.make_control({ parent: $main.find(`#${id}`), df, render_input: true });
			control.refresh();
			return control;
		}
		controls.company = makeControl("kgm-fast-company", { fieldtype: "Link", fieldname: "company", label: __("Company"), options: "Company", reqd: 1 });
		controls.date = makeControl("kgm-fast-date", { fieldtype: "Date", fieldname: "posting_date", label: __("Posting Date"), reqd: 1 });
		controls.source = makeControl("kgm-fast-source", { fieldtype: "Link", fieldname: "source_account", label: __(config.sourceLabel), options: "Account", reqd: 1, get_query: () => ({ filters: { company: controls.company.get_value(), account_type: ["in", config.sourceTypes], is_group: 0, disabled: 0 } }) });
		controls.counterpart = makeControl("kgm-fast-counterpart", { fieldtype: "Link", fieldname: "counterpart_account", label: __(config.counterpartLabel), options: "Account", reqd: 1, get_query: () => ({ filters: { company: controls.company.get_value(), is_group: 0, disabled: 0 } }) });
		controls.party = makeControl("kgm-fast-party", { fieldtype: "Link", fieldname: "party", label: __(config.partyLabel || "Party"), options: config.partyType || "Customer", reqd: 1 });
		if (config.customerPayment) controls.customer = makeControl("kgm-fast-customer", { fieldtype: "Link", fieldname: "customer", label: __("Paid To Customer"), options: "Customer", get_query: () => ({ filters: { disabled: 0 } }) });
		if (config.referenceFields) controls.referenceDate = makeControl("kgm-fast-reference-date", { fieldtype: "Date", fieldname: "reference_date", label: __("Bank Reference Date"), reqd: Boolean(config.referenceRequired) });

		controls.company.$input.on("change", () => {
			if (state.loadingDefaults) return;
			state.customerRequest++; state.customerAutoAccount = false;
			if (controls.customer) controls.customer.set_value("");
			controls.source.set_value(""); controls.counterpart.set_value(""); controls.party.set_value("");
			state.counterpartType = ""; state.invoices = []; renderParty(); renderPreview();
			const company = controls.company.get_value();
			if (company) frappe.call({ method: method + "get_company_defaults", args: { flow: config.flow, company }, callback(r) { if (company === controls.company.get_value()) controls.source.set_value((r.message || {}).source_account || ""); } });
		});
		controls.source.$input.on("change", renderPreview);
		controls.counterpart.$input.on("change", counterpartChanged);
		controls.party.$input.on("change", loadInvoices);
		if (controls.customer) controls.customer.$input.on("change", customerChanged);
		$main.find("#kgm-fast-amount").on("input", () => { if (config.autoAllocate) autoAllocateInvoices(); renderPreview(); renderAllocationSummary(); });
		$main.find("#kgm-fast-invoices").on("input", "input[data-invoice-index]", renderAllocationSummary);
		$main.find("#kgm-fast-save").on("click", saveDraft).attr("title", __("Ctrl+S to save draft"));
		function handleTab(event) {
			if (event.key !== "Tab" || event.altKey || event.ctrlKey || event.metaKey || frappe.get_route()[0] !== config.route) return;
			const fields = $main.find(".kgm-fast-entry input:not([type=hidden]), .kgm-fast-entry textarea, #kgm-fast-save").filter(function() {
				return !this.disabled && this.tabIndex >= 0 && this.getClientRects().length > 0;
			}).toArray();
			const index = fields.indexOf(event.target), next = fields[index + (event.shiftKey ? -1 : 1)];
			if (index < 0 || !next) return;
			event.preventDefault(); event.stopPropagation();
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
		if (frappe.pages[config.route].tabShortcut) document.removeEventListener("keydown", frappe.pages[config.route].tabShortcut, true);
		frappe.pages[config.route].tabShortcut = handleTab;
		document.addEventListener("keydown", handleTab, true);

		if (frappe.pages[config.route].saveShortcut) document.removeEventListener("keydown", frappe.pages[config.route].saveShortcut, true);
		frappe.pages[config.route].saveShortcut = function(event) {
			const route = frappe.get_route()[0];
			if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "s" && route === config.route) { event.preventDefault(); event.stopPropagation(); saveDraft(); }
			const routeConfig = routes.find(item => item.key === event.key && route === config.route);
			if (!event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && routeConfig) { event.preventDefault(); frappe.set_route(routeConfig.route); }
		};
		document.addEventListener("keydown", frappe.pages[config.route].saveShortcut, true);

		frappe.call({ method: method + "get_page_context", args: { flow: config.flow }, callback(r) {
			const defaults = r.message || {};
			Promise.resolve(controls.company.set_value(defaults.company || "")).then(() => { controls.date.set_value(defaults.posting_date || frappe.datetime.get_today()); if (controls.referenceDate) controls.referenceDate.set_value(defaults.posting_date || frappe.datetime.get_today()); Promise.resolve(controls.source.set_value(defaults.source_account || "")).then(() => { state.loadingDefaults = false; (controls.customer || controls.counterpart).$input.trigger("focus"); }); });
		} });

		function counterpartChanged() {
			if (state.settingAccountFromCustomer) return;
			state.customerRequest++; state.customerAutoAccount = false;
			if (controls.customer) controls.customer.set_value("");
			const company = controls.company.get_value(), account = controls.counterpart.get_value();
			state.counterpartType = ""; state.invoices = []; controls.party.set_value(""); renderParty(); renderPreview();
			if (!company || !account) return;
			frappe.call({ method: method + "get_counterpart_kind", args: { flow: config.flow, company, counterpart_account: account }, callback(r) { if (company !== controls.company.get_value() || account !== controls.counterpart.get_value()) return; state.counterpartType = (r.message || {}).account_type || ""; renderParty(); } });
		}
		function customerChanged() {
			if (!controls.customer) return;
			const company = controls.company.get_value(), customer = controls.customer.get_value(), request = ++state.customerRequest;
			if (!customer) {
				if (state.customerAutoAccount) { state.customerAutoAccount = false; controls.counterpart.set_value(""); }
				renderPreview();
				return;
			}
			if (!company) return;
			frappe.call({ method: method + "get_customer_receivable_account", args: { company, customer }, callback(r) {
				if (request !== state.customerRequest || company !== controls.company.get_value() || customer !== controls.customer.get_value()) return;
				const account = (r.message || {}).account;
				if (!account) return;
				state.settingAccountFromCustomer = true;
				Promise.resolve(controls.counterpart.set_value(account)).then(() => {
					state.settingAccountFromCustomer = false;
					if (request !== state.customerRequest || company !== controls.company.get_value() || customer !== controls.customer.get_value()) return;
					state.customerAutoAccount = true; state.counterpartType = "Receivable";
					renderParty(); renderPreview(); $main.find("#kgm-fast-amount").trigger("focus");
				}, () => { state.settingAccountFromCustomer = false; });
			} });
		}
		function partyRequired() { return Boolean(config.partyType && state.counterpartType === config.partyAccountType); }
		function renderParty() {
			const visible = partyRequired();
			$main.find("#kgm-fast-party-field").toggle(visible); $main.find("#kgm-fast-invoice-section").toggle(visible && Boolean(config.invoiceDoctype));
			if (!visible) $main.find("#kgm-fast-invoices").empty(); renderAllocationSummary();
		}
		function loadInvoices() {
			const company = controls.company.get_value(), account = controls.counterpart.get_value(), party = controls.party.get_value(), request = ++state.invoiceRequest;
			state.invoices = []; $main.find("#kgm-fast-invoices").empty(); renderAllocationSummary();
			if (!company || !account || !party || !partyRequired() || !config.invoiceDoctype) return;
			$main.find("#kgm-fast-invoices").text(__("Loading open invoices..."));
			frappe.call({ method: method + "get_open_invoices", args: { flow: config.flow, company, account, party }, callback(r) { if (request !== state.invoiceRequest || party !== controls.party.get_value() || account !== controls.counterpart.get_value()) return; state.invoices = r.message || []; renderInvoices(); } });
		}
		function renderInvoices() {
			const $box = $main.find("#kgm-fast-invoices");
			if (!state.invoices.length) { $box.text(__("No open invoices found. You can still save an unallocated payment.")); return; }
			const rows = state.invoices.map((invoice, index) => `<div class="kgm-fast-invoice-row"><div class="kgm-fast-invoice-name"><strong title="${frappe.utils.escape_html(invoice.invoice)}">${frappe.utils.escape_html(invoice.invoice)}</strong><small>${invoice.payment_term ? `${frappe.utils.escape_html(invoice.payment_term)} · ` : ""}${__("Due")} ${frappe.utils.escape_html(invoice.due_date || "")}</small></div><span class="kgm-fast-invoice-outstanding" title="${__("Outstanding")}">${format_currency(invoice.outstanding_amount, "INR")}</span><input class="kgm-fast-input" type="number" min="0" step="0.01" max="${invoice.outstanding_amount}" data-invoice-index="${index}" aria-label="${__("Allocation for {0}", [invoice.invoice])}" placeholder="${__("Allocate")}"></div>`).join("");
			$box.html(`<div class="kgm-fast-invoice-list">${rows}</div>`); if (config.autoAllocate) autoAllocateInvoices(); renderAllocationSummary();
		}
		function autoAllocateInvoices() {
			let remaining = Math.max(0, Math.round((Number($main.find("#kgm-fast-amount").val()) || 0) * 100));
			$main.find("input[data-invoice-index]").each(function() {
				const invoice = state.invoices[Number($(this).data("invoice-index"))];
				const allocated = Math.min(remaining, Math.round(Number(invoice.outstanding_amount) * 100));
				$(this).val(allocated ? (allocated / 100).toFixed(2) : "");
				remaining -= allocated;
			});
		}
		function getAllocations() { const rows = []; $main.find("input[data-invoice-index]").each(function() { const value = Number($(this).val()); if (value > 0) { const invoice = state.invoices[Number($(this).data("invoice-index"))]; rows.push({ invoice: invoice.invoice, payment_term: invoice.payment_term, amount: value }); } }); return rows; }
		function renderAllocationSummary() { if (!partyRequired() || !config.invoiceDoctype) return; const amount = Number($main.find("#kgm-fast-amount").val()) || 0, allocated = getAllocations().reduce((sum, row) => sum + row.amount, 0), remaining = Math.max(0, amount - allocated); $main.find("#kgm-fast-allocation-summary").text(__("Allocated: {0} · Unallocated: {1}", [format_currency(allocated, "INR"), format_currency(remaining, "INR")])); }
		function renderPreview() { const amount = Number($main.find("#kgm-fast-amount").val()) || 0; $main.find("#kgm-fast-debit, #kgm-fast-credit").text(format_currency(amount, "INR")); const debit = (config.debitAccount === "source" ? controls.source : controls.counterpart).get_value() || "", credit = (config.creditAccount === "source" ? controls.source : controls.counterpart).get_value() || "", customer = controls.customer && controls.customer.get_value(); $main.find("#kgm-fast-debit-account").text(customer && state.counterpartType === "Receivable" ? `${customer} · ${debit}` : debit); $main.find("#kgm-fast-credit-account").text(credit); }
		function prepareNextEntry() { state.invoiceRequest++; state.customerRequest++; state.invoices = []; state.counterpartType = ""; state.customerAutoAccount = false; $main.find("#kgm-fast-amount, #kgm-fast-narration, #kgm-fast-reference-no").val(""); controls.party.set_value(""); if (controls.customer) controls.customer.set_value(""); renderParty(); renderPreview(); Promise.resolve(controls.counterpart.set_value("")).then(() => (controls.customer || controls.counterpart).$input.trigger("focus")); }
		function saveDraft() {
			if (state.saving) return;
			const validMoney = /^(?:\d+(?:\.\d{0,2})?|\.\d{1,2})$/, text = $main.find("#kgm-fast-amount").val(), amount = Number(text);
			if (!controls.company.get_value() || !controls.date.get_value() || !controls.source.get_value() || !controls.counterpart.get_value() || !validMoney.test(text) || !Number.isFinite(amount) || amount <= 0) { frappe.msgprint(__("Choose the date and both accounts, then enter a positive amount with at most two decimal places.")); return; }
			let invalidAllocation = false; $main.find("input[data-invoice-index]").each(function() { const value = $(this).val(); if (value !== "" && (!validMoney.test(value) || Number(value) > state.invoices[Number($(this).data("invoice-index"))].outstanding_amount)) invalidAllocation = true; });
			if (invalidAllocation) { frappe.msgprint(__("Enter a non-negative invoice allocation with at most two decimal places, no greater than the invoice outstanding amount.")); return; }
			if (partyRequired() && !controls.party.get_value()) { frappe.msgprint(__("Select the party for this account.")); return; }
			if (config.customerPayment && state.counterpartType === "Receivable" && !controls.customer.get_value()) { frappe.msgprint(__("Select the customer for this receivable account.")); return; }
			if (controls.customer && controls.customer.get_value() && state.counterpartType !== "Receivable") { frappe.msgprint(__("Wait for the customer's receivable account to load.")); return; }
			if (config.referenceRequired && (!$main.find("#kgm-fast-reference-no").val().trim() || !controls.referenceDate.get_value())) { frappe.msgprint(__("Enter the bank reference number and date.")); return; }
			const allocations = getAllocations(); if (allocations.reduce((sum, row) => sum + row.amount, 0) > amount + 0.001) { frappe.msgprint(__("Invoice allocations cannot exceed the payment amount.")); return; }
			state.saving = true; $main.find("#kgm-fast-save").prop("disabled", true); $main.find("#kgm-fast-status").text(__("Saving draft..."));
			frappe.call({ method: method + "save_draft", args: { flow: config.flow, company: controls.company.get_value(), posting_date: controls.date.get_value(), source_account: controls.source.get_value(), counterpart_account: controls.counterpart.get_value(), amount: text, narration: $main.find("#kgm-fast-narration").val(), party: partyRequired() ? controls.party.get_value() : "", customer: controls.customer ? controls.customer.get_value() : "", allocations, reference_no: $main.find("#kgm-fast-reference-no").val(), reference_date: controls.referenceDate ? controls.referenceDate.get_value() : "" }, freeze: true, freeze_message: __("Saving draft"), callback(r) { const voucher = r.message || {}; if (!voucher.name) return; const route = voucher.doctype === "Payment Entry" ? "payment-entry" : "journal-entry"; const $link = $("<a>", { href: `/app/${route}/${encodeURIComponent(voucher.name)}`, text: __("Open voucher"), target: "_blank", rel: "noopener noreferrer" }); $main.find("#kgm-fast-status").text(__("Saved draft {0}.", [voucher.name]) + " ").append($link); prepareNextEntry(); }, always() { state.saving = false; $main.find("#kgm-fast-save").prop("disabled", false); } });
		}
	},
};
