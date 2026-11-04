# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency") or "USD"

	columns = get_columns(filters, company_currency)
	data = get_data(filters)
	report_summary = get_report_summary(data, company_currency)
	chart = get_chart_data(data, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(filters, currency):
	return [
		{"label": _("Ingredient Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Ingredient Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Theoretical (BOM)"), "fieldname": "theoretical_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Actual Issues"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Variance Qty"), "fieldname": "variance_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Variance %"), "fieldname": "variance_pct", "fieldtype": "Percent", "width": 100},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Variance Cost"), "fieldname": "variance_cost", "fieldtype": "Currency", "options": "currency", "width": 130},
	]


def get_data(filters):
	params = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
	}

	# 1. Calculate Theoretical Usage from POS Sales × BOM Items
	theo_query = """
		SELECT
			bi.item_code,
			bi.item_name,
			bi.uom,
			SUM(pii.qty * bi.stock_qty / COALESCE(b.quantity, 1)) as theo_qty
		FROM `tabPOS Invoice Item` pii
		JOIN `tabPOS Invoice` pi ON pi.name = pii.parent
		JOIN `tabBOM` b ON b.item = pii.item_code AND b.is_active = 1 AND b.is_default = 1
		JOIN `tabBOM Item` bi ON bi.parent = b.name
		WHERE pi.docstatus = 1
			AND pi.posting_date >= %(from_date)s
			AND pi.posting_date <= %(to_date)s
		GROUP BY bi.item_code, bi.item_name, bi.uom
	"""
	theo_rows = frappe.db.sql(theo_query, params, as_dict=True)
	theo_map = {r.item_code: r for r in theo_rows}

	# 2. Calculate Actual Issues from Stock Entries
	act_query = """
		SELECT
			sed.item_code,
			sed.item_name,
			sed.uom,
			SUM(sed.qty) as actual_qty,
			AVG(sed.basic_rate) as avg_rate
		FROM `tabStock Entry Detail` sed
		JOIN `tabStock Entry` se ON se.name = sed.parent
		WHERE se.docstatus = 1
			AND (se.purpose = 'Material Issue' OR se.purpose = 'Manufacture')
			AND se.posting_date >= %(from_date)s
			AND se.posting_date <= %(to_date)s
		GROUP BY sed.item_code, sed.item_name, sed.uom
	"""
	act_rows = frappe.db.sql(act_query, params, as_dict=True)
	act_map = {r.item_code: r for r in act_rows}

	all_items = set(list(theo_map.keys()) + list(act_map.keys()))
	data = []

	for it in all_items:
		t = theo_map.get(it)
		a = act_map.get(it)
		name = (t and t.item_name) or (a and a.item_name) or it
		uom = (t and t.uom) or (a and a.uom) or "Kg"

		t_qty = flt(t.theo_qty, 2) if t else 0.0
		a_qty = flt(a.actual_qty, 2) if a else 0.0
		var_qty = flt(a_qty - t_qty, 2)
		var_pct = flt((var_qty / t_qty) * 100, 1) if t_qty else 100.0

		rate = flt(a.avg_rate, 2) if a and a.avg_rate else 10.0
		var_cost = flt(var_qty * rate, 2)

		data.append({
			"item_code": it,
			"item_name": name,
			"uom": uom,
			"theoretical_qty": t_qty,
			"actual_qty": a_qty,
			"variance_qty": var_qty,
			"variance_pct": var_pct,
			"valuation_rate": rate,
			"variance_cost": var_cost,
		})

	data.sort(key=lambda x: abs(x["variance_cost"]), reverse=True)
	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_loss = sum(d["variance_cost"] for d in data if d["variance_cost"] > 0)
	tot_gain = sum(abs(d["variance_cost"]) for d in data if d["variance_cost"] < 0)

	return [
		{"value": len(data), "label": _("Tracked Ingredients"), "datatype": "Int"},
		{"value": tot_loss, "label": _("Over-consumption Loss"), "datatype": "Currency", "currency": currency, "indicator": "Red"},
		{"value": tot_gain, "label": _("Portion Savings"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	top = data[:8]
	labels = [d["item_name"][:14] for d in top]
	theo = [d["theoretical_qty"] for d in top]
	act = [d["actual_qty"] for d in top]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Theoretical (BOM)"), "values": theo},
				{"name": _("Actual Used"), "values": act},
			],
		},
		"type": "bar",
		"colors": ["#10b981", "#ef4444"],
	}
