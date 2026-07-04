# Script Review Notes

This file records hardcoded behavior found during the client-script review and whether each item should become part of a settings DocType.

## Scope Update

Current settings implementation scope is limited to:

- `Sales Order`
- `Quotation`
- `Sales Invoice`

Earlier WhatsApp findings are retained below only as historical review notes. They should not be included in the current settings DocType.

## Created Settings Artifacts

Primary DocType:

- `Auto Filler Settings` as a Single DocType under module `Auto Filler`.

Child tables:

- `Auto Filler Item Template`
- `Auto Filler Finish Option`
- `Auto Filler Attribute Suffix Rule`
- `Auto Filler Item Match Rule`
- `Auto Filler Width Rule`

Workspace:

- `Auto Filler Settings` is linked from the `Auto Filler` workspace.

Default seeding:

- `kgmaccount.patches.v1_0.seed_auto_filler_settings` fills empty settings tables with current script defaults after model sync.
- The `Load Missing Defaults` button fills missing defaults manually without overwriting existing settings.
- `get_transaction_settings` returns safe fallback defaults if scalar fields or rule tables are blank.

Current wiring status:

- The settings DocType and server helper exist.
- Existing Client Scripts are not yet refactored to read these settings.

## 1. Chat Interface

Client Script: `Chat Interface`  
DocType: `WhatsApp Group`

Current status: out of scope for the transaction settings build.

### Settings Candidates

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| Embedded chat always renders for saved WhatsApp Group docs | Enable embedded WhatsApp chat | Check | Add to settings so the UI can be disabled without deleting the Client Script. |
| Chat fieldname is `chat_interface` | Chat interface fieldname | Data | Optional. Keep in code unless this field is expected to change. |
| Chat height is `500px` | Chat panel height | Int/Data | Add if users want larger/smaller chat history display. |
| WhatsApp wallpaper URL is hardcoded to a GitHub image | Chat background image URL | Data/Attach Image | Add. External image URLs are brittle and should be configurable or moved local. |
| Incoming bubble color `#ffffff`, outgoing bubble color `#dcf8c6`, container color `#efeae2` | Chat theme colors | Color fields | Optional. Useful if settings should control branding/theme. |
| Message bubble max width `65%` | Message bubble max width percent | Int | Optional UI setting. |
| Auto-scroll delay is `50ms` | Chat auto-scroll delay | Int | Low priority. Keep default in code unless timing issues happen. |
| Chat always auto-scrolls to bottom | Auto-scroll chat on load | Check | Add if users need to inspect older messages without jumping. |
| Loading/empty labels are hardcoded | Chat loading message / empty message | Data/Small Text | Low priority. Usually code-only unless multi-language/custom wording is needed. |
| Media preview behavior is fixed for Image/Video/Audio/Document | Enable media preview | Check | Add if media preview causes performance or privacy concerns. |
| Audio max width is `200px` | Audio preview max width | Int | Low priority UI setting. |

### Code-Only / Not Settings

- Backend method path `kgmaccount.whatsapp_suite.doctype.whatsapp_group.whatsapp_group.get_chat_history` should stay in code.
- CSS class names should stay in code.
- Media type branching should stay in code.

### Non-Settings Fixes To Consider

- Escape `msg.message` before replacing newlines with `<br>`. Current rendering injects message content directly into HTML.
- Escape attachment URLs and media labels, or build DOM nodes instead of string-concatenated HTML.
- Consider moving large inline CSS out of the Client Script if this UI remains long-term.

## 2. Llm_based Sales Order

Client Script: `Llm_based Sales Order`  
DocType: `WhatsApp Order Staging`

Current status: out of scope for the transaction settings build.

### Settings Candidates

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| Button appears only when status is `Pending` | Allowed staging status for conversion | Select/Data | Usually keep in code because it matches DocType workflow/status options. |
| Button label `Create Sales Order` | Conversion button label | Data | Low priority. Keep in code unless UI text needs admin customization. |
| Freeze message `Slicing handwriting coordinates and mapping Draft fields...` | Conversion loading message | Small Text | Optional. Useful if the wording should be business-friendly. |
| Success alert `Sales Order Draft generated successfully!` | Conversion success message | Small Text | Low priority. |
| Backend method converts staging to Sales Order | Enable AI staging conversion button | Check | Add to settings so the feature can be hidden/disabled without removing the script. |

### Backend Settings Candidates Connected To This Script

These are not in the Client Script itself, but the button calls `kgmaccount.utils.order_builder.convert_staging_to_sales_order`, which currently has important hardcoded defaults.

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| `DEFAULT_WHATSAPP_CUSTOMER = "Suspense"` | Default WhatsApp fallback customer | Link: Customer | Add. This is business data and should not be hardcoded. |
| `DEFAULT_WHATSAPP_ITEM_CODE = "KOTA 11x11 RAJ"` | Default WhatsApp fallback item | Link: Item | Add. This is business data and should not be hardcoded. |
| `SALES_ORDER_QTY_CLIENT_SCRIPT = "Sales-Order Kota Kaddpaa Granite Neno Calculation"` | Quantity calculation Client Script name | Link/Data: Client Script | Add only if the architecture continues executing Client Scripts from Python. Better long-term: move calculation rules into a shared server/client module or settings-driven rules. |
| Date parsing expects `DD/MM/YY` | AI order date format | Data/Select | Add if AI input date formats vary. |
| Sales Order item `rate` is always `0` | Default AI order item rate | Currency | Add if generated orders should use a configurable default rate. |
| Sales Order item `uom` is always `Nos` | Default AI order item UOM | Link: UOM | Add. Business default. |
| Cropped image quality is `95` | AI cropped image JPEG quality | Int | Low priority. |
| Conversion sets `custom_is_ai_generated = 1` | Mark AI generated orders | Check | Probably keep in code; this is audit behavior. |

### Code-Only / Not Settings

- Backend method path should stay in code.
- Status transition from `Pending` to `Converted` should stay aligned with the DocType/workflow.
- Error handling and rollback behavior should stay in code.

## 3-5. Select Item Keyboard Shortcut

Client Scripts:

- `sales_order Focus Button` on `Sales Order`
- `Sales Invoice Focus Button` on `Sales Invoice`
- `Quotation Focus Button` on `Quotation`

### Settings Candidates

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| Shortcut is always active | Enable Select Item shortcut | Check | Add. Allows disabling keyboard behavior globally. |
| Shortcut is `Ctrl + Space` | Select Item shortcut key | Data/Select | Add if users may want another shortcut. Default: `Ctrl+Space`. |
| Shortcut applies to Sales Order, Sales Invoice, and Quotation | Enabled doctypes for Select Item shortcut | Child Table or Check fields | Optional. Add only if shortcuts should differ per document type. |
| Triggered dialog event is `custom_select_item` | Select Item trigger event | Data | Keep in code; this is an internal handler contract. |

### Code-Only / Not Settings

- Child row DocType mapping should stay in code: `Sales Order Item`, `Sales Invoice Item`, `Quotation Item`.
- DOM selectors such as `.grid-row`, `input:focus`, and `data-name` should stay in code.
- Listener namespaces `keydown.custom_so_shortcut`, `keydown.custom_si_shortcut`, and `keydown.custom_qt_shortcut` should stay in code.

### Non-Settings Refactor To Consider

- These three scripts can be merged into one shared helper to avoid maintaining three copies.
- Use `e.key === " "` or `e.code === "Space"` instead of deprecated `keyCode`.
- Guard against triggering inside text areas or non-item grids if that becomes an issue.

## 6. Sales-Order Moulding Dialog Box

Client Script: `Sales-Order Moulding Dialog Box`  
DocType: `Sales Order`

### Settings Candidates

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| Dialog opens automatically when item matches moulding rules | Enable moulding dimension dialog | Check | Add as a global feature toggle. |
| Exact moulding item names are `Full Round Mould`, `Dhar Mould`, `Half Round Mould`, `Tiles Job Work` | Moulding item rules | Child Table with Link/Data item code and match type | Add. Item names are business data and should be configurable. |
| Keyword match includes `MOULDG` | Moulding keyword rules | Child Table with keyword and case-insensitive flag | Add. Avoid hardcoding naming conventions. |
| Keyword match includes `JOB WORK` | Job work keyword rules | Child Table or keyword setting | Add. It controls both dialog eligibility and default side selection. |
| Job work items default Right/Left/Top/Bottom to checked | Job work default selected sides | Check fields or MultiSelect | Add. This is business behavior. |
| Dimensions are fetched from the previous item row | Copy dimensions from previous row for moulding items | Check | Add. Useful if some users want blank dimensions instead. |
| No previous row means fetched width/height default to `0` | Default moulding width / height | Float | Optional. Usually `0` is fine in code. |
| Focus delay after dialog action is `200ms` | Dialog focus delay | Int | Low priority. Keep code default unless focus timing varies. |
| Focus target after dialog is `custom_height` | Post-dialog focus field | Data/Select | Optional. Add only if workflow wants a different field. |
| Dialog submit shortcut is `Ctrl + Enter` | Dialog submit shortcut | Data/Select | Add if keyboard shortcuts are being centralized. |

### Code-Only / Not Settings

- Fieldname mapping should stay in code unless custom fields are expected to be renamed: `custom_right`, `custom_left`, `custom_top`, `custom_bottom`, `custom_width`, `custom_height`.
- Dialog layout fieldnames such as `section_main`, `col_left`, `col_right`, and `section_dimensions` should stay in code.
- Dialog labels can stay in code unless UI copy customization is a goal.

### Non-Settings Refactor To Consider

- The same moulding dialog pattern exists for Sales Order, Quotation, and Sales Invoice. It should become one shared helper that receives parent/child DocType names.
- The helper name `set_focus_on_item_code` is misleading because it focuses `custom_height`.
- If settings are loaded asynchronously, cache them once per form load to avoid slowing every item-code change.

## 7. Sales-Order Select Item

Client Script: `Sales-Order Select Item`  
DocType: `Sales Order`

### Settings Candidates

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| Select Item dialog is always available through `custom_select_item` | Enable Select Item dialog | Check | Add as a global feature toggle. |
| Template options are `Kota`/`KOTA` and `Kaddpa`/`KADDPA` | Item templates | Child Table: label, code prefix, enabled, default | Add. Templates are core business configuration. |
| Default template is `KOTA` | Default item template | Link/Select from template child table | Add. |
| Height segments round to next multiple of `6`, but exact multiples add another `6` | Height segment rule | Child Table or structured JSON rule | Add carefully. This is a business formula used in multiple scripts. |
| Width rule changes when height is `< 24` | Width height threshold | Float | Add if calculation settings are exposed. Default: `24`. |
| Width bands for height `< 24`: `>1 <6 => 6`, `6-<12 => 12`, `12-<15 => 30`, `15 => 18`, `>15 <18 => 18`, `>=18 => special 6-rule` | Width segment rules for small height | Child Table: min, max, output, rule type | High-value but needs careful validation. |
| Standard width bands: `<6 => 24`, `6-<12 => 24`, `12-<15 => 30`, `15 => 24`, `>15 <18 => 24`, `>=18 => special 6-rule` | Standard width segment rules | Child Table | High-value but should be tested heavily. |
| Kaddpa width uses special 6-rule with minimum `24` | Kaddpa minimum cut width | Float | Add. |
| Non-Rajsthan standard width enforces minimum `24` | Standard minimum cut width | Float | Add if calculation settings are exposed. |
| Manual segment editing default is off | Allow manual segment editing / default manual editing | Check | Add. Useful workflow setting. |
| Finish options are `Fine`, `Rough`, `Polish`, `DP`, `Uncut`, `Ledhar`, `River`, `Mirror` | Finish/polish options | Child Table: label, suffix, target checkbox field | Add. This is business vocabulary. |
| Finish suffix map is hardcoded: `FIN`, `RUF`, blank, `DP`, `UNC`, `LDR`, `RIV`, `MIR` | Finish suffix mapping | Child Table | Add. |
| Attribute suffixes are hardcoded: Rajsthan `RAJ`, Gadela `G`, Rough `RUF`, Patala `P`, Jada `J`, Mirror `MIR` | Item attribute suffix mapping | Child Table | Add. |
| Rajsthan without Gadela uses actual dimensions instead of cut dimensions in item code | Item-code dimension source rules | Child Table / rule setting | Add if users need to adjust generated item names. |
| Patala and Jada are mutually exclusive | Mutually exclusive attributes | Code or child table rule | Keep in code for v1 unless more exclusivity rules appear. |
| Item lookup requires exact `item_code` match | Generated item lookup mode | Select: Exact / Starts With / Create Missing | Add only if business wants fallback or item creation. Default should remain Exact. |
| Missing item sets row `item_code` to null | Missing generated item behavior | Select: Clear Item / Keep Existing / Show Only | Optional. Current behavior can surprise users. |
| Dialog submit shortcut is `Ctrl + Enter` | Dialog submit shortcut | Data/Select | Reuse same centralized shortcut setting as moulding dialog if added. |
| Focus returns to `custom_height` after close / lookup | Post-dialog focus field | Data/Select | Optional. |
| Focus delay is `200ms` | Dialog focus delay | Int | Low priority. |

### Code-Only / Not Settings

- The `frappe.client.get_list` method path and exact Item lookup call should stay in code.
- Fieldname mapping to existing custom fields should stay in code for v1.
- Dialog layout structure should stay in code.
- Client event name `custom_select_item` should stay as an internal contract.

### Non-Settings Refactor To Consider

- Sales Order, Quotation, and Sales Invoice appear to have near-duplicate Select Item scripts. Build one shared helper and configure only parent/child DocType differences.
- Calculation rules also overlap with square-foot scripts and the WhatsApp Sales Order conversion path. Long-term, move formulas to one shared source instead of copying them through Client Scripts.
- Because tests already cover Select Item behavior, any settings refactor should preserve current defaults exactly and run the client-script test suite.

## 8. Sales-Order Kota Kaddpaa Granite Neno Calculation

Client Script: `Sales-Order Kota Kaddpaa Granite Neno Calculation`  
DocType: `Sales Order`

### Settings Candidates

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| Square-foot calculation is always active | Enable stone square-foot calculation | Check | Add as a global feature toggle. |
| Debounce delay is `300ms` | Calculation debounce delay | Int | Low priority. Default: `300`. |
| Exclusion keywords are `mould`, `mouldg`, `hole`, `farma`, `tiles`, `job work` | Square-foot exclusion keywords | Child Table | Add. These determine which rows are skipped. |
| Branch keywords are `pati`, `raj` + `kota`, `kota` prefix, `kaddpa`, else default granite | Stone calculation item rules | Child Table: rule name, match type, keywords/prefix, priority | Add. This is core business behavior. |
| Pati height rounds to multiple of `6`; width minimum is `12` then rounds to `3` | Pati calculation rule | Structured rule fields | Add only with tests. |
| Raj Kota uses plus-six rounding for height and width | Raj Kota calculation rule | Structured rule fields | Add only with tests. |
| Kota-only height uses strict next `6` | Kota height rule | Structured rule fields | Add only with tests. |
| Kota-only width changes when height is `< 24` | Kota height threshold | Float | Add if exposing calculation settings. Default: `24`. |
| Kota width pair/single/small band rules are hardcoded | Kota width rule tables | Child Tables | Add if admin needs formula control. High impact. |
| Kaddpa rounds height and width to multiple of `6` | Kaddpa calculation rule | Structured rule fields | Add only with tests. |
| Default granite rounds height and width to multiple of `3` | Default stone calculation rule | Structured rule fields | Add. |
| SQFT divisor is `144` | Area conversion divisor | Float | Add only if non-inch units are expected. Default: `144`. |
| Quantity precision is `4` decimals | Calculated quantity precision | Int | Optional. Default: `4`. |
| Output fields are `cut_from_height`, `cut_from_width`, and `qty` | SQFT output field mapping | Data | Keep in code for v1; verify fieldnames before any refactor. |

### Code-Only / Not Settings

- Math helper implementation should stay in code unless formulas are moved to a validated calculation-rule engine.
- Event wiring for `item_code`, `custom_height`, `custom_width`, and `custom_quantity` should stay in code.

### Non-Settings Refactor To Consider

- Current custom field fixtures define `custom_cut_from_height` and `custom_cut_from_width`, while this script writes `cut_from_height` and `cut_from_width`. Existing tests expect the shorter names, so verify actual Desk behavior before changing it.
- This same formula exists across Sales Order, Quotation, Sales Invoice, and the WhatsApp conversion runner. A shared calculation module would reduce drift.
- Run the CSV-backed client-script tests after any settings extraction.

## 9. Sales-Order Kota Granite Moulding Calculation

Client Script: `Sales-Order Kota Granite Moulding Calculation`  
DocType: `Sales Order`

### Settings Candidates

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| Moulding running-foot calculation is always active | Enable moulding quantity calculation | Check | Add as a global feature toggle. |
| Keywords `MOULDG`, `TILES`, `JOB WORK` use rounding factor `3` | Moulding factor rules | Child Table: keyword, factor, priority | Add. Business rule. |
| Keyword `MOULD` uses rounding factor `6` | Moulding factor rules | Child Table | Add with the same table. |
| Dimensions are converted from inches to feet by dividing by `12` | Inch-to-foot divisor | Float | Usually keep default, but can be a setting if units may change. |
| Side flags Right/Left/Top/Bottom control running-foot total | Moulding side field mapping | Code or child table | Keep in code for v1 unless custom fields may be renamed. |
| Calculation only triggers on `custom_quantity` change | Moulding calculation trigger fields | Code | Consider code refactor, not settings. It may need to trigger on width/height/side changes too. |

### Code-Only / Not Settings

- Running-foot formula should stay in code unless a tested formula engine is introduced.
- Debug `console.log` behavior should be removed or guarded by a developer/debug setting, not exposed as normal business settings.

### Non-Settings Refactor To Consider

- Triggering only on `custom_quantity` means changing side flags or dimensions after quantity may not recalculate immediately.
- The keyword order matters because `MOULDG` must be checked before `MOULD`; preserve priority if moved to settings.

## 10-13. Quotation Calculation, Select Item, and Moulding Dialog Scripts

Client Scripts:

- `Quotation Kota Kaddpaa Granite Neno Calculation`
- `Quotation Select Item`
- `Qutotation Kota Granite Moulding Calculation`
- `Quotation Moulding Dialog Box`

### Comparison Result

After normalizing `Sales Order`/`Sales Order Item` to `Quotation`/`Quotation Item`, these scripts match the Sales Order versions exactly.

### Settings Candidates

| Current Hardcoded Behavior | Suggested Setting | Type | Recommendation |
|---|---|---|---|
| Quotation uses same Select Item settings as Sales Order | Shared transaction item settings | Single shared settings section | Use the same template, suffix, rounding, and lookup settings. |
| Quotation uses same square-foot settings as Sales Order | Shared stone calculation settings | Single shared settings section | Use the same calculation rules. |
| Quotation uses same moulding dialog and running-foot settings as Sales Order | Shared moulding settings | Single shared settings section | Use the same moulding item rules and factor rules. |
| Feature is enabled on Quotation because script exists | Enable on Quotation | Check | Add only if per-DocType toggles are needed. Default: enabled. |

### Code-Only / Not Settings

- Parent and child DocType names should be passed by code, not stored as business settings.
- Typo in script name `Qutotation` can stay for compatibility unless scripts are renamed/migrated deliberately.

### Non-Settings Refactor To Consider

- Replace these duplicate Client Scripts with shared JS helpers or generated scripts that receive DocType-specific mappings.
- Use one settings read path for Sales Order, Quotation, and Sales Invoice so defaults cannot drift between documents.
