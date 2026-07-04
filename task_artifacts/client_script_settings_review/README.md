# Client Script Settings Review

This folder stores working artifacts for reviewing KGM Account client scripts and deciding what should move into a centralized settings DocType.

## Current Scope

The settings work is now limited to transaction documents only:

- `Sales Order`
- `Quotation`
- `Sales Invoice`

WhatsApp scripts, WhatsApp backend defaults, Sales Order Fast Entry page settings, and batch-print settings are out of scope unless they are explicitly brought back in later.

## Artifact Index

- `task_list.md` - review workflow, status, and outputs to produce.
- `client_script_inventory.md` - inventory of exported Client Script records and app JavaScript files.
- `script_review_notes.md` - script-by-script findings and settings candidates.
- `proposed_settings_fields.md` - concrete fields and child tables created for transaction settings.
- `implementation_checklist.md` - implementation status and follow-up wiring checklist.

## Goal

Identify hardcoded behavior in `Sales Order`, `Quotation`, and `Sales Invoice` client scripts, then map configurable behavior to one transaction settings DocType and its child tables.
