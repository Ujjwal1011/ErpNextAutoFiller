# Client Script Inventory

Source: `kgmaccount/fixtures/client_script.json`

## Current Scope

Only scripts attached to these DocTypes are in scope for the settings build:

- `Sales Order`
- `Quotation`
- `Sales Invoice`

Scripts for `WhatsApp Group`, `WhatsApp Order Staging`, `WhatsApp Connection`, standalone pages, and batch-print tooling are excluded from the current settings implementation.

| # | Client Script | DocType | Enabled | Script Size |
|---|---|---|---:|---:|
| 1 | Chat Interface | WhatsApp Group | Yes | 5,517 chars |
| 2 | Llm_based Sales Order | WhatsApp Order Staging | Yes | 931 chars |
| 3 | sales_order Focus Button | Sales Order | Yes | 1,178 chars |
| 4 | Sales Invoice Focus Button | Sales Invoice | Yes | 1,182 chars |
| 5 | Quotation Focus Button | Quotation | Yes | 1,174 chars |
| 6 | Sales-Order Moulding Dialog Box | Sales Order | Yes | 9,517 chars |
| 7 | Sales-Order Select Item | Sales Order | Yes | 17,105 chars |
| 8 | Sales-Order Kota Kaddpaa Granite Neno Calculation | Sales Order | Yes | 4,682 chars |
| 9 | Sales-Order Kota Granite Moulding Calculation | Sales Order | Yes | 2,298 chars |
| 10 | Quotation Kota Kaddpaa Granite Neno Calculation | Quotation | Yes | 4,680 chars |
| 11 | Quotation Select Item | Quotation | Yes | 17,103 chars |
| 12 | Qutotation Kota Granite Moulding Calculation | Quotation | Yes | 2,296 chars |
| 13 | Quotation Moulding Dialog Box | Quotation | Yes | 9,513 chars |
| 14 | Sales-Invoice Select Item | Sales Invoice | Yes | 17,107 chars |
| 15 | Sales-Invoice Moulding Dialog Box | Sales Invoice | Yes | 9,542 chars |
| 16 | Sales-Invoice Kota Granite Moulding Calculation | Sales Invoice | Yes | 2,300 chars |
| 17 | Sales-Invoice Kota Kaddpaa Granite Neno Calculation | Sales Invoice | Yes | 4,684 chars |
| 18 | Quotation-New-Quotation | Quotation | Yes | 102 chars |
| 19 | sales order Date Changing | Sales Order | Yes | 859 chars |
| 20 | Qutotation Date Changing | Quotation | Yes | 934 chars |
| 21 | Buttons whatsapp connection | WhatsApp Connection | Yes | 4,340 chars |
| 22 | WhatsApp Group Button | WhatsApp Group | Yes | 899 chars |
| 23 | Sales-Order-Merging-Quotation | Sales Order | Yes | 4,195 chars |
| 24 | Sales-Invoice-Merging-TaxAndCharges | Sales Invoice | Yes | 4,979 chars |

## Related App JavaScript Files

- In scope: `kgmaccount/public/js/sales_order.js`
- Out of scope unless requested: `kgmaccount/auto_filler/page/sales_order_fast_entry/sales_order_fast_entry.js`
- Out of scope unless requested: `kgmaccount/auto_filler/doctype/sales_order_batch_print/sales_order_batch_print.js`
- Out of scope: `kgmaccount/whatsapp_suite/page/whatsapp_chat_ui/whatsapp_chat_ui.js`
- Out of scope: `kgmaccount/whatsapp_suite/doctype/whatsapp_connection/whatsapp_connection.js`

## Review Order

1. Shared shortcut/focus scripts.
2. Sales Order, Quotation, and Sales Invoice moulding dialog scripts.
3. Sales Order, Quotation, and Sales Invoice Select Item scripts.
4. Sales Order, Quotation, and Sales Invoice square-foot and moulding calculation scripts.
5. Transaction date defaulting scripts.
6. Sales Order and Sales Invoice tax merge scripts.
7. Scoped Sales Order doctype JavaScript.
