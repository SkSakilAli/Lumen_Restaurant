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
		{"label": _("BOM / Recipe No"), "fieldname": "bom_no", "fieldtype": "Link", "options": "BOM", "width": 140},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Dish Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Portion / Yield"), "fieldname": "quantity", "fieldtype": "Float", "width": 105},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Raw Material Cost"), "fieldname": "raw_material_cost", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Total Cost / Portion"), "fieldname": "unit_cost", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Menu Selling Price"), "fieldname": "selling_price", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Food Cost %"), "fieldname": "food_cost_pct", "fieldtype": "Percent", "width": 110},
		{"label": _("Contribution Margin"), "fieldname": "margin", "fieldtype": "Currency", "options": "currency", "width": 130},
	]


def get_data(filters):
	conditions = ["b.docstatus = 1"]
	params = {}

	if filters.get("item_code"):
		conditions.append("b.item = %(item_code)s")
		params["item_code"] = filters.item_code

	if filters.get("is_active"):
		conditions.append("b.is_active = 1 AND b.is_default = 1")

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			b.name as bom_no,
			b.item as item_code,
			b.item_name,
			b.quantity,
			b.uom,
			b.raw_material_cost,
			b.total_cost,
			(
				SELECT price_list_rate
				FROM `tabItem Price` ip
				WHERE ip.item_code = b.item AND ip.selling = 1
				ORDER BY ip.valid_from DESC LIMIT 1
			) as selling_price
		FROM `tabBOM` b
		WHERE {where_clause}
		ORDER BY b.item_name ASC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		qty = flt(r.quantity, 2) or 1.0
		tot_cost = flt(r.total_cost or r.raw_material_cost, 2)
		u_cost = flt(tot_cost / qty, 2)
		s_price = flt(r.selling_price, 2)
		fc_pct = flt((u_cost / s_price) * 100, 1) if s_price else 0.0
		margin = flt(s_price - u_cost, 2) if s_price else 0.0

		data.append({
			"bom_no": r.bom_no,
			"item_code": r.item_code,
			"item_name": r.item_name,
			"quantity": qty,
			"uom": r.uom,
			"raw_material_cost": flt(r.raw_material_cost, 2),
			"unit_cost": u_cost,
			"selling_price": s_price,
			"food_cost_pct": fc_pct,
			"margin": margin,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_recipes = len(data)
	priced = [d for d in data if d["selling_price"] > 0]
	avg_fc = flt(sum(d["food_cost_pct"] for d in priced) / len(priced), 1) if priced else 0.0

	return [
		{"value": tot_recipes, "label": _("Active Menu Recipes"), "datatype": "Int"},
		{"value": avg_fc, "label": _("Avg Target Food Cost %"), "datatype": "Percent", "indicator": "Green" if avg_fc <= 30 else "Orange"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	priced = [d for d in data if d["selling_price"] > 0][:8]
	labels = [d["item_name"][:14] for d in priced]
	costs = [d["unit_cost"] for d in priced]
	prices = [d["selling_price"] for d in priced]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Recipe Cost"), "values": costs},
				{"name": _("Selling Price"), "values": prices},
			],
		},
		"type": "bar",
		"colors": ["#ef4444", "#10b981"],
	}
