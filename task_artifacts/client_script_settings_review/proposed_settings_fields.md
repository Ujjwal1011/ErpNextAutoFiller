# Proposed Settings Fields

Implemented as the Single DocType `Auto Filler Settings`.

## Scope

These settings are only for:

- `Sales Order`
- `Quotation`
- `Sales Invoice`

## Main Settings

| Area | Field |
|---|---|
| Transaction Documents | `apply_to_sales_order`, `apply_to_quotation`, `apply_to_sales_invoice` |
| Feature Toggles | `enable_select_item_shortcut`, `enable_select_item_dialog`, `enable_moulding_dialog`, `enable_stone_sqft_calculation`, `enable_moulding_quantity_calculation` |
| Shortcuts and Focus | `select_item_shortcut`, `dialog_submit_shortcut`, `post_dialog_focus_field`, `focus_delay_ms` |
| Calculation Timing | `calculation_debounce_ms`, `tax_merge_delay_ms` |
| Select Item | `default_item_template`, `allow_manual_segment_edit`, `manual_segment_default`, `item_lookup_mode`, `missing_item_behavior` |
| Calculation Constants | `small_height_threshold`, `area_divisor`, `inch_to_foot_divisor`, `quantity_precision` |
| Rounding Constants | `height_segment_multiple`, `default_granite_multiple`, `kaddpa_multiple`, `kaddpa_min_cut_width`, `standard_min_cut_width`, `pati_height_multiple`, `pati_width_multiple`, `pati_min_cut_width` |
| Date Defaults | `enable_sales_order_date_from_last_order`, `enable_quotation_date_from_last_quotation`, `quotation_valid_till_months` |
| Tax Merge | `enable_sales_order_tax_merge`, `enable_sales_invoice_tax_merge`, `show_force_tax_merge_button`, `auto_merge_after_get_items` |

## Child Tables

| Child Table | Purpose |
|---|---|
| `Auto Filler Item Template` | Configure templates such as `KOTA` and `KADDPA`. |
| `Auto Filler Finish Option` | Configure finish labels, suffixes, and target checkbox fields. |
| `Auto Filler Attribute Suffix Rule` | Configure suffixes like `RAJ`, `G`, `P`, `J`, and `MIR`. |
| `Auto Filler Item Match Rule` | Configure item/keyword rules for moulding, exclusions, and stone calculation branches. |
| `Auto Filler Width Rule` | Configure width band outputs used by Select Item and Kota calculations. |

## Defaults

Scalar fields use DocType defaults matching the current scripts. Child-table defaults are seeded by this post-model-sync patch:

`kgmaccount.patches.v1_0.seed_auto_filler_settings`

The same defaults are also exposed by the server helper:

`kgmaccount.auto_filler.doctype.auto_filler_settings.auto_filler_settings.get_transaction_settings`

Default safety now has four layers:

- Scalar fields have DocType-level defaults.
- Child tables are seeded after migration when they are empty.
- The settings form has a `Load Missing Defaults` button that fills blank fields or empty tables without overwriting existing values.
- `get_transaction_settings` returns fallback defaults for blank scalar fields and empty rule tables, so future Client Scripts can keep running.
