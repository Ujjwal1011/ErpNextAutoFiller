frappe.pages["cash-bank-transfer-fast-entry"].on_page_load = function(wrapper) {
	frappe.require("/assets/kgmaccount/js/accounting_fast_entry.js").then(() => window.kgmaccount.accountingFastEntry.make(wrapper, {
		flow: "internal_transfer", route: "cash-bank-transfer-fast-entry", title: "Cash / Bank Transfer Fast Entry", subtitle: "Move money between two company cash or bank accounts.", sourceLabel: "Transfer From", sourceTypes: ["Cash", "Bank"], counterpartLabel: "Transfer To", debitLabel: "Debit · Destination", creditLabel: "Credit · Source", debitAccount: "counterpart", creditAccount: "source", referenceFields: true,
	}));
};
