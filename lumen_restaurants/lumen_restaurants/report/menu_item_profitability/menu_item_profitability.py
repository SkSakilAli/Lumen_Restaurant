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
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Dish Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 120},
		{"label": _("Qty Sold"), "fieldname": "qty_sold", "fieldtype": "Float", "width": 90},
		{"label": _("Selling Price"), "fieldname": "avg_selling_price", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Recipe Cost"), "fieldname": "recipe_cost", "fieldtype": "Currency", "options": "currency", "width": 115},
		{"label": _("Gross Margin"), "fieldname": "unit_margin", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Total Revenue"), "fieldname": "total_revenue", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Total Profit"), "fieldname": "total_profit", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Menu Classification"), "fieldname": "classification", "fieldtype": "Data", "width": 140},
	]


def get_data(filters):
	conditions = ["inv.docstatus = 1"]
	params = {}

	if filters.get("company"):
		conditions.append("inv.company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("inv.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("inv.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("item_group"):
		conditions.append("it.item_group = %(item_group)s")
		params["item_group"] = filters.item_group

	where_clause = " AND ".join(conditions)

	# Fetch item sales joined with BOM recipe cost
	query = f"""
		SELECT
			it.item_code,
			it.item_name,
			i.item_group,
			SUM(it.qty) as qty_sold,
			SUM(it.base_net_amount) as total_revenue,
			COALESCE(b.total_cost / NULLIF(b.quantity, 0), i.valuation_rate, 0) as recipe_cost
		FROM `tabPOS Invoice Item` it
		JOIN `tabPOS Invoice` inv ON inv.name = it.parent
		JOIN `tabItem` i ON i.name = it.item_code
		LEFT JOIN `tabBOM` b ON b.item = it.item_code AND b.is_active = 1 AND b.is_default = 1
		WHERE {where_clause}
		GROUP BY it.item_code, it.item_name, i.item_group, b.total_cost, b.quantity, i.valuation_rate
		HAVING qty_sold > 0
		ORDER BY total_revenue DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)
	if not rows:
		return []

	avg_qty = sum(flt(r.qty_sold) for r in rows) / len(rows)

	# Pre-calculate unit margins to find median margin
	margins = []
	for r in rows:
		qty = flt(r.qty_sold)
		rev = flt(r.total_revenue)
		sp = rev / qty if qty else 0
		rc = flt(r.recipe_cost) or (sp * 0.32)
		margins.append(sp - rc)

	avg_margin = sum(margins) / len(margins) if margins else 0

	data = []
	for r, m in zip(rows, margins):
		qty = flt(r.qty_sold, 1)
		rev = flt(r.total_revenue, 2)
		sp = flt(rev / qty, 2) if qty else 0.0
		rc = flt(r.recipe_cost, 2) or round(sp * 0.32, 2)
		u_margin = flt(sp - rc, 2)
		tot_profit = flt(u_margin * qty, 2)

		# Menu Engineering categorization
		is_high_pop = qty >= avg_qty
		is_high_margin = u_margin >= avg_margin

		if is_high_pop and is_high_margin:
			cat = "Star ⭐"
		elif is_high_pop and not is_high_margin:
			cat = "Plowhorse 🐴"
		elif not is_high_pop and is_high_margin:
			cat = "Puzzle 🧩"
		else:
			cat = "Dog 🐶"

		data.append({
			"item_code": r.item_code,
			"item_name": r.item_name,
			"item_group": r.item_group,
			"qty_sold": qty,
			"avg_selling_price": sp,
			"recipe_cost": rc,
			"unit_margin": u_margin,
			"total_revenue": rev,
			"total_profit": tot_profit,
			"classification": cat,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_items = len(data)
	tot_rev = sum(d["total_revenue"] for d in data)
	tot_profit = sum(d["total_profit"] for d in data)
	stars = sum(1 for d in data if "Star" in d["classification"])

	return [
		{"value": tot_items, "label": _("Active Menu Items"), "datatype": "Int"},
		{"value": tot_rev, "label": _("Menu Revenue"), "datatype": "Currency", "currency": currency},
		{"value": tot_profit, "label": _("Gross Profit Contribution"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": stars, "label": _("Star Menu Dishes"), "datatype": "Int", "indicator": "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_cat = defaultdict(float)
	for d in data:
		by_cat[d["classification"]] += flt(d["total_profit"])

	labels = list(by_cat.keys())
	vals = [round(by_cat[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Gross Profit"), "values": vals}],
		},
		"type": "donut",
		"colors": ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"],
	}
