# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company_currency = frappe.defaults.get_global_default("currency") or "USD"

	columns = get_columns(filters, company_currency)
	data = get_data(filters)
	report_summary = get_report_summary(data, company_currency)
	chart = get_chart_data(data, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(filters, currency):
	return [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 130},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Actual Qty"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 105},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "options": "currency", "width": 130},
	]


def get_data(filters):
	conditions = ["b.actual_qty != 0"]
	params = {}

	if filters.get("warehouse"):
		conditions.append("b.warehouse = %(warehouse)s")
		params["warehouse"] = filters.warehouse

	if filters.get("item_group"):
		conditions.append("i.item_group = %(item_group)s")
		params["item_group"] = filters.item_group

	if filters.get("item_code"):
		conditions.append("b.item_code = %(item_code)s")
		params["item_code"] = filters.item_code

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			b.item_code,
			i.item_name,
			i.item_group,
			b.warehouse,
			i.stock_uom,
			b.actual_qty,
			b.valuation_rate,
			b.stock_value
		FROM `tabBin` b
		JOIN `tabItem` i ON i.name = b.item_code
		WHERE {where_clause}
		ORDER BY b.stock_value DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		qty = flt(r.actual_qty, 2)
		rate = flt(r.valuation_rate, 2)
		val = flt(r.stock_value, 2) if r.stock_value else flt(qty * rate, 2)

		data.append({
			"item_code": r.item_code,
			"item_name": r.item_name,
			"item_group": r.item_group,
			"warehouse": r.warehouse,
			"stock_uom": r.stock_uom,
			"actual_qty": qty,
			"valuation_rate": rate,
			"stock_value": val,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_items = len(data)
	tot_val = sum(d["stock_value"] for d in data)

	return [
		{"value": tot_items, "label": _("Stocked Items"), "datatype": "Int"},
		{"value": tot_val, "label": _("Total Inventory Value"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_group = defaultdict(float)
	for d in data:
		g = d["item_group"] or "General"
		by_group[g] += flt(d["stock_value"])

	labels = list(by_group.keys())[:8]
	vals = [round(by_group[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Stock Value"), "values": vals}],
		},
		"type": "donut",
		"colors": ["#10b981", "#6366f1", "#f59e0b", "#ec4899"],
	}
