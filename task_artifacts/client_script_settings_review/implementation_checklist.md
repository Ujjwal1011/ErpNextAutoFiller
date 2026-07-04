# Implementation Checklist

## Completed

- [x] Created `Auto Filler Settings` Single DocType.
- [x] Created child tables for item templates, finish options, attribute suffixes, item match rules, and width rules.
- [x] Added a whitelisted helper to return transaction settings with safe defaults.
- [x] Added a migration patch to seed default child-table rows when settings tables are empty.
- [x] Added a `Load Missing Defaults` settings button for manual recovery.
- [x] Added runtime fallback values for blank scalar settings.
- [x] Added `Auto Filler Settings` to the Auto Filler workspace.
- [x] Kept settings scope limited to `Sales Order`, `Quotation`, and `Sales Invoice`.

## Deferred Wiring

- [ ] Update shortcut Client Scripts to read `enable_select_item_shortcut` and `select_item_shortcut`.
- [ ] Update Select Item scripts to read templates, suffixes, width rules, lookup behavior, and focus settings.
- [ ] Update moulding dialog scripts to read item match rules and default side behavior.
- [ ] Update square-foot calculation scripts to read exclusion rules, calculation constants, and width rules.
- [ ] Update moulding quantity scripts to read factor rules and conversion divisor.
- [ ] Update date defaulting scripts to read date settings.
- [ ] Update tax merge scripts to read tax merge toggles and delay.

## Validation To Run After Wiring

- Client-script tests for Sales Order, Quotation, and Sales Invoice.
- JSON validation for all DocType and Workspace files.
- Manual Desk check that `Auto Filler Settings` opens from the workspace.
