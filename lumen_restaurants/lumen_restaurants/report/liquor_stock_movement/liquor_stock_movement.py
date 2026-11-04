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
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Spirit Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 130},
		{"label": _("Bottle Size (ml)"), "fieldname": "bottle_ml", "fieldtype": "Float", "width": 115},
		{"label": _("Opening (Bottles)"), "fieldname": "opening_bottles", "fieldtype": "Float", "width": 125},
		{"label": _("Inward (Bottles)"), "fieldname": "inward_bottles", "fieldtype": "Float", "width": 120},
		{"label": _("Outward (Bottles)"), "fieldname": "outward_bottles", "fieldtype": "Float", "width": 125},
		{"label": _("Closing (Bottles)"), "fieldname": "closing_bottles", "fieldtype": "Float", "width": 125},
		{"label": _("Total ml Depleted"), "fieldname": "ml_consumed", "fieldtype": "Float", "width": 130},
		{"label": _("Pegs (30ml Equiv)"), "fieldname": "pegs_count", "fieldtype": "Int", "width": 130},
	]


def get_data(filters):
	from frappe.utils import add_months, today

	from_date = filters.get("from_date") or add_months(today(), -1)
	to_date = filters.get("to_date") or today()

	conditions = ["sle.is_cancelled = 0"]
	params = {
		"from_date": from_date,
		"to_date": to_date,
	}

	if filters.get("warehouse"):
		conditions.append("sle.warehouse = %(warehouse)s")
		params["warehouse"] = filters.warehouse

	if filters.get("item_code"):
		conditions.append("sle.item_code = %(item_code)s")
		params["item_code"] = filters.item_code

	where_clause = " AND ".join(conditions)

	# Fetch SLEs for items in beverage or liquor item groups, or all
	query = f"""
		SELECT
			sle.item_code,
			i.item_name,
			sle.warehouse,
			COALESCE(i.weight_per_unit * 1000, 750.0) as bottle_ml,
			SUM(CASE WHEN sle.posting_date < %(from_date)s THEN sle.actual_qty ELSE 0 END) as opening_qty,
			SUM(CASE WHEN sle.posting_date >= %(from_date)s AND sle.posting_date <= %(to_date)s AND sle.actual_qty > 0 THEN sle.actual_qty ELSE 0 END) as in_qty,
			SUM(CASE WHEN sle.posting_date >= %(from_date)s AND sle.posting_date <= %(to_date)s AND sle.actual_qty < 0 THEN ABS(sle.actual_qty) ELSE 0 END) as out_qty
		FROM `tabStock Ledger Entry` sle
		JOIN `tabItem` i ON i.name = sle.item_code
		WHERE {where_clause}
		GROUP BY sle.item_code, i.item_name, sle.warehouse, i.weight_per_unit
		HAVING opening_qty != 0 OR in_qty != 0 OR out_qty != 0
		ORDER BY out_qty DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		b_ml = flt(r.bottle_ml, 1) or 750.0
		op = flt(r.opening_qty, 2)
		inp = flt(r.in_qty, 2)
		out = flt(r.out_qty, 2)
		cl = flt(op + inp - out, 2)
		ml_dep = flt(out * b_ml, 1)
		pegs = int(ml_dep / 30.0) if ml_dep else 0

		data.append({
			"item_code": r.item_code,
			"item_name": r.item_name,
			"warehouse": r.warehouse,
			"bottle_ml": b_ml,
			"opening_bottles": op,
			"inward_bottles": inp,
			"outward_bottles": out,
			"closing_bottles": cl,
			"ml_consumed": ml_dep,
			"pegs_count": pegs,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_brands = len(data)
	tot_out_bottles = sum(d["outward_bottles"] for d in data)
	tot_pegs = sum(d["pegs_count"] for d in data)
	tot_liters = flt(sum(d["ml_consumed"] for d in data) / 1000.0, 2)

	return [
		{"value": tot_brands, "label": _("Active Spirits"), "datatype": "Int"},
		{"value": tot_out_bottles, "label": _("Bottles Depleted"), "datatype": "Float", "indicator": "Blue"},
		{"value": tot_liters, "label": _("Total Liters"), "datatype": "Float"},
		{"value": tot_pegs, "label": _("Total Pegs Served"), "datatype": "Int", "indicator": "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [d["item_name"][:14] for d in data[:8]]
	pegs = [d["pegs_count"] for d in data[:8]]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Pegs Served"), "values": pegs}],
		},
		"type": "bar",
		"colors": ["#8b5cf6"],
	}
