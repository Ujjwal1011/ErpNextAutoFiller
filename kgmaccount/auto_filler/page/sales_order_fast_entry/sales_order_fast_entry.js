frappe.pages["sales-order-fast-entry"].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Sales Order Fast Entry"),
		single_column: true,
	});

	const methodRoot = "kgmaccount.auto_filler.page.sales_order_fast_entry.sales_order_fast_entry.";
	const state = {
		entries: [],
		taxes: [],
		workItems: [],
		lastGeneratedItemCode: "",
		itemDetailsRequest: 0,
		lastOperationItemCode: "",
		lastSalesOrder: null,
		livePreviewTimer: null,
		livePreviewRequest: 0,
		workOptionsKey: "",
		isAddingEntry: false,
		editingIndex: null,
		lastSideMode: "",
		sqftManual: false,
	};

	const $main = $(wrapper).find(".layout-main-section");
	$main.html(`
		<style>
			#page-sales-order-fast-entry .layout-main-section { padding: 0; }
			#page-sales-order-fast-entry .layout-main { margin: 0; }
			.kgm-fast-shell { display: flex; flex-direction: column; min-height: calc(100vh - 150px); background: #ffffff; border: 1px solid #d8e1e8; border-radius: 8px; overflow: hidden; color: #24323d; }
			.kgm-fast-band { background: #ffffff; border-bottom: 1px solid #d5e9df; padding: 10px 12px; }
			.kgm-fast-band:first-child { background: #f3faf7; }
			.kgm-fast-header { display: grid; grid-template-columns: minmax(220px, 1.35fr) repeat(4, minmax(120px, 0.75fr)); gap: 12px; align-items: end; }
			.kgm-entry-band { overflow: visible; }
			.kgm-entry-grid { display: grid; grid-template-columns: 110px minmax(220px, 1fr) repeat(4, minmax(88px, 130px)); gap: 10px; align-items: end; }
			.kgm-entry-grid.second { grid-template-columns: 118px minmax(300px, 1.15fr) minmax(90px, 105px) minmax(120px, 140px) minmax(240px, 1fr) minmax(100px, 120px) minmax(120px, 150px); margin-top: 10px; }
			.kgm-field { min-width: 0; }
			.kgm-field label { display: block; margin: 0 0 4px; color: #405751; font-size: 11px; font-weight: 700; }
			.kgm-field input, .kgm-field select { width: 100%; height: 32px; border: 1px solid #bdcbd5; border-radius: 4px; padding: 4px 7px; background: #fff; color: #24323d; }
			.kgm-fast-shell .frappe-control { margin-bottom: 0; }
			.kgm-fast-shell .control-label { margin-bottom: 4px; color: #405751; font-size: 11px; font-weight: 700; }
			.kgm-fast-shell .form-control { min-height: 32px; height: 32px; border-color: #bdcbd5; border-radius: 4px; background: #fff; color: #24323d; }
			.kgm-fast-shell input:focus, .kgm-fast-shell select:focus, .kgm-fast-shell .form-control:focus { border-color: #55a97d; box-shadow: 0 0 0 2px rgba(34, 139, 89, 0.12); }
			.kgm-generated { min-height: 32px; display: flex; align-items: center; gap: 8px; padding: 4px 8px; border: 1px solid #bdcbd5; border-radius: 4px; background: #f8fbfa; font-weight: 700; color: #24323d; overflow: hidden; }
			.kgm-generated span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.kgm-generated.missing { border-color: #f59e0b; background: #fff7ed; color: #92400e; }
			.kgm-segment, .kgm-sides { display: flex; flex-wrap: nowrap; gap: 6px; max-width: 100%; overflow-x: auto; }
			.kgm-segment button, .kgm-sides button, .kgm-action { min-height: 34px; border: 1px solid #c5d4ce; border-radius: 7px; background: #ffffff; color: #285044; padding: 6px 10px; font-size: 12px; font-weight: 650; line-height: 1.25; cursor: pointer; transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease; }
			.kgm-segment button, .kgm-sides button { flex: 0 0 auto; white-space: nowrap; }
			.kgm-action { display: inline-flex; align-items: center; justify-content: center; gap: 8px; white-space: nowrap; }
			.kgm-action kbd { display: inline-block; border: 1px solid #c5d4ce; border-radius: 4px; background: #f4f8f6; color: #456257; padding: 2px 5px; font-family: inherit; font-size: 10px; font-weight: 600; line-height: 1.2; white-space: nowrap; }
			.kgm-action.primary kbd { border-color: rgba(255,255,255,.35); background: rgba(255,255,255,.14); color: #ffffff; }
			.kgm-shortcuts { display: inline-flex; align-items: center; gap: 4px; }
			.kgm-shortcuts > span { font-size: 10px; opacity: .8; }
			.kgm-segment button:hover, .kgm-sides button:hover, .kgm-action:not(.primary):hover { background: #edf7f2; border-color: #69aa88; }
			.kgm-segment button.active, .kgm-sides button.active { background: #18765a; border-color: #18765a; color: #ffffff; }
			.kgm-action.primary { background: #18765a; border-color: #18765a; color: #ffffff; box-shadow: 0 2px 5px rgba(24,118,90,.16); }
			.kgm-action.primary:hover { background: #125f48; border-color: #125f48; box-shadow: 0 3px 8px rgba(24,118,90,.22); }
			.kgm-action.danger { color: #a43232; border-color: #edc7c7; background: #fffafa; }
			.kgm-action.danger:hover { color: #8e2222; border-color: #dfaaaa; background: #fff0f0; }
			.kgm-segment button:focus-visible, .kgm-sides button:focus-visible, .kgm-action:focus-visible { outline: 2px solid #18765a; outline-offset: 2px; }
			.kgm-action:disabled { opacity: .55; cursor: not-allowed; box-shadow: none; }
			.kgm-entry-buttons, .kgm-row-actions { display: flex; gap: 6px; align-items: center; }
			.kgm-entry-buttons { width: 100%; flex-wrap: wrap; }
			#kgm-add-entry { width: 100%; min-height: 48px; flex-direction: column; gap: 3px; padding: 5px 7px; }
			#kgm-cancel-edit { width: 100%; }
			.kgm-row-actions { flex-wrap: nowrap; }
			.kgm-row-actions .kgm-action { min-height: 30px; padding: 5px 8px; font-size: 11px; }
			.kgm-actions { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
			.kgm-footer-buttons { display: flex; align-items: center; gap: 8px; }
			.kgm-footer-buttons .kgm-action { min-height: 38px; padding: 8px 12px; }
			.kgm-preview-wrap { flex: 1 0 auto; overflow: auto; background: #ffffff; }
			.kgm-preview { width: 100%; min-width: 980px; border-collapse: collapse; table-layout: fixed; }
			.kgm-preview th, .kgm-preview td { border-bottom: 1px solid #e8edf0; padding: 6px 8px; vertical-align: middle; color: #24323d; font-size: 11px; }
			.kgm-preview th { position: sticky; top: 0; z-index: 2; color: #405751; background: #edf5f2; border-bottom-color: #b9c9c3; font-weight: 800; font-size: 10px; }
			.kgm-preview .stone-row td { font-weight: 700; }
			.kgm-preview .work-row td { background: #f8fbfa; color: #405751; }
			.kgm-preview .editing-row td { background: #fff2bf; }
			.kgm-muted { color: #64748b; font-size: 12px; }
			.kgm-totals { display: flex; gap: 18px; flex-wrap: wrap; color: #173d30; font-weight: 800; }
			.kgm-tax-grid { display: grid; grid-template-columns: minmax(220px, 1fr) minmax(130px, 0.45fr) minmax(120px, 0.4fr) minmax(120px, 0.4fr) minmax(120px, 0.4fr); gap: 10px; align-items: end; }
			.kgm-tax-list { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
			.kgm-tax-pill { display: inline-flex; align-items: center; gap: 8px; border: 1px solid #d5e9df; border-radius: 4px; background: #f3faf7; padding: 5px 8px; color: #405751; font-size: 11px; }
			.kgm-tax-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
			.kgm-actions { position: sticky; bottom: 0; z-index: 4; background: #f3faf7; border-top: 1px solid #d5e9df; padding-top: 12px; padding-bottom: 12px; }
			.kgm-hidden { display: none !important; }
			@media (max-width: 1100px) {
				.kgm-fast-header, .kgm-entry-grid, .kgm-entry-grid.second, .kgm-tax-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
			}
			@media (max-width: 620px) {
				.kgm-fast-header, .kgm-entry-grid, .kgm-entry-grid.second, .kgm-tax-grid { grid-template-columns: 1fr; }
				.kgm-fast-band { padding: 10px; }
				.kgm-actions { align-items: stretch; }
				.kgm-footer-buttons { width: 100%; }
				#kgm-save { flex: 1; }
			}
		</style>
		<div class="kgm-fast-shell">
			<div class="kgm-fast-band">
				<div class="kgm-fast-header">
					<div id="kgm-customer-control"></div>
					<div id="kgm-date-control"></div>
					<div id="kgm-delivery-date-control"></div>
					<div id="kgm-cash-customer-control"></div>
					<div id="kgm-phone-control"></div>
				</div>
			</div>
			<div class="kgm-fast-band kgm-entry-band">
				<div class="kgm-entry-grid">
					<div class="kgm-field">
						<label>${__("Item")}</label>
						<select id="kgm-template">
							<option value="KOTA">Kota</option>
							<option value="KADDPA">Kaddpa</option>
							<option value="MANUAL">Manual</option>
						</select>
					</div>
					<div id="kgm-manual-item-wrap" class="kgm-hidden"></div>
					<div class="kgm-field" id="kgm-generated-wrap">
						<label>${__("Selected")}</label>
						<div class="kgm-generated" id="kgm-generated-item"><span></span></div>
					</div>
					<div class="kgm-field">
						<label>${__("Height")}</label>
						<input id="kgm-height" type="number" min="0" step="0.01" inputmode="decimal">
					</div>
					<div class="kgm-field">
						<label>${__("Width")}</label>
						<input id="kgm-width" type="number" min="0" step="0.01" inputmode="decimal">
					</div>
					<div class="kgm-field">
						<label>${__("Pcs")}</label>
						<input id="kgm-quantity" type="number" min="0" step="0.01" inputmode="decimal" value="1">
					</div>
					<div class="kgm-field">
						<label>${__("Sqft")}</label>
						<input id="kgm-sqft" type="number" min="0" step="0.01" inputmode="decimal">
					</div>
				</div>
				<div class="kgm-entry-grid second">
					<div class="kgm-field">
						<label>${__("Finish")}</label>
						<select id="kgm-finish">
							<option value="">Polish</option>
							<option value="Fine">Fine</option>
							<option value="Rough">Rough</option>
							<option value="DP">DP</option>
							<option value="Uncut">Uncut</option>
							<option value="Ledhar">Ledhar</option>
							<option value="River">River</option>
							<option value="Mirror">Mirror</option>
						</select>
					</div>
					<div class="kgm-field">
						<label>${__("Kota Type")}</label>
						<div class="kgm-segment" id="kgm-attrs">
							<button type="button" data-attr="rough">Rough</button>
							<button type="button" data-attr="raj">Raj</button>
							<button type="button" data-attr="g">G</button>
							<button type="button" data-attr="p">P</button>
							<button type="button" data-attr="j">J</button>
							<button type="button" data-attr="mirror">Mirror</button>
						</div>
					</div>
					<div class="kgm-field">
						<label>${__("Rate")}</label>
						<input id="kgm-rate" type="number" min="0" step="0.01" inputmode="decimal">
					</div>
					<div class="kgm-field">
						<label>${__("Work")}</label>
						<select id="kgm-operation">
							<option value="">None</option>
						</select>
					</div>
					<div class="kgm-field" id="kgm-sides-wrap">
						<label>${__("Sides")}</label>
						<div class="kgm-sides" id="kgm-sides">
							<button type="button" data-side="custom_top">Top</button>
							<button type="button" data-side="custom_bottom">Bottom</button>
							<button type="button" data-side="custom_left">Left</button>
							<button type="button" data-side="custom_right">Right</button>
							<button type="button" data-preset="top_bottom">Top+Bottom</button>
							<button type="button" data-preset="all">All</button>
						</div>
					</div>
					<div class="kgm-field" id="kgm-operation-rate-wrap">
						<label>${__("Work Rate")}</label>
						<input id="kgm-operation-rate" type="number" min="0" step="0.01" inputmode="decimal">
					</div>
					<div class="kgm-field">
						<label>&nbsp;</label>
						<div class="kgm-entry-buttons">
							<button class="kgm-action primary" id="kgm-add-entry" type="button" title="${__("Enter in a number field or Ctrl+Enter anywhere on this page")}">
								<span class="kgm-action-label">${__("Add Entry")}</span>
								<span class="kgm-shortcuts"><kbd>Enter</kbd><span>/</span><kbd>Ctrl+Enter</kbd></span>
							</button>
							<button class="kgm-action kgm-hidden" id="kgm-cancel-edit" type="button">${__("Cancel")}</button>
						</div>
					</div>
				</div>
				<div class="kgm-muted" id="kgm-live-summary"></div>
			</div>
			<div class="kgm-preview-wrap">
				<table class="kgm-preview">
					<thead>
						<tr>
							<th style="width: 42px;">#</th>
							<th style="width: 190px;">${__("Item")}</th>
							<th style="width: 85px;">${__("Height")}</th>
							<th style="width: 85px;">${__("Width")}</th>
							<th style="width: 75px;">${__("Pcs")}</th>
							<th style="width: 100px;">${__("Cut H")}</th>
							<th style="width: 100px;">${__("Cut W")}</th>
							<th style="width: 80px;">${__("Qty")}</th>
							<th style="width: 80px;">${__("Rate")}</th>
							<th style="width: 95px;">${__("Amount")}</th>
							<th style="width: 130px;">${__("Sides")}</th>
							<th style="width: 140px;"></th>
						</tr>
					</thead>
					<tbody id="kgm-preview-body">
						<tr><td colspan="12" class="kgm-muted">${__("No entries yet.")}</td></tr>
					</tbody>
				</table>
			</div>
			<div class="kgm-fast-band">
				<div class="kgm-tax-head">
					<div class="kgm-muted">${__("Taxes are optional.")}</div>
					<button class="kgm-action" id="kgm-toggle-tax" type="button">${__("Add Tax")}</button>
				</div>
				<div class="kgm-tax-grid kgm-hidden" id="kgm-tax-panel">
					<div id="kgm-tax-account-control"></div>
					<div class="kgm-field">
						<label>${__("Tax Type")}</label>
						<select id="kgm-tax-charge-type">
							<option value="On Net Total">On Net Total</option>
							<option value="Actual">Actual</option>
						</select>
					</div>
					<div class="kgm-field" id="kgm-tax-rate-wrap">
						<label>${__("Rate %")}</label>
						<input id="kgm-tax-rate" type="number" min="0" step="0.01" inputmode="decimal">
					</div>
					<div class="kgm-field kgm-hidden" id="kgm-tax-amount-wrap">
						<label>${__("Amount")}</label>
						<input id="kgm-tax-amount" type="number" step="0.01" inputmode="decimal">
					</div>
					<div class="kgm-field">
						<label>&nbsp;</label>
						<button class="kgm-action" id="kgm-add-tax" type="button">${__("Add Tax")}</button>
					</div>
				</div>
				<div class="kgm-tax-list" id="kgm-tax-list"></div>
			</div>
			<div class="kgm-fast-band kgm-actions">
				<div class="kgm-totals" id="kgm-totals"></div>
				<div class="kgm-footer-buttons">
					<button class="kgm-action" id="kgm-clear" type="button">${__("Clear")}</button>
					<button class="kgm-action primary" id="kgm-save" type="button"><span>${__("Save Draft")}</span><kbd>Ctrl+S</kbd></button>
				</div>
			</div>
		</div>
	`);

	const controls = {};
	controls.customer = makeControl("kgm-customer-control", {
		fieldtype: "Link",
		options: "Customer",
		label: __("Customer"),
		reqd: 1,
	});
	controls.transaction_date = makeControl("kgm-date-control", {
		fieldtype: "Date",
		label: __("Order Date"),
		reqd: 1,
	});
	controls.delivery_date = makeControl("kgm-delivery-date-control", {
		fieldtype: "Date",
		label: __("Delivery Date"),
		reqd: 1,
	});
	controls.cash_customer = makeControl("kgm-cash-customer-control", {
		fieldtype: "Data",
		label: __("Cash Name"),
	});
	controls.phone = makeControl("kgm-phone-control", {
		fieldtype: "Data",
		label: __("Phone"),
	});
	controls.manual_item = makeControl("kgm-manual-item-wrap", {
		fieldtype: "Link",
		options: "Item",
		label: __("Manual Item"),
		onchange: function() {
			refreshGeneratedItem();
			focusEntryHeight();
		},
	});
	controls.tax_account = makeControl("kgm-tax-account-control", {
		fieldtype: "Link",
		options: "Account",
		label: __("Tax Account"),
		get_query: function() {
			return {
				filters: {
					is_group: 0,
				},
			};
		},
	});

	page.add_inner_button(__("Open Sales Orders"), function() {
		frappe.set_route("List", "Sales Order");
	});

	page.add_inner_button(__("Open Last Draft"), function() {
		if (state.lastSalesOrder) {
			frappe.set_route("Form", "Sales Order", state.lastSalesOrder);
		}
	});

	loadDefaults();
	loadWorkItems();
	bindEvents();
	refreshGeneratedItem();
	updateOperationControls({ focusAddEntry: false });
	updateTaxControls();
	renderPreview();
	renderTaxes();

	function makeControl(parentId, df) {
		const control = frappe.ui.form.make_control({
			parent: $main.find(`#${parentId}`),
			df,
			render_input: true,
		});
		control.refresh();
		return control;
	}

	function bindEvents() {
		$main.on("change", "#kgm-template, #kgm-finish", refreshGeneratedItem);
		$main.on("focusout", "#kgm-manual-item-wrap input", function() {
			setTimeout(() => {
				if ($main.find("#kgm-template").val() !== "MANUAL" || $main.find("#kgm-rate").val()) return;
				if (controls.manual_item.get_value()) refreshGeneratedItem(true);
			}, 0);
		});
		$main.on("input", "#kgm-height, #kgm-width, #kgm-quantity", refreshGeneratedItem);
		$main.on("input", "#kgm-sqft", function() {
			state.sqftManual = Boolean($(this).val());
		});
		$main.on("change", "#kgm-operation", function() {
			updateOperationControls({ focusAddEntry: !$(this).val() });
			refreshOperationRate();
		});
		$main.on("change", "#kgm-finish", function() {
			if ($(this).val()) {
				$main.find("#kgm-attrs button").removeClass("active");
			}
		});
		$main.on("click", "#kgm-attrs button", function() {
			const attr = $(this).data("attr");
			if (attr === "g" || attr === "p" || attr === "j") {
				$main.find('#kgm-attrs button[data-attr="raj"]').addClass("active");
			}
			if (attr === "p") $main.find('#kgm-attrs button[data-attr="j"]').removeClass("active");
			if (attr === "j") $main.find('#kgm-attrs button[data-attr="p"]').removeClass("active");
			$(this).toggleClass("active");
			if ($(this).hasClass("active")) {
				$main.find("#kgm-finish").val("");
			}
			refreshGeneratedItem();
		});
		$main.on("click", "#kgm-sides button[data-side]", function() {
			$(this).toggleClass("active");
			scheduleLivePreview();
		});
		$main.on("click", "#kgm-sides button[data-preset]", function() {
			const preset = $(this).data("preset");
			if (preset === "top_bottom") {
				setSides({ custom_top: 1, custom_bottom: 1, custom_left: 0, custom_right: 0 });
			}
			if (preset === "all") {
				setSides({ custom_top: 1, custom_bottom: 1, custom_left: 1, custom_right: 1 });
			}
			scheduleLivePreview();
		});
		$main.on("click", "#kgm-add-entry", addEntry);
		$main.on("click", "#kgm-cancel-edit", function() {
			state.editingIndex = null;
			resetEntryInputs();
		});
		$main.on("click", ".kgm-edit-entry", function() {
			loadEntryForEdit(Number($(this).data("index")));
		});
		$main.on("click", ".kgm-remove-entry", function() {
			const index = Number($(this).data("index"));
			state.entries.splice(index, 1);
			if (state.editingIndex === index) {
				state.editingIndex = null;
				resetEntryInputs();
			} else if (state.editingIndex > index) {
				state.editingIndex -= 1;
				updateEntryMode();
			}
			renderPreview();
		});
		$main.on("click", "#kgm-clear", function() {
			state.entries = [];
			state.taxes = [];
			state.editingIndex = null;
			resetEntryInputs();
			setTaxPanelOpen(false);
			renderPreview();
			renderTaxes();
		});
		$main.on("change", "#kgm-tax-charge-type", updateTaxControls);
		$main.on("click", "#kgm-toggle-tax", function() {
			setTaxPanelOpen($main.find("#kgm-tax-panel").hasClass("kgm-hidden"));
		});
		$main.on("click", "#kgm-add-tax", addTax);
		$main.on("click", ".kgm-remove-tax", function() {
			state.taxes.splice(Number($(this).data("index")), 1);
			renderTaxes();
		});
		$main.on("click", "#kgm-save", saveDraft);
		$main.on("keydown", "#kgm-height, #kgm-width, #kgm-quantity, #kgm-sqft, #kgm-rate, #kgm-operation-rate", function(event) {
			if (event.ctrlKey || event.metaKey) return;
			if (event.key !== "Enter") return;
			event.preventDefault();
			addEntry();
		});
		$main.on("keydown", function(event) {
			if (!(event.ctrlKey || event.metaKey) || event.key !== "Enter") return;
			if ($(event.target).closest("#kgm-tax-panel").length) return;
			event.preventDefault();
			addEntry();
		});
		const pageConfig = frappe.pages["sales-order-fast-entry"];
		if (pageConfig.saveShortcut) {
			document.removeEventListener("keydown", pageConfig.saveShortcut, true);
		}
		pageConfig.saveShortcut = function(event) {
			if (
				frappe.get_route()[0] !== "sales-order-fast-entry" ||
				!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey ||
				event.key.toLowerCase() !== "s"
			) return;
			event.preventDefault();
			event.stopPropagation();
			saveDraft();
		};
		document.addEventListener("keydown", pageConfig.saveShortcut, true);
	}

	function loadWorkItems() {
		frappe.call({
			method: methodRoot + "get_work_items",
			callback: function(r) {
				state.workItems = r.message || [];
				renderWorkOptions();
			},
		});
	}

	function renderWorkOptions() {
		const $operation = $main.find("#kgm-operation");
		const current = $operation.val();
		const stoneItemCode = (getStoneSelection().item_code || "").toLowerCase();
		const isKotaOrKaddpa = stoneItemCode.includes("kota") || stoneItemCode.includes("kaddpa");
		const filterMode = isKotaOrKaddpa ? "plain_mould" : "mouldg";
		const filteredItems = state.workItems.filter(item => {
			const text = `${item.item_code || ""} ${item.item_name || ""}`;
			return isKotaOrKaddpa
				? /\bmould\b/i.test(text)
				: /mouldg/i.test(text);
		});
		const optionsKey = `${filterMode}:${filteredItems.map(item => item.item_code).join("\n")}`;
		const currentIsValid = current && filteredItems.some(item => item.item_code === current);

		if (state.workOptionsKey === optionsKey && (!current || currentIsValid)) {
			updateOperationControls({ focusAddEntry: false });
			return;
		}
		state.workOptionsKey = optionsKey;

		$operation.html(`<option value="">${__("None")}</option>`);
		for (const item of filteredItems) {
			const label = item.item_name && item.item_name !== item.item_code
				? `${item.item_code} - ${item.item_name}`
				: item.item_code;
			$operation.append(
				$("<option>", {
					value: item.item_code,
					text: label,
					"data-rate": item.rate || 0,
				})
			);
		}

		if (current && filteredItems.some(item => item.item_code === current)) {
			$operation.val(current);
		} else {
			$operation.val("");
			state.lastOperationItemCode = "";
		}
		updateOperationControls({ focusAddEntry: false });
	}

	function loadDefaults() {
		frappe.call({
			method: methodRoot + "get_defaults",
			callback: function(r) {
				const defaults = r.message || {};
				controls.transaction_date.set_value(defaults.transaction_date || frappe.datetime.get_today());
				controls.delivery_date.set_value(defaults.delivery_date || defaults.transaction_date || frappe.datetime.get_today());
			},
		});
	}

	function getPositiveFloat(selector, fallback) {
		const value = parseFloat($main.find(selector).val());
		return value > 0 ? value : (fallback || 0);
	}

	function getManualBillRate(itemCode, work = false) {
		if ($main.find("#kgm-template").val() !== "MANUAL" || !itemCode) return null;
		for (let index = state.entries.length - 1; index >= 0; index--) {
			if (index === state.editingIndex) continue;
			const entry = state.entries[index].input;
			if (entry.form_state?.template !== "MANUAL") continue;
			const row = work ? (entry.operations || [])[0] : entry.stone;
			if (row?.item_code === itemCode && Number(row.rate) > 0) return Number(row.rate);
		}
		return null;
	}

	function syncManualBillRates(changedEntry) {
		if (changedEntry.input.form_state?.template !== "MANUAL") return;
		const stone = changedEntry.input.stone;
		const work = (changedEntry.input.operations || [])[0];
		for (const entry of state.entries) {
			if (entry.input.form_state?.template !== "MANUAL") continue;
			if (stone.rate > 0 && entry.input.stone.item_code === stone.item_code) {
				entry.input.stone.rate = stone.rate;
				entry.rows[0].rate = stone.rate;
				entry.rows[0].amount = Math.round((Number(entry.rows[0].qty) || 0) * stone.rate * 100) / 100;
			}
			const entryWork = (entry.input.operations || [])[0];
			if (work?.rate > 0 && entryWork?.item_code === work.item_code && entry.rows[1]) {
				entryWork.rate = work.rate;
				entry.rows[1].rate = work.rate;
				entry.rows[1].amount = Math.round((Number(entry.rows[1].qty) || 0) * work.rate * 100) / 100;
			}
		}
	}

	function formatNumber(value) {
		const number = parseFloat(value) || 0;
		if (Math.abs(number - Math.round(number)) < 0.0001) return String(Math.round(number));
		return String(number).replace(/0+$/, "").replace(/\.$/, "");
	}

	function calculateSegmentsSpecial(value) {
		const val = Math.max(0, parseFloat(value) || 0);
		if (val === 0) return 0;
		return val % 6 === 0 ? val + 6 : Math.ceil(val / 6) * 6;
	}

	function calculateWidthSegmentsHeightRule(value) {
		const val = Math.max(0, parseFloat(value) || 0);
		if (val === 0) return 0;
		if (val > 1 && val < 6) return 6;
		if (val >= 6 && val < 12) return 12;
		if (val >= 12 && val < 15) return 30;
		if (val === 15) return 18;
		if (val > 15 && val < 18) return 18;
		if (val >= 18) return calculateSegmentsSpecial(val);
		return 0;
	}

	function calculateWidthSegmentsStandard(value) {
		const val = Math.max(0, parseFloat(value) || 0);
		if (val === 0) return 0;
		if (val > 1 && val < 6) return 24;
		if (val >= 6 && val < 12) return 24;
		if (val >= 12 && val < 15) return 30;
		if (val === 15) return 24;
		if (val > 15 && val < 18) return 24;
		if (val >= 18) return calculateSegmentsSpecial(val);
		return 0;
	}

	function getAttrValue(attr) {
		return $main.find(`#kgm-attrs button[data-attr="${attr}"]`).hasClass("active");
	}

	function isJobWorkItem(itemCode) {
		return String(itemCode || "").toLowerCase().includes("job work");
	}

	function selectedItemNeedsSides() {
		return isJobWorkItem(getStoneSelection().item_code);
	}

	function calculateCutWidth(template, height, width) {
		let calculatedWidth = 0;
		if (template === "KADDPA") {
			calculatedWidth = calculateSegmentsSpecial(width);
			if (width > 0 && calculatedWidth < 24) calculatedWidth = 24;
		} else if (getAttrValue("raj")) {
			calculatedWidth = calculateSegmentsSpecial(width);
		} else if (height < 24) {
			calculatedWidth = calculateWidthSegmentsHeightRule(width);
		} else {
			calculatedWidth = calculateWidthSegmentsStandard(width);
			if (calculatedWidth < 24) calculatedWidth = 24;
		}
		return calculatedWidth;
	}

	function getStoneSelection() {
		const template = $main.find("#kgm-template").val();
		const height = getPositiveFloat("#kgm-height");
		const width = getPositiveFloat("#kgm-width");
		const quantity = getPositiveFloat("#kgm-quantity", 1);
		const finish = $main.find("#kgm-finish").val();

		if (template === "MANUAL") {
			return {
				item_code: controls.manual_item.get_value(),
				custom_height: height,
				custom_width: width,
				custom_quantity: quantity,
				custom_cut_from_height: 0,
				custom_cut_from_width: 0,
			};
		}

		const cutHeight = calculateSegmentsSpecial(height);
		const cutWidth = calculateCutWidth(template, height, width);
		let dimensions = `${formatNumber(cutHeight)}x${formatNumber(cutWidth)}`;
		if (getAttrValue("raj") && !getAttrValue("g")) {
			dimensions = `${formatNumber(height)}x${formatNumber(width)}`;
		}

		let itemCode = `${template} ${dimensions}`;
		const polishSuffixMap = {
			Fine: " FIN",
			Rough: " RUF",
			DP: " DP",
			Uncut: " UNC",
			Ledhar: " LDR",
			River: " RIV",
			Mirror: " MIR",
		};
		if (finish && polishSuffixMap[finish]) {
			itemCode += polishSuffixMap[finish];
		} else {
			if (getAttrValue("raj")) itemCode += " RAJ";
			if (getAttrValue("g")) itemCode += " G";
			if (getAttrValue("rough")) itemCode += " RUF";
			if (getAttrValue("p")) itemCode += " P";
			else if (getAttrValue("j")) itemCode += " J";
			if (getAttrValue("mirror")) itemCode += " MIR";
		}

		return {
			item_code: itemCode,
			custom_height: height,
			custom_width: width,
			custom_quantity: quantity,
			custom_cut_from_height: cutHeight,
			custom_cut_from_width: cutWidth,
		};
	}

	function refreshGeneratedItem(forceRate = false) {
		const template = $main.find("#kgm-template").val();
		$main.find("#kgm-manual-item-wrap").toggleClass("kgm-hidden", template !== "MANUAL");
		$main.find("#kgm-generated-wrap").toggleClass("kgm-hidden", template === "MANUAL");
		$main.find("#kgm-attrs").toggleClass("kgm-hidden", template === "MANUAL");

		const selection = getStoneSelection();
		const itemCode = selection.item_code || "";
		const $generated = $main.find("#kgm-generated-item");
		$generated.find("span").text(itemCode || __("Waiting"));
		$generated.removeClass("missing");
		renderWorkOptions();
		scheduleLivePreview();

		if (itemCode && (itemCode !== state.lastGeneratedItemCode || forceRate === true)) {
			state.lastGeneratedItemCode = itemCode;
			const requestId = ++state.itemDetailsRequest;
			const billRate = getManualBillRate(itemCode);
			$main.find("#kgm-rate").val(billRate === null ? "" : formatNumber(billRate));
			frappe.call({
				method: methodRoot + "get_item_details",
				args: { item_code: itemCode },
				callback: function(r) {
					if (requestId !== state.itemDetailsRequest) return;
					const details = r.message || {};
					if (getStoneSelection().item_code !== itemCode) return;
					if (details.exists === false) {
						$generated.addClass("missing");
						return;
					}
					if (getStoneSelection().item_code === itemCode && !$main.find("#kgm-rate").val()) {
						const currentBillRate = getManualBillRate(itemCode);
						$main.find("#kgm-rate").val(currentBillRate === null ? (details.rate || "") : formatNumber(currentBillRate));
					}
				},
			});
		}
	}

	function scheduleLivePreview() {
		clearTimeout(state.livePreviewTimer);
		state.livePreviewTimer = setTimeout(refreshLivePreview, 250);
	}

	function refreshLivePreview() {
		const stone = getStoneSelection();
		const $summary = $main.find("#kgm-live-summary");
		const manualItem = $main.find("#kgm-template").val() === "MANUAL";
		const hasManualSqft = state.sqftManual && getPositiveFloat("#kgm-sqft") > 0;
		if (!stone.item_code || !stone.custom_quantity || ((!stone.custom_height || !stone.custom_width) && !(manualItem && hasManualSqft))) {
			$summary.text("");
			return;
		}

		const previewStone = Object.assign({}, stone, { rate: getPositiveFloat("#kgm-rate") });
		if (state.sqftManual) {
			previewStone.qty = getPositiveFloat("#kgm-sqft");
			previewStone.manual_qty = 1;
		}
		if (isJobWorkItem(previewStone.item_code)) {
			Object.assign(previewStone, getSides());
		}
		const requestId = ++state.livePreviewRequest;
		$summary.text(__("Calculating..."));
		frappe.call({
			method: methodRoot + "preview_entry",
			args: {
				quiet_missing: 1,
				entry: {
					stone: previewStone,
					operations: [],
				},
			},
			callback: function(r) {
				if (requestId !== state.livePreviewRequest) return;
				const missingItems = (r.message && r.message.missing_items) || [];
				if (missingItems.length) {
					$main.find("#kgm-generated-item").addClass("missing");
					$summary.text(__("Item not found."));
					return;
				}
				const row = r.message && r.message.rows && r.message.rows[0];
				if (!row) {
					$summary.text("");
					return;
				}
				if (!state.sqftManual) {
					$main.find("#kgm-sqft").val(formatNumber(row.qty));
				}
				$summary.text(
					`${__("Qty")}: ${formatNumber(row.qty)} | ${__("Cut")}: ${formatNumber(row.custom_cut_from_height)} x ${formatNumber(row.custom_cut_from_width)}`
				);
			},
			error: function() {
				if (requestId === state.livePreviewRequest) $summary.text("");
			},
		});
	}

	function setSides(values) {
		for (const fieldname of ["custom_top", "custom_bottom", "custom_left", "custom_right"]) {
			$main.find(`#kgm-sides button[data-side="${fieldname}"]`).toggleClass("active", Boolean(values[fieldname]));
		}
	}

	function getSides() {
		const values = {};
		for (const fieldname of ["custom_top", "custom_bottom", "custom_left", "custom_right"]) {
			values[fieldname] = $main.find(`#kgm-sides button[data-side="${fieldname}"]`).hasClass("active") ? 1 : 0;
		}
		return values;
	}

	function hasAnySideSelected() {
		return Object.values(getSides()).some(Boolean);
	}

	function applyDefaultSidesForOperation() {
		const operation = $main.find("#kgm-operation").val();
		if (!operation) return;
		if (operation.includes("Job Work")) {
			setSides({ custom_top: 1, custom_bottom: 1, custom_left: 1, custom_right: 1 });
		} else if (operation.includes("Phal") || operation.includes("MouldG")) {
			setSides({ custom_top: 1, custom_bottom: 1, custom_left: 0, custom_right: 0 });
		} else {
			setSides({ custom_top: 1, custom_bottom: 0, custom_left: 1, custom_right: 0 });
		}
	}

	function updateOperationControls({ focusAddEntry = false } = {}) {
		const operation = $main.find("#kgm-operation").val();
		const hasOperation = Boolean(operation);
		const mainNeedsSides = selectedItemNeedsSides();
		const sideMode = hasOperation ? `operation:${operation}` : (mainNeedsSides ? "main-job-work" : "");
		$main.find("#kgm-sides-wrap").toggleClass("kgm-hidden", !hasOperation && !mainNeedsSides);
		$main.find("#kgm-operation-rate-wrap").toggleClass("kgm-hidden", !hasOperation);

		if (hasOperation) {
			if (state.lastSideMode !== sideMode || !hasAnySideSelected()) {
				applyDefaultSidesForOperation();
			}
			state.lastSideMode = sideMode;
			return;
		}

		$main.find("#kgm-operation-rate").val("");
		if (mainNeedsSides) {
			if (state.lastSideMode !== sideMode || !hasAnySideSelected()) {
				setSides({ custom_top: 1, custom_bottom: 1, custom_left: 1, custom_right: 1 });
			}
			state.lastSideMode = sideMode;
			return;
		}

		setSides({ custom_top: 0, custom_bottom: 0, custom_left: 0, custom_right: 0 });
		state.lastSideMode = "";
		if (focusAddEntry) {
			setTimeout(() => {
				$main.find("#kgm-add-entry").trigger("focus");
			}, 0);
		}
	}

	function refreshOperationRate() {
		const itemCode = $main.find("#kgm-operation").val();
		if (!itemCode) {
			state.lastOperationItemCode = "";
			return;
		}
		if (itemCode === state.lastOperationItemCode) return;
		state.lastOperationItemCode = itemCode;
		const billRate = getManualBillRate(itemCode, true);
		$main.find("#kgm-operation-rate").val(billRate === null ? "" : formatNumber(billRate));
		if (billRate !== null) return;
		const optionRate = parseFloat($main.find("#kgm-operation option:selected").data("rate")) || 0;
		if (optionRate) {
			$main.find("#kgm-operation-rate").val(optionRate);
			return;
		}
		frappe.call({
			method: methodRoot + "get_item_details",
			args: { item_code: itemCode },
			callback: function(r) {
				const details = r.message || {};
				if (details.exists === false) return;
				if ($main.find("#kgm-operation").val() === itemCode && !$main.find("#kgm-operation-rate").val()) {
					const currentBillRate = getManualBillRate(itemCode, true);
					$main.find("#kgm-operation-rate").val(currentBillRate === null ? (details.rate || "") : formatNumber(currentBillRate));
				}
			},
		});
	}

	function getFormState() {
		return {
			template: $main.find("#kgm-template").val(),
			manual_item: controls.manual_item.get_value(),
			finish: $main.find("#kgm-finish").val(),
			attrs: $main.find("#kgm-attrs button.active").map(function() {
				return $(this).data("attr");
			}).get(),
		};
	}

	function buildEntryPayload() {
		const stone = getStoneSelection();
		const manualItem = $main.find("#kgm-template").val() === "MANUAL";
		if (state.sqftManual) {
			stone.qty = getPositiveFloat("#kgm-sqft");
			stone.manual_qty = 1;
		}
		stone.rate = getPositiveFloat("#kgm-rate");
		if (!stone.item_code) {
			frappe.msgprint(__("Select an item."));
			return null;
		}
		if (!stone.custom_quantity || ((!stone.custom_height || !stone.custom_width) && !(manualItem && state.sqftManual && stone.qty > 0))) {
			frappe.msgprint(manualItem ? __("Enter pcs and Sqft when height or width is blank.") : __("Height, width, and pcs are required."));
			return null;
		}
		if (isJobWorkItem(stone.item_code)) {
			const sides = getSides();
			if (!Object.values(sides).some(Boolean)) {
				frappe.msgprint(__("Select at least one side."));
				return null;
			}
			Object.assign(stone, sides);
		}

		const operationItem = $main.find("#kgm-operation").val();
		const operations = [];
		if (operationItem) {
			const sides = getSides();
			if (!Object.values(sides).some(Boolean)) {
				frappe.msgprint(__("Select at least one side."));
				return null;
			}
			operations.push(Object.assign({
				item_code: operationItem,
				custom_height: stone.custom_height,
				custom_width: stone.custom_width,
				custom_quantity: stone.custom_quantity,
				rate: getPositiveFloat("#kgm-operation-rate"),
			}, sides));
		}

		return { stone, operations, form_state: getFormState() };
	}

	function addEntry() {
		if (state.isAddingEntry) return;
		const entry = buildEntryPayload();
		if (!entry) return;

		state.isAddingEntry = true;
		let entryWasSaved = false;
		const $button = $main.find("#kgm-add-entry");
		$button.prop("disabled", true);
		frappe.call({
			method: methodRoot + "preview_entry",
			args: { entry },
			callback: function(r) {
				const rows = (r.message && r.message.rows) || [];
				const savedEntry = { input: entry, rows };
				if (Number.isInteger(state.editingIndex) && state.entries[state.editingIndex]) {
					state.entries[state.editingIndex] = savedEntry;
				} else {
					state.entries.push(savedEntry);
				}
				syncManualBillRates(savedEntry);
				renderPreview();
				state.editingIndex = null;
				resetEntryInputs({ focusItem: false });
				entryWasSaved = true;
			},
			always: function() {
				state.isAddingEntry = false;
				$button.prop("disabled", false);
				if (entryWasSaved) {
					focusEntryItem();
				}
			},
		});
	}

	function updateEntryMode() {
		const isEditing = Number.isInteger(state.editingIndex) && state.entries[state.editingIndex];
		$main.find("#kgm-add-entry .kgm-action-label").text(isEditing ? __("Update Entry") : __("Add Entry"));
		$main.find("#kgm-cancel-edit").toggleClass("kgm-hidden", !isEditing);
	}

	function focusEntryHeight() {
		setTimeout(() => {
			$main.find("#kgm-height").trigger("focus").trigger("select");
		}, 0);
	}

	function focusEntryItem() {
		setTimeout(() => {
			if ($main.find("#kgm-template").val() === "MANUAL") {
				if (controls.manual_item.set_focus) {
					controls.manual_item.set_focus();
				}
				const $input = controls.manual_item.$input || controls.manual_item.$wrapper.find("input:visible").first();
				$input.trigger("focus").trigger("select");
				return;
			}
			$main.find("#kgm-template").trigger("focus").trigger("select");
		}, 80);
	}

	function resetEntryInputs({ focusItem = true, resetItem = false } = {}) {
		if (resetItem) {
			$main.find("#kgm-template").val("KOTA");
			controls.manual_item.set_value("");
		}
		$main.find("#kgm-height").val("");
		$main.find("#kgm-width").val("");
		$main.find("#kgm-quantity").val("1");
		$main.find("#kgm-sqft").val("");
		$main.find("#kgm-rate").val("");
		$main.find("#kgm-finish").val("");
		$main.find("#kgm-operation").val("");
		$main.find("#kgm-operation-rate").val("");
		$main.find("#kgm-attrs button, #kgm-sides button").removeClass("active");
		state.itemDetailsRequest += 1;
		state.lastGeneratedItemCode = getStoneSelection().item_code || "";
		state.lastOperationItemCode = "";
		state.sqftManual = false;
		clearTimeout(state.livePreviewTimer);
		state.livePreviewRequest += 1;
		$main.find("#kgm-live-summary").text("");
		refreshGeneratedItem();
		updateOperationControls({ focusAddEntry: false });
		updateEntryMode();
		if (focusItem) {
			focusEntryItem();
		}
	}

	function inferTemplateFromItem(itemCode) {
		const upper = String(itemCode || "").toUpperCase();
		if (upper.startsWith("KADDPA ")) return "KADDPA";
		if (upper.startsWith("KOTA ")) return "KOTA";
		return "MANUAL";
	}

	function setActiveAttrs(attrs) {
		$main.find("#kgm-attrs button").removeClass("active");
		for (const attr of attrs || []) {
			$main.find(`#kgm-attrs button[data-attr="${attr}"]`).addClass("active");
		}
	}

	function loadEntryInputs(entry) {
		const stone = Object.assign({}, entry.stone || {});
		const operation = Object.assign({}, (entry.operations || [])[0] || {});
		const formState = entry.form_state || {};
		const template = formState.template || inferTemplateFromItem(stone.item_code);

		$main.find("#kgm-template").val(template);
		controls.manual_item.set_value(template === "MANUAL" ? (formState.manual_item || stone.item_code || "") : "");
		$main.find("#kgm-height").val(formatNumber(stone.custom_height));
		$main.find("#kgm-width").val(formatNumber(stone.custom_width));
		$main.find("#kgm-quantity").val(formatNumber(stone.custom_quantity || 1));
		$main.find("#kgm-sqft").val(stone.qty ? formatNumber(stone.qty) : "");
		state.sqftManual = Boolean(stone.manual_qty);
		$main.find("#kgm-finish").val(formState.finish || "");
		setActiveAttrs(formState.attrs || []);
		state.lastGeneratedItemCode = "";
		refreshGeneratedItem();
		$main.find("#kgm-rate").val(stone.rate ? formatNumber(stone.rate) : "");

		$main.find("#kgm-operation").val(operation.item_code || "");
		$main.find("#kgm-operation-rate").val(operation.rate ? formatNumber(operation.rate) : "");
		state.lastOperationItemCode = operation.item_code || "";
		updateOperationControls({ focusAddEntry: false });
		setSides(operation.item_code ? operation : { custom_top: 0, custom_bottom: 0, custom_left: 0, custom_right: 0 });
	}

	function loadEntryForEdit(index) {
		const entry = state.entries[index];
		if (!entry || state.isAddingEntry) return;
		state.editingIndex = index;
		loadEntryInputs(entry.input);
		updateEntryMode();
		renderPreview();
		focusEntryHeight();
	}

	function sideLabel(row) {
		const sides = [];
		if (row.custom_top) sides.push("Top");
		if (row.custom_bottom) sides.push("Bottom");
		if (row.custom_left) sides.push("Left");
		if (row.custom_right) sides.push("Right");
		return sides.join(", ");
	}

	function rowHtml(row, entryIndex, rowIndex) {
		const isStone = rowIndex === 0;
		const isEditing = entryIndex === state.editingIndex;
		return `
			<tr class="${isStone ? "stone-row" : "work-row"} ${isEditing ? "editing-row" : ""}">
				<td>${isStone ? entryIndex + 1 : ""}</td>
				<td>${frappe.utils.escape_html(row.item_code || "")}</td>
				<td>${formatNumber(row.custom_height)}</td>
				<td>${formatNumber(row.custom_width)}</td>
				<td>${formatNumber(row.custom_quantity)}</td>
				<td>${formatNumber(row.custom_cut_from_height)}</td>
				<td>${formatNumber(row.custom_cut_from_width)}</td>
				<td>${formatNumber(row.qty)}</td>
				<td>${formatNumber(row.rate)}</td>
				<td>${formatNumber(row.amount)}</td>
				<td>${frappe.utils.escape_html(sideLabel(row))}</td>
				<td>${isStone ? `
					<div class="kgm-row-actions">
						<button class="kgm-action kgm-edit-entry" type="button" data-index="${entryIndex}" ${isEditing ? "disabled" : ""}>${isEditing ? __("Editing") : __("Edit")}</button>
						<button class="kgm-action danger kgm-remove-entry" type="button" data-index="${entryIndex}">${__("Remove")}</button>
					</div>
				` : ""}</td>
			</tr>
		`;
	}

	function renderPreview() {
		const $body = $main.find("#kgm-preview-body");
		if (!state.entries.length) {
			$body.html(`<tr><td colspan="12" class="kgm-muted">${__("No entries yet.")}</td></tr>`);
			$main.find("#kgm-totals").html("");
			return;
		}

		$body.html(state.entries.map((entry, entryIndex) => {
			return entry.rows.map((row, rowIndex) => rowHtml(row, entryIndex, rowIndex)).join("");
		}).join(""));

		const totals = state.entries
			.flatMap(entry => entry.rows)
			.reduce((acc, row) => {
				acc.qty += parseFloat(row.qty) || 0;
				acc.amount += parseFloat(row.amount) || 0;
				acc.lines += 1;
				return acc;
			}, { qty: 0, amount: 0, lines: 0 });

		$main.find("#kgm-totals").html(`
			<span>${__("Lines")}: ${totals.lines}</span>
			<span>${__("Qty")}: ${formatNumber(totals.qty)}</span>
			<span>${__("Amount")}: ${formatNumber(totals.amount)}</span>
		`);
	}

	function updateTaxControls() {
		const isActual = $main.find("#kgm-tax-charge-type").val() === "Actual";
		$main.find("#kgm-tax-rate-wrap").toggleClass("kgm-hidden", isActual);
		$main.find("#kgm-tax-amount-wrap").toggleClass("kgm-hidden", !isActual);
	}

	function setTaxPanelOpen(open) {
		$main.find("#kgm-tax-panel").toggleClass("kgm-hidden", !open);
		$main.find("#kgm-toggle-tax").text(open ? __("Hide Tax") : __("Add Tax"));
	}

	function addTax() {
		const accountHead = controls.tax_account.get_value();
		const chargeType = $main.find("#kgm-tax-charge-type").val();
		const rate = getPositiveFloat("#kgm-tax-rate");
		const taxAmount = parseFloat($main.find("#kgm-tax-amount").val()) || 0;

		if (!accountHead) {
			frappe.msgprint(__("Select a tax account."));
			return;
		}
		if (chargeType === "Actual" && !taxAmount) {
			frappe.msgprint(__("Enter a tax amount."));
			return;
		}
		if (chargeType !== "Actual" && !rate) {
			frappe.msgprint(__("Enter a tax rate."));
			return;
		}

		state.taxes.push({
			account_head: accountHead,
			charge_type: chargeType,
			rate: chargeType === "Actual" ? 0 : rate,
			tax_amount: chargeType === "Actual" ? taxAmount : 0,
			description: accountHead,
		});

		controls.tax_account.set_value("");
		$main.find("#kgm-tax-rate").val("");
		$main.find("#kgm-tax-amount").val("");
		setTaxPanelOpen(true);
		renderTaxes();
	}

	function renderTaxes() {
		const $list = $main.find("#kgm-tax-list");
		if (!state.taxes.length) {
			$list.html($main.find("#kgm-tax-panel").hasClass("kgm-hidden") ? "" : `<span class="kgm-muted">${__("No taxes added.")}</span>`);
			return;
		}
		setTaxPanelOpen(true);
		$list.html(state.taxes.map((tax, index) => {
			const value = tax.charge_type === "Actual"
				? formatNumber(tax.tax_amount)
				: `${formatNumber(tax.rate)}%`;
			return `
				<span class="kgm-tax-pill">
					<span>${frappe.utils.escape_html(tax.account_head)} | ${frappe.utils.escape_html(tax.charge_type)} | ${frappe.utils.escape_html(value)}</span>
					<button class="kgm-action danger kgm-remove-tax" type="button" data-index="${index}">${__("Remove")}</button>
				</span>
			`;
		}).join(""));
	}

	function getHeaderPayload() {
		return {
			customer: controls.customer.get_value(),
			transaction_date: controls.transaction_date.get_value(),
			delivery_date: controls.delivery_date.get_value(),
			custom_cash_customer_name: controls.cash_customer.get_value(),
			custom_phone_number: controls.phone.get_value(),
		};
	}

	function saveDraft() {
		const header = getHeaderPayload();
		if (!header.customer) {
			frappe.msgprint(__("Customer is required."));
			return;
		}
		if (!state.entries.length) {
			frappe.msgprint(__("Add at least one entry."));
			return;
		}

		const $button = $main.find("#kgm-save");
		if ($button.prop("disabled")) return;
		$button.prop("disabled", true);
		frappe.call({
			method: methodRoot + "save_sales_order",
			args: {
				header,
				entries: state.entries,
				taxes: state.taxes,
			},
			freeze: true,
			freeze_message: __("Saving Sales Order"),
			callback: function(r) {
				const result = r.message || {};
				if (!result.name) return;
				state.lastSalesOrder = result.name;
				frappe.show_alert({ message: __("Saved {0}", [result.name]), indicator: "green" });
				state.entries = [];
				state.taxes = [];
				state.editingIndex = null;
				controls.customer.set_value("");
				controls.cash_customer.set_value("");
				controls.phone.set_value("");
				controls.tax_account.set_value("");
				$main.find("#kgm-tax-charge-type").val("On Net Total");
				$main.find("#kgm-tax-rate, #kgm-tax-amount").val("");
				resetEntryInputs({ focusItem: false, resetItem: true });
				updateTaxControls();
				loadDefaults();
				setTaxPanelOpen(false);
				renderPreview();
				renderTaxes();
				controls.customer.set_focus();
			},
			always: function() {
				$button.prop("disabled", false);
			},
		});
	}
};
