# Copyright (c) 2026, Ujjwal  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


DEFAULT_ITEM_TEMPLATES = [
	{"enabled": 1, "template_label": "Kota", "template_code": "KOTA", "is_default": 1},
	{"enabled": 1, "template_label": "Kaddpa", "template_code": "KADDPA", "is_default": 0},
]

DEFAULT_FINISH_OPTIONS = [
	{"enabled": 1, "finish_label": "Fine", "finish_value": "Fine", "suffix": "FIN", "checkbox_field": "custom_fine_polish"},
	{"enabled": 1, "finish_label": "Rough", "finish_value": "Rough", "suffix": "RUF", "checkbox_field": "custom_rough_polish"},
	{"enabled": 1, "finish_label": "Polish", "finish_value": "Polish", "suffix": "", "checkbox_field": "custom_polish_type"},
	{"enabled": 1, "finish_label": "DP", "finish_value": "DP", "suffix": "DP", "checkbox_field": "custom_dp"},
	{"enabled": 1, "finish_label": "Uncut", "finish_value": "Uncut", "suffix": "UNC", "checkbox_field": "custom_uncut"},
	{"enabled": 1, "finish_label": "Ledhar", "finish_value": "Ledhar", "suffix": "LDR", "checkbox_field": "custom_ledhar"},
	{"enabled": 1, "finish_label": "River", "finish_value": "River", "suffix": "RIV", "checkbox_field": "custom_river"},
	{"enabled": 1, "finish_label": "Mirror", "finish_value": "Mirror", "suffix": "MIR", "checkbox_field": "custom_mirror"},
]

DEFAULT_ATTRIBUTE_SUFFIX_RULES = [
	{"enabled": 1, "priority": 10, "attribute_label": "Rajsthan", "checkbox_field": "custom_is_rajsthan", "suffix": "RAJ", "dimension_source": "Actual If No Gadela"},
	{"enabled": 1, "priority": 20, "attribute_label": "Gadela", "checkbox_field": "custom_is_gadela", "suffix": "G"},
	{"enabled": 1, "priority": 30, "attribute_label": "Rough", "checkbox_field": "custom_is_rough", "suffix": "RUF"},
	{"enabled": 1, "priority": 40, "attribute_label": "Patala", "checkbox_field": "custom_is_patala", "suffix": "P", "mutually_exclusive_with": "custom_is_jada"},
	{"enabled": 1, "priority": 50, "attribute_label": "Jada", "checkbox_field": "custom_is_jada", "suffix": "J", "mutually_exclusive_with": "custom_is_patala"},
	{"enabled": 1, "priority": 60, "attribute_label": "Mirror", "checkbox_field": "custom_is_mirror", "suffix": "MIR"},
]

DEFAULT_ITEM_MATCH_RULES = [
	{"enabled": 1, "rule_group": "Moulding Dialog Item", "priority": 10, "rule_name": "Full Round Mould", "match_type": "Exact Item Code", "item_code": "Full Round Mould"},
	{"enabled": 1, "rule_group": "Moulding Dialog Item", "priority": 20, "rule_name": "Dhar Mould", "match_type": "Exact Item Code", "item_code": "Dhar Mould"},
	{"enabled": 1, "rule_group": "Moulding Dialog Item", "priority": 30, "rule_name": "Half Round Mould", "match_type": "Exact Item Code", "item_code": "Half Round Mould"},
	{"enabled": 1, "rule_group": "Moulding Dialog Item", "priority": 40, "rule_name": "Tiles Job Work", "match_type": "Exact Item Code", "item_code": "Tiles Job Work"},
	{"enabled": 1, "rule_group": "Moulding Dialog Item", "priority": 50, "rule_name": "MouldG keyword", "match_type": "Contains Keyword", "keyword": "MOULDG"},
	{"enabled": 1, "rule_group": "Moulding Job Work", "priority": 10, "rule_name": "Job Work keyword", "match_type": "Contains Keyword", "keyword": "JOB WORK", "default_sides": "Select All"},
	{"enabled": 1, "rule_group": "Moulding Quantity Factor", "priority": 10, "rule_name": "MouldG factor", "match_type": "Contains Keyword", "keyword": "MOULDG", "rounding_factor": 3},
	{"enabled": 1, "rule_group": "Moulding Quantity Factor", "priority": 20, "rule_name": "Tiles factor", "match_type": "Contains Keyword", "keyword": "TILES", "rounding_factor": 3},
	{"enabled": 1, "rule_group": "Moulding Quantity Factor", "priority": 30, "rule_name": "Job Work factor", "match_type": "Contains Keyword", "keyword": "JOB WORK", "rounding_factor": 3},
	{"enabled": 1, "rule_group": "Moulding Quantity Factor", "priority": 40, "rule_name": "Mould factor", "match_type": "Contains Keyword", "keyword": "MOULD", "rounding_factor": 6},
	{"enabled": 1, "rule_group": "Square Foot Exclusion", "priority": 10, "rule_name": "Mould exclusion", "match_type": "Contains Keyword", "keyword": "mould"},
	{"enabled": 1, "rule_group": "Square Foot Exclusion", "priority": 20, "rule_name": "MouldG exclusion", "match_type": "Contains Keyword", "keyword": "mouldg"},
	{"enabled": 1, "rule_group": "Square Foot Exclusion", "priority": 30, "rule_name": "Hole exclusion", "match_type": "Contains Keyword", "keyword": "hole"},
	{"enabled": 1, "rule_group": "Square Foot Exclusion", "priority": 40, "rule_name": "Farma exclusion", "match_type": "Contains Keyword", "keyword": "farma"},
	{"enabled": 1, "rule_group": "Square Foot Exclusion", "priority": 50, "rule_name": "Tiles exclusion", "match_type": "Contains Keyword", "keyword": "tiles"},
	{"enabled": 1, "rule_group": "Square Foot Exclusion", "priority": 60, "rule_name": "Job Work exclusion", "match_type": "Contains Keyword", "keyword": "job work"},
	{"enabled": 1, "rule_group": "Stone Calculation Branch", "priority": 10, "rule_name": "Pati", "match_type": "Contains Keyword", "keyword": "pati", "calculation_branch": "Pati"},
	{"enabled": 1, "rule_group": "Stone Calculation Branch", "priority": 20, "rule_name": "Raj Kota", "match_type": "Contains All Keywords", "keyword": "raj", "secondary_keyword": "kota", "calculation_branch": "Raj Kota"},
	{"enabled": 1, "rule_group": "Stone Calculation Branch", "priority": 30, "rule_name": "Kota", "match_type": "Starts With", "keyword": "kota", "calculation_branch": "Kota"},
	{"enabled": 1, "rule_group": "Stone Calculation Branch", "priority": 40, "rule_name": "Kaddpa", "match_type": "Contains Keyword", "keyword": "kaddpa", "calculation_branch": "Kaddpa"},
	{"enabled": 1, "rule_group": "Stone Calculation Branch", "priority": 999, "rule_name": "Default Granite", "match_type": "Default", "calculation_branch": "Default Granite"},
]

DEFAULT_WIDTH_RULES = [
	{"enabled": 1, "rule_group": "Select Item Small Height", "priority": 10, "min_width": 1, "max_width": 6, "include_min": 0, "include_max": 0, "result_type": "Fixed Value", "result_value": 6},
	{"enabled": 1, "rule_group": "Select Item Small Height", "priority": 20, "min_width": 6, "max_width": 12, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 12},
	{"enabled": 1, "rule_group": "Select Item Small Height", "priority": 30, "min_width": 12, "max_width": 15, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 30},
	{"enabled": 1, "rule_group": "Select Item Small Height", "priority": 40, "min_width": 15, "max_width": 18, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 18},
	{"enabled": 1, "rule_group": "Select Item Small Height", "priority": 50, "min_width": 18, "include_min": 1, "result_type": "Plus Six", "multiple": 6},
	{"enabled": 1, "rule_group": "Select Item Standard", "priority": 10, "min_width": 1, "max_width": 12, "include_min": 0, "include_max": 0, "result_type": "Fixed Value", "result_value": 24},
	{"enabled": 1, "rule_group": "Select Item Standard", "priority": 20, "min_width": 12, "max_width": 15, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 30},
	{"enabled": 1, "rule_group": "Select Item Standard", "priority": 30, "min_width": 15, "max_width": 18, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 24},
	{"enabled": 1, "rule_group": "Select Item Standard", "priority": 40, "min_width": 18, "include_min": 1, "result_type": "Plus Six", "multiple": 6},
	{"enabled": 1, "rule_group": "Kota Small Height", "priority": 10, "min_width": 0, "max_width": 5, "include_min": 1, "include_max": 1, "result_type": "Fixed Value", "result_value": 6},
	{"enabled": 1, "rule_group": "Kota Small Height", "priority": 20, "min_width": 5, "max_width": 11, "include_min": 0, "include_max": 1, "result_type": "Fixed Value", "result_value": 12},
	{"enabled": 1, "rule_group": "Kota Small Height", "priority": 30, "min_width": 11, "max_width": 14, "include_min": 0, "include_max": 1, "result_type": "Fixed Value", "result_value": 15},
	{"enabled": 1, "rule_group": "Kota Small Height", "priority": 40, "min_width": 14, "max_width": 18, "include_min": 0, "include_max": 0, "result_type": "Fixed Value", "result_value": 18},
	{"enabled": 1, "rule_group": "Kota Small Height", "priority": 50, "min_width": 18, "include_min": 1, "result_type": "Plus Six", "multiple": 6},
	{"enabled": 1, "rule_group": "Kota Pair Quantity", "priority": 10, "min_width": 0, "max_width": 6, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 6},
	{"enabled": 1, "rule_group": "Kota Pair Quantity", "priority": 20, "min_width": 6, "max_width": 12, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 12},
	{"enabled": 1, "rule_group": "Kota Pair Quantity", "priority": 30, "min_width": 12, "max_width": 15, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 15},
	{"enabled": 1, "rule_group": "Kota Pair Quantity", "priority": 40, "min_width": 15, "max_width": 18, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 24},
	{"enabled": 1, "rule_group": "Kota Pair Quantity", "priority": 50, "min_width": 18, "include_min": 1, "result_type": "Plus Six", "multiple": 6},
	{"enabled": 1, "rule_group": "Kota Single Quantity", "priority": 10, "min_width": 0, "max_width": 6, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 6},
	{"enabled": 1, "rule_group": "Kota Single Quantity", "priority": 20, "min_width": 6, "max_width": 12, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 12},
	{"enabled": 1, "rule_group": "Kota Single Quantity", "priority": 30, "min_width": 12, "max_width": 15, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 18},
	{"enabled": 1, "rule_group": "Kota Single Quantity", "priority": 40, "min_width": 15, "max_width": 18, "include_min": 1, "include_max": 0, "result_type": "Fixed Value", "result_value": 24},
	{"enabled": 1, "rule_group": "Kota Single Quantity", "priority": 50, "min_width": 18, "include_min": 1, "result_type": "Plus Six", "multiple": 6},
]

SCALAR_DEFAULTS = {
	"apply_to_sales_order": 1,
	"apply_to_quotation": 1,
	"apply_to_sales_invoice": 1,
	"enable_select_item_shortcut": 1,
	"select_item_shortcut": "Ctrl+Space",
	"enable_select_item_dialog": 1,
	"enable_moulding_dialog": 1,
	"enable_stone_sqft_calculation": 1,
	"enable_moulding_quantity_calculation": 1,
	"dialog_submit_shortcut": "Ctrl+Enter",
	"post_dialog_focus_field": "custom_height",
	"focus_delay_ms": 200,
	"calculation_debounce_ms": 300,
	"tax_merge_delay_ms": 2000,
	"default_item_template": "KOTA",
	"allow_manual_segment_edit": 1,
	"manual_segment_default": 0,
	"item_lookup_mode": "Exact Match",
	"missing_item_behavior": "Clear Item",
	"small_height_threshold": 24,
	"area_divisor": 144,
	"inch_to_foot_divisor": 12,
	"quantity_precision": 4,
	"height_segment_multiple": 6,
	"default_granite_multiple": 3,
	"kaddpa_multiple": 6,
	"kaddpa_min_cut_width": 24,
	"standard_min_cut_width": 24,
	"pati_height_multiple": 6,
	"pati_width_multiple": 3,
	"pati_min_cut_width": 12,
	"enable_sales_order_date_from_last_order": 1,
	"enable_quotation_date_from_last_quotation": 1,
	"quotation_valid_till_months": 1,
	"enable_sales_order_tax_merge": 1,
	"enable_sales_invoice_tax_merge": 1,
	"show_force_tax_merge_button": 1,
	"auto_merge_after_get_items": 1,
}

TABLE_DEFAULTS = {
	"item_templates": DEFAULT_ITEM_TEMPLATES,
	"finish_options": DEFAULT_FINISH_OPTIONS,
	"attribute_suffix_rules": DEFAULT_ATTRIBUTE_SUFFIX_RULES,
	"item_match_rules": DEFAULT_ITEM_MATCH_RULES,
	"width_rules": DEFAULT_WIDTH_RULES,
}


class AutoFillerSettings(Document):
	def validate(self):
		enabled_documents = (
			int(self.apply_to_sales_order or 0)
			+ int(self.apply_to_quotation or 0)
			+ int(self.apply_to_sales_invoice or 0)
		)
		if enabled_documents < 1:
			frappe.throw("Enable at least one transaction document.")


def apply_missing_defaults(doc):
	changed = False

	for fieldname, default_value in SCALAR_DEFAULTS.items():
		if doc.get(fieldname) in (None, ""):
			doc.set(fieldname, default_value)
			changed = True

	for table_field, rows in TABLE_DEFAULTS.items():
		if doc.get(table_field):
			continue

		for row in rows:
			doc.append(table_field, row)
		changed = True

	return changed


def _value(doc, fieldname):
	value = doc.get(fieldname)
	if value in (None, ""):
		return SCALAR_DEFAULTS.get(fieldname)
	return value


def _rows(doc, table_field, defaults):
	rows = [row.as_dict(no_nulls=True) for row in doc.get(table_field, []) if row.get("enabled")]
	return rows or defaults


@frappe.whitelist()
def get_transaction_settings():
	doc = frappe.get_single("Auto Filler Settings")
	return {
		"apply_to_sales_order": _value(doc, "apply_to_sales_order"),
		"apply_to_quotation": _value(doc, "apply_to_quotation"),
		"apply_to_sales_invoice": _value(doc, "apply_to_sales_invoice"),
		"enable_select_item_shortcut": _value(doc, "enable_select_item_shortcut"),
		"select_item_shortcut": _value(doc, "select_item_shortcut"),
		"enable_select_item_dialog": _value(doc, "enable_select_item_dialog"),
		"enable_moulding_dialog": _value(doc, "enable_moulding_dialog"),
		"enable_stone_sqft_calculation": _value(doc, "enable_stone_sqft_calculation"),
		"enable_moulding_quantity_calculation": _value(doc, "enable_moulding_quantity_calculation"),
		"dialog_submit_shortcut": _value(doc, "dialog_submit_shortcut"),
		"post_dialog_focus_field": _value(doc, "post_dialog_focus_field"),
		"focus_delay_ms": _value(doc, "focus_delay_ms"),
		"calculation_debounce_ms": _value(doc, "calculation_debounce_ms"),
		"default_item_template": _value(doc, "default_item_template"),
		"allow_manual_segment_edit": _value(doc, "allow_manual_segment_edit"),
		"manual_segment_default": _value(doc, "manual_segment_default"),
		"item_lookup_mode": _value(doc, "item_lookup_mode"),
		"missing_item_behavior": _value(doc, "missing_item_behavior"),
		"small_height_threshold": _value(doc, "small_height_threshold"),
		"area_divisor": _value(doc, "area_divisor"),
		"inch_to_foot_divisor": _value(doc, "inch_to_foot_divisor"),
		"quantity_precision": _value(doc, "quantity_precision"),
		"height_segment_multiple": _value(doc, "height_segment_multiple"),
		"default_granite_multiple": _value(doc, "default_granite_multiple"),
		"kaddpa_multiple": _value(doc, "kaddpa_multiple"),
		"kaddpa_min_cut_width": _value(doc, "kaddpa_min_cut_width"),
		"standard_min_cut_width": _value(doc, "standard_min_cut_width"),
		"pati_height_multiple": _value(doc, "pati_height_multiple"),
		"pati_width_multiple": _value(doc, "pati_width_multiple"),
		"pati_min_cut_width": _value(doc, "pati_min_cut_width"),
		"enable_sales_order_date_from_last_order": _value(doc, "enable_sales_order_date_from_last_order"),
		"enable_quotation_date_from_last_quotation": _value(doc, "enable_quotation_date_from_last_quotation"),
		"quotation_valid_till_months": _value(doc, "quotation_valid_till_months"),
		"enable_sales_order_tax_merge": _value(doc, "enable_sales_order_tax_merge"),
		"enable_sales_invoice_tax_merge": _value(doc, "enable_sales_invoice_tax_merge"),
		"show_force_tax_merge_button": _value(doc, "show_force_tax_merge_button"),
		"auto_merge_after_get_items": _value(doc, "auto_merge_after_get_items"),
		"tax_merge_delay_ms": _value(doc, "tax_merge_delay_ms"),
		"item_templates": _rows(doc, "item_templates", DEFAULT_ITEM_TEMPLATES),
		"finish_options": _rows(doc, "finish_options", DEFAULT_FINISH_OPTIONS),
		"attribute_suffix_rules": _rows(doc, "attribute_suffix_rules", DEFAULT_ATTRIBUTE_SUFFIX_RULES),
		"item_match_rules": _rows(doc, "item_match_rules", DEFAULT_ITEM_MATCH_RULES),
		"width_rules": _rows(doc, "width_rules", DEFAULT_WIDTH_RULES),
	}


@frappe.whitelist()
def load_missing_defaults():
	doc = frappe.get_single("Auto Filler Settings")
	changed = apply_missing_defaults(doc)

	if changed:
		doc.save(ignore_permissions=True)
		return {"updated": 1, "message": "Missing default values were loaded."}

	return {"updated": 0, "message": "All default values are already present."}
