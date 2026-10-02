frappe.pages["ledger-book"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Ledger Book"), single_column: true });
	var method = "kgmaccount.auto_filler.page.ledger_book.ledger_book.";
	var $main = $(wrapper).find(".layout-main-section");
	var state = { ledgers: [], selected: null, visible: [], highlighted: null, reportRows: [], highlightedRow: null, openedFromPicker: false, openedVoucher: false };
	$main.html('<style>' +
		'#page-ledger-book .layout-main-section{padding:0}#page-ledger-book .layout-main{margin:0}.kgm-ledger{height:calc(100vh - 155px);min-height:520px;color:#24323d}.kgm-ledger-card{height:100%;display:flex;flex-direction:column;overflow:hidden;background:#fff;border:1px solid #d8e1e8;border-radius:8px}.kgm-ledger-head{display:flex;justify-content:space-between;gap:16px;padding:12px 16px;background:#f3faf7;border-bottom:1px solid #d5e9df}.kgm-ledger-head h2{margin:0;color:#173d30;font-size:18px}.kgm-ledger-head p{margin:2px 0 0;color:#61716d;font-size:12px}.kgm-ledger-actions{display:flex;flex-wrap:wrap;gap:6px;align-content:start}.kgm-picker,.kgm-report{flex:1;min-height:0}.kgm-picker{display:flex;flex-direction:column}.kgm-picker-controls{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:12px;padding:12px 16px;border-bottom:1px solid #e4eaee}.kgm-search label,.kgm-company label,.kgm-date label{display:block;margin-bottom:3px;color:#52616f;font-size:11px;font-weight:700}.kgm-search input{width:100%;min-height:34px;padding:6px 9px;border:1px solid #bdcbd5;border-radius:5px}.kgm-company .frappe-control,.kgm-date .frappe-control{margin:0}.kgm-picker-list-head{padding:9px 16px;border-bottom:1px solid #dce5e9;color:#405751;font-size:12px;font-weight:700}.kgm-picker-list{flex:1;min-height:0;overflow:auto;padding:7px 10px 12px;display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));align-content:start;gap:5px}.kgm-ledger-option{min-width:0;padding:7px 9px;border:1px solid #e2e9ed;border-radius:5px;cursor:pointer;background:#fff;display:flex;justify-content:space-between;gap:8px}.kgm-ledger-option:hover,.kgm-ledger-option.active{background:#e8f5ef;border-color:#55a97d;box-shadow:inset 3px 0 #228b59}.kgm-ledger-option span{min-width:0}.kgm-ledger-option strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#24323d;font-size:12px}.kgm-ledger-option small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#667782;font-size:10px}.kgm-report{display:none;flex-direction:column}.kgm-report-toolbar{display:flex;justify-content:space-between;gap:12px;padding:9px 14px;border-bottom:1px solid #e4eaee}.kgm-report-back{align-self:start}.kgm-report-account{min-width:0;flex:1}.kgm-report-account h3{margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:16px}.kgm-report-account small{color:#667782;font-size:11px}.kgm-report-filters{display:flex;align-items:end;gap:7px}.kgm-date{width:130px}.kgm-run{margin-bottom:1px;white-space:nowrap}#kgm-ledger-output{flex:1;min-height:0;overflow:auto}.kgm-ledger-title{padding:8px 14px 5px;display:flex;justify-content:space-between;gap:12px;font-size:12px}.kgm-ledger-period{color:#65757e;font-size:11px}.kgm-ledger-summary{margin:0 14px 8px;display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #dce5e9;border-radius:4px;overflow:hidden}.kgm-ledger-summary div{padding:5px 8px;border-right:1px solid #dce5e9}.kgm-ledger-summary div:last-child{border:0}.kgm-ledger-summary small{display:block;color:#62727c;font-size:10px}.kgm-ledger-summary strong{color:#173d30;font-size:13px}.kgm-ledger-table-wrap{overflow:auto;border-top:1px solid #dce5e9}.kgm-ledger-table{min-width:720px;width:100%;border-collapse:collapse}.kgm-ledger-table th{padding:6px 8px;background:#edf5f2;text-align:left;color:#405751;font-size:11px}.kgm-ledger-table td{padding:5px 8px;border-top:1px solid #e8edf0;font-size:12px;line-height:1.25}.kgm-ledger-table .num{text-align:right;font-variant-numeric:tabular-nums}.kgm-ledger-voucher{color:#18765a;cursor:pointer;font-weight:600}.kgm-ledger-empty{padding:24px 18px;color:#64748b;text-align:center;font-size:12px}@media(max-width:820px){.kgm-ledger{height:auto;min-height:0}.kgm-ledger-card{height:auto}.kgm-ledger-head,.kgm-report-toolbar{display:block}.kgm-ledger-actions{margin-top:10px}.kgm-picker-controls{grid-template-columns:1fr}.kgm-picker-list{max-height:420px;grid-template-columns:1fr}.kgm-report-filters{margin-top:12px;flex-wrap:wrap}.kgm-date{width:calc(50% - 5px)}#kgm-ledger-output{overflow:visible}.kgm-ledger-summary{grid-template-columns:1fr 1fr}.kgm-ledger-summary div:nth-child(2){border-right:0}.kgm-ledger-summary div:nth-child(-n+2){border-bottom:1px solid #dce5e9}}' +
		'</style><style>' +
		'#page-ledger-book .page-head{display:none}#page-ledger-book .kgm-ledger{height:calc(100vh - 92px)}.kgm-ledger-head{padding:5px 10px}.kgm-ledger-head h2{font-size:13px}.kgm-ledger-head p{margin:1px 0 0;font-size:10px}.kgm-ledger-actions .btn{padding:3px 7px;font-size:10px}.kgm-picker-controls{padding:6px 10px}.kgm-picker-list-head{padding:5px 10px}.kgm-picker-list{display:block;padding:0;grid-template-columns:none}.kgm-ledger-option{height:22px;padding:2px 10px;border:0;border-bottom:1px solid #edf1f3;border-radius:0;align-items:center}.kgm-ledger-option strong,.kgm-ledger-option small{display:inline;font-size:11px;line-height:16px}.kgm-ledger-option span{display:flex;gap:8px}.kgm-ledger-option span small{color:#7a8990}.kgm-ledger-option:hover,.kgm-ledger-option.active{box-shadow:inset 3px 0 #d99100;background:#f6c94a;border-color:#e2b63b}.kgm-report-toolbar{position:relative;z-index:4;min-height:34px;padding:4px 8px;background:#fff;border-bottom:1px solid #9eb7ad;align-items:center}.kgm-report-back{padding:3px 7px;font-size:10px}.kgm-report-account h3{font-size:13px}.kgm-report-account small{font-size:9px}.kgm-period-wrap{position:relative;margin-left:auto}.kgm-period-trigger{padding:2px 7px;border:0;background:transparent;color:#2e4e43;font-size:10px;font-weight:600;white-space:nowrap}.kgm-period-trigger:hover{background:#edf5f2}.kgm-period-editor{position:absolute;right:0;top:26px;z-index:8;width:310px;padding:8px;background:#fff;border:1px solid #9eb7ad;box-shadow:0 5px 15px rgba(0,0,0,.16)}.kgm-period-fields{display:grid;grid-template-columns:1fr 1fr;gap:7px}.kgm-period-apply{width:100%;margin-top:6px;padding:3px 8px;font-size:10px}.kgm-date{width:auto}.kgm-date .control-input{min-height:28px}#kgm-ledger-output{display:flex;flex-direction:column;overflow:hidden}.kgm-ledger-table-wrap{flex:1;min-height:0;overflow:auto}.kgm-ledger-table,.kgm-tally-totals{table-layout:fixed}.kgm-ledger-table th{position:sticky;top:0;z-index:3;padding:4px 6px;background:#e7f1ed;border-bottom:1px solid #9eb7ad;font-size:10px}.kgm-ledger-table td{padding:3px 6px;font-size:10.5px;line-height:1.15}.kgm-ledger-row{cursor:pointer}.kgm-ledger-row:hover td,.kgm-ledger-row.active td{background:#f6c94a;color:#1f2d28}.kgm-ledger-row.active td:first-child{box-shadow:inset 3px 0 #d99100}.kgm-ledger-row:hover .kgm-ledger-voucher,.kgm-ledger-row.active .kgm-ledger-voucher{color:#1f2d28}.kgm-col-date{width:11%}.kgm-col-particulars{width:32%}.kgm-col-type{width:15%}.kgm-col-number{width:18%}.kgm-col-debit,.kgm-col-credit{width:12%}.kgm-tally-totals{flex:none;min-width:720px;width:100%;border-collapse:collapse;border-top:1px solid #9eb7ad;background:#fff}.kgm-tally-totals td{padding:2px 6px;font-size:10.5px}.kgm-tally-totals .label{text-align:right}.kgm-tally-totals .num{text-align:right;font-variant-numeric:tabular-nums}.kgm-tally-totals .current td{border-top:1px solid #dce5e9}.kgm-tally-totals .closing td{border-top:1px solid #9eb7ad;font-weight:700}.kgm-tally-totals .closing .label{font-size:11px}@media(max-width:820px){#page-ledger-book .kgm-ledger{height:auto}.kgm-period-editor{position:fixed;left:12px;right:12px;top:100px;width:auto}}' +
		'</style><div class="kgm-ledger"><div class="kgm-ledger-card">' +
		'<div class="kgm-ledger-head"><div><h2>' + __("General Ledger Account Book") + '</h2><p id="kgm-ledger-subtitle">' + __("Choose a general ledger account to open its voucher report.") + '</p></div><div id="kgm-ledger-actions" class="kgm-ledger-actions" style="display:none"></div></div>' +
		'<section id="kgm-ledger-picker" class="kgm-picker"><div class="kgm-picker-controls"><div class="kgm-search"><label for="kgm-ledger-search">' + __("Name of Ledger") + '</label><input id="kgm-ledger-search" autocomplete="off" placeholder="' + __("Search cash, bank, truck, debtor, expense…") + '"></div><div id="kgm-ledger-company" class="kgm-company"></div></div><div id="kgm-ledger-list-head" class="kgm-picker-list-head"></div><div id="kgm-ledger-list" class="kgm-picker-list"></div></section>' +
		'<section id="kgm-ledger-report" class="kgm-report"><div class="kgm-report-toolbar"><button id="kgm-ledger-back" class="btn btn-default kgm-report-back">← ' + __("Choose Account") + '</button><div class="kgm-report-account"><h3 id="kgm-ledger-account-name"></h3><small id="kgm-ledger-account-detail"></small></div><div class="kgm-period-wrap"><button id="kgm-ledger-period-trigger" class="kgm-period-trigger"></button><div id="kgm-ledger-period-editor" class="kgm-period-editor" style="display:none"><div class="kgm-period-fields"><div id="kgm-ledger-from" class="kgm-date"></div><div id="kgm-ledger-to" class="kgm-date"></div></div><button id="kgm-ledger-period-apply" class="btn btn-primary kgm-period-apply">' + __("Apply Period") + '</button></div></div></div><div id="kgm-ledger-output" class="kgm-ledger-empty">' + __("Loading ledger…") + '</div></section>' +
		'</div></div>');
	function control(id, df) { var c = frappe.ui.form.make_control({ parent: $main.find("#" + id), df: df, render_input: true }); c.refresh(); return c; }
	var company = control("kgm-ledger-company", { fieldtype:"Link", fieldname:"company", label:__("Company"), options:"Company", reqd:1 });
	var from = control("kgm-ledger-from", { fieldtype:"Date", fieldname:"from_date", label:__("From"), reqd:1 });
	var to = control("kgm-ledger-to", { fieldtype:"Date", fieldname:"to_date", label:__("To"), reqd:1 });
	function esc(value) { return $("<div>").text(value || "").html(); }
	function money(value, currency) { return format_currency(value || 0, currency || "INR"); }
	function renderActions(actions) {
		var labels = {"Payment Entry":__("New Receipt / Payment"),"Journal Entry":__("New Journal"),"Sales Invoice":__("New Sales Invoice"),"Purchase Invoice":__("New Purchase Invoice")};
		var html = Object.entries(actions || {}).filter(function (entry) { return entry[1]; }).map(function (entry) { return '<button class="btn btn-default btn-sm" data-new-doctype="' + entry[0] + '">' + labels[entry[0]] + '</button>'; }).join("");
		$main.find("#kgm-ledger-actions").html(html);
	}
	function renderLedgerList() {
		var query = $main.find("#kgm-ledger-search").val().toLowerCase();
		var visible = state.ledgers.filter(function (row) { return !query || (row.label + " " + row.name + " " + row.detail).toLowerCase().includes(query); });
		state.visible = visible;
		if (!visible.some(function (row) { return state.ledgers.indexOf(row) === state.highlighted; })) state.highlighted = visible.length ? state.ledgers.indexOf(visible[0]) : null;
		$main.find("#kgm-ledger-list-head").text(__("All General Ledger Accounts") + " (" + visible.length + ")");
		var html = visible.length ? visible.map(function (row) { var index = state.ledgers.indexOf(row); return '<div class="kgm-ledger-option ' + (index === state.highlighted ? "active" : "") + '" data-ledger-index="' + index + '"><span><strong>' + esc(row.label) + '</strong><small>' + esc(row.name) + '</small></span><small>' + esc(row.detail) + '</small></div>'; }).join("") : '<div class="kgm-ledger-empty">' + __("No matching accounts") + '</div>';
		$main.find("#kgm-ledger-list").html(html);
		var active = $main.find(".kgm-ledger-option.active")[0]; if (active) active.scrollIntoView({ block:"nearest" });
	}
	function showPicker() {
		$main.find("#kgm-ledger-period-editor").hide(); $main.find("#kgm-ledger-report").hide(); $main.find("#kgm-ledger-picker").css("display", "flex"); $main.find(".kgm-ledger-head").show(); $main.find("#kgm-ledger-actions").css("display", "flex");
		$main.find("#kgm-ledger-subtitle").text(__("Choose a general ledger account to open its voucher report.")); $main.find("#kgm-ledger-search").focus();
	}
	function showReport() {
		$main.find("#kgm-ledger-picker").hide(); $main.find(".kgm-ledger-head").hide(); $main.find("#kgm-ledger-report").css("display", "flex"); $main.find("#kgm-ledger-actions").hide();
		$main.find("#kgm-ledger-account-name").text(state.selected.label); $main.find("#kgm-ledger-account-detail").text(state.selected.detail + " · " + state.selected.name);
		updatePeriodLabel();
	}
	function routeAccount() {
		var route = frappe.get_route();
		if (route[0] !== "ledger-book") return;
		state.openedVoucher = false;
		var ledgerKind = ["Account", "Customer", "Supplier"].includes(route[1]) ? route[1] : "";
		var nameStart = ledgerKind ? 2 : 1;
		var accountName = route.length > nameStart ? decodeURIComponent(route.slice(nameStart).join("/")) : "";
		if (!accountName) { state.selected = null; showPicker(); return; }
		var row = state.ledgers.find(function (ledger) { return ledger.name === accountName && (!ledgerKind || ledger.kind === ledgerKind); });
		if (!row) { if (state.ledgers.length) frappe.set_route("ledger-book"); return; }
		if (state.selected && state.selected.name === row.name && $main.find("#kgm-ledger-report").is(":visible")) return;
		state.selected = row; state.highlighted = state.ledgers.indexOf(row); showReport(); showLedger();
	}
	function updatePeriodLabel() { $main.find("#kgm-ledger-period-trigger").text("F2: " + frappe.datetime.str_to_user(from.get_value()) + " " + __("to") + " " + frappe.datetime.str_to_user(to.get_value())); }
	function balanceCells(balance, currency) { var debit = balance.side === "Dr" ? money(balance.amount, currency) : ""; var credit = balance.side === "Cr" ? money(balance.amount, currency) : ""; return '<td class="num">' + debit + '</td><td class="num">' + credit + '</td>'; }
	function reportColumns() { return '<colgroup><col class="kgm-col-date"><col class="kgm-col-particulars"><col class="kgm-col-type"><col class="kgm-col-number"><col class="kgm-col-debit"><col class="kgm-col-credit"></colgroup>'; }
	function renderStatement(data) {
		state.reportRows = data.rows; state.highlightedRow = data.rows.length ? 0 : null;
		var rows = data.rows.map(function (row, index) { return '<tr class="kgm-ledger-row ' + (index === state.highlightedRow ? "active" : "") + '" data-row-index="' + index + '"><td>' + frappe.datetime.str_to_user(row.posting_date) + '</td><td>' + esc(row.particulars) + '</td><td>' + esc(row.voucher_type) + '</td><td><span class="kgm-ledger-voucher">' + esc(row.voucher_no) + '</span></td><td class="num">' + (row.debit ? money(row.debit, data.currency) : "") + '</td><td class="num">' + (row.credit ? money(row.credit, data.currency) : "") + '</td></tr>'; }).join("");
		var totals = '<table class="kgm-tally-totals">' + reportColumns() + '<tbody><tr><td colspan="4" class="label">' + __("Opening Balance") + ':</td>' + balanceCells(data.opening, data.currency) + '</tr><tr class="current"><td colspan="4" class="label">' + __("Current Total") + ':</td><td class="num">' + money(data.total_debit, data.currency) + '</td><td class="num">' + money(data.total_credit, data.currency) + '</td></tr><tr class="closing"><td colspan="4" class="label">' + __("Closing Balance") + ':</td>' + balanceCells(data.closing, data.currency) + '</tr></tbody></table>';
		$main.find("#kgm-ledger-output").html('<div class="kgm-ledger-table-wrap"><table class="kgm-ledger-table">' + reportColumns() + '<thead><tr><th>' + __("Date") + '</th><th>' + __("Particulars") + '</th><th>' + __("Voucher Type") + '</th><th>' + __("Voucher No.") + '</th><th class="num">' + __("Debit") + '</th><th class="num">' + __("Credit") + '</th></tr></thead><tbody>' + rows + '</tbody></table></div>' + totals);
	}
	function loadLedgers() { if (!company.get_value()) return; frappe.call({ method:method + "search_ledgers", args:{company:company.get_value(),text:""}, callback:function (r) { state.ledgers = r.message || []; renderLedgerList(); routeAccount(); } }); }
	function showLedger() {
		if (!state.selected) return;
		$main.find("#kgm-ledger-output").html('<div class="kgm-ledger-empty">' + __("Loading ledger…") + '</div>');
		frappe.call({ method:method + "get_statement", args:{company:company.get_value(),ledger_kind:state.selected.kind,ledger:state.selected.name,from_date:from.get_value(),to_date:to.get_value()}, callback:function (r) { renderStatement(r.message); }, error:function () { $main.find("#kgm-ledger-output").html('<div class="kgm-ledger-empty">' + __("Could not load this ledger.") + '</div>'); } });
	}
	function highlightReportRow(index) {
		if (!state.reportRows.length) return;
		state.highlightedRow = (index + state.reportRows.length) % state.reportRows.length;
		$main.find(".kgm-ledger-row").removeClass("active");
		var row = $main.find('.kgm-ledger-row[data-row-index="' + state.highlightedRow + '"]').addClass("active")[0];
		if (row) row.scrollIntoView({ block:"nearest" });
	}
	function openReportRow(index) {
		var row = state.reportRows[index];
		if (row && row.voucher_type && row.voucher_no) { state.openedVoucher = true; frappe.set_route("Form", row.voucher_type, row.voucher_no); }
	}
	function backToAccountList() { if (state.openedFromPicker) { state.openedFromPicker = false; window.history.back(); } else { frappe.set_route("ledger-book"); } }
	function openHighlighted() { if (state.highlighted === null) return; var ledger = state.ledgers[state.highlighted]; state.openedFromPicker = true; frappe.set_route("ledger-book", ledger.kind, ledger.name); }
	$main.find("#kgm-ledger-search").on("input", function () { state.highlighted = null; renderLedgerList(); });
	$main.find("#kgm-ledger-search").on("keydown", function (event) { if (!state.visible.length) return; var position = state.visible.map(function (row) { return state.ledgers.indexOf(row); }).indexOf(state.highlighted); if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); position = event.key === "ArrowDown" ? (position + 1) % state.visible.length : (position - 1 + state.visible.length) % state.visible.length; state.highlighted = state.ledgers.indexOf(state.visible[position]); renderLedgerList(); } else if (event.key === "Enter") { event.preventDefault(); openHighlighted(); } });
	$main.find("#kgm-ledger-list").on("click", ".kgm-ledger-option[data-ledger-index]", function () { state.highlighted = Number($(this).data("ledger-index")); openHighlighted(); });
	$main.find("#kgm-ledger-back").on("click", backToAccountList);
	$main.find("#kgm-ledger-period-trigger").on("click", function () { $main.find("#kgm-ledger-period-editor").toggle(); if ($main.find("#kgm-ledger-period-editor").is(":visible")) from.$input.focus(); });
	$main.find("#kgm-ledger-period-apply").on("click", function () { if (!from.get_value() || !to.get_value()) return; $main.find("#kgm-ledger-period-editor").hide(); updatePeriodLabel(); showLedger(); });
	$main.find("#kgm-ledger-actions").on("click", "[data-new-doctype]", function () { frappe.new_doc($(this).data("new-doctype")); });
	$main.find("#kgm-ledger-output").on("mouseenter", ".kgm-ledger-row", function () { highlightReportRow(Number($(this).data("row-index"))); });
	$main.find("#kgm-ledger-output").on("click", ".kgm-ledger-row", function () { openReportRow(Number($(this).data("row-index"))); });
	company.$input.on("change", function () { state.selected = null; state.ledgers = []; state.visible = []; state.highlighted = null; $main.find("#kgm-ledger-search").val(""); loadLedgers(); });
	$(document).off("keydown.kgmLedger").on("keydown.kgmLedger", function (event) {
		var route = frappe.get_route();
		if (event.key === "Escape" && state.openedVoucher && route[0] !== "ledger-book") { event.preventDefault(); state.openedVoucher = false; window.history.back(); return; }
		if (route[0] !== "ledger-book" || !state.selected || !$main.find("#kgm-ledger-report").is(":visible")) return;
		if (event.key === "Escape") { event.preventDefault(); if ($main.find("#kgm-ledger-period-editor").is(":visible")) $main.find("#kgm-ledger-period-editor").hide(); else backToAccountList(); return; }
		if (event.key === "F2") { event.preventDefault(); $main.find("#kgm-ledger-period-editor").toggle(); if ($main.find("#kgm-ledger-period-editor").is(":visible")) from.$input.focus(); return; }
		if ($main.find("#kgm-ledger-period-editor").is(":visible") || $(event.target).is("input, select, textarea")) return;
		if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); highlightReportRow((state.highlightedRow === null ? 0 : state.highlightedRow) + (event.key === "ArrowDown" ? 1 : -1)); }
		else if (event.key === "Enter" && state.highlightedRow !== null) { event.preventDefault(); openReportRow(state.highlightedRow); }
	});
	wrapper.kgmLedgerShowRoute = routeAccount;
	frappe.call({ method:method + "get_page_context", callback:function (r) { var context = r.message || {}; Promise.resolve(company.set_value(context.company || "")).then(function () { from.set_value(context.from_date || ""); to.set_value(context.to_date || ""); renderActions(context.actions); showPicker(); loadLedgers(); }); } });
};

frappe.pages["ledger-book"].on_page_show = function (wrapper) {
	if (wrapper.kgmLedgerShowRoute) wrapper.kgmLedgerShowRoute();
};
