frappe.pages["supplier-payment-fast-entry"].on_page_load = function(wrapper) {
	frappe.require("/assets/kgmaccount/js/accounting_fast_entry.js").then(() => window.kgmaccount.accountingFastEntry.make(wrapper, {
		flow: "supplier_payment", route: "supplier-payment-fast-entry", title: "Supplier Payment Fast Entry", subtitle: "Pay a supplier and optionally allocate the payment to Purchase Invoices.", sourceLabel: "Cash / Bank Account", sourceTypes: ["Cash", "Bank"], counterpartLabel: "Supplier Payable Account", debitLabel: "Debit · Supplier", creditLabel: "Credit · Cash / Bank", debitAccount: "counterpart", creditAccount: "source", partyType: "Supplier", partyLabel: "Supplier", partyAccountType: "Payable", invoiceDoctype: "Purchase Invoice", invoiceTitle: "Allocate to open Purchase Invoices", referenceFields: true,
	}));
};
