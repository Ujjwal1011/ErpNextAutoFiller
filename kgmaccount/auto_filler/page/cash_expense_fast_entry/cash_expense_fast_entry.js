frappe.pages["cash-expense-fast-entry"].on_page_load = function(wrapper) {
	frappe.require("/assets/kgmaccount/js/accounting_fast_entry.js").then(() => window.kgmaccount.accountingFastEntry.make(wrapper, {
		flow: "cash_expense", route: "cash-expense-fast-entry", title: "Cash Expense Fast Entry", subtitle: "Record a cash expense against an expense account.", sourceLabel: "Cash Account", sourceTypes: ["Cash"], counterpartLabel: "Expense Account", debitLabel: "Debit · Expense", creditLabel: "Credit · Cash", debitAccount: "counterpart", creditAccount: "source",
	}));
};
