frappe.pages["bank-receipt-fast-entry"].on_page_load = function(wrapper) {
	frappe.require("/assets/kgmaccount/js/accounting_fast_entry.js").then(() => window.kgmaccount.accountingFastEntry.make(wrapper, {
		flow: "bank_receipt", route: "bank-receipt-fast-entry", title: "Bank Receipt Fast Entry", subtitle: "Record a bank receipt from a customer or directly against income.", sourceLabel: "Bank Account", sourceTypes: ["Bank"], counterpartLabel: "Received From Account", debitLabel: "Debit · Bank", creditLabel: "Credit · From account", debitAccount: "source", creditAccount: "counterpart", partyType: "Customer", partyLabel: "Customer", partyAccountType: "Receivable", invoiceDoctype: "Sales Invoice", invoiceTitle: "Allocate to open Sales Invoices", referenceFields: true, referenceRequired: true,
	}));
};
