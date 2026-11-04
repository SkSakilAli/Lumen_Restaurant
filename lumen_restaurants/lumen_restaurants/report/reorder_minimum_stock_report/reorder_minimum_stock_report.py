# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns(filters)
	data = get_data(filters)
	report_summary = get_report_summary(data)
	chart = get_chart_data(data)

	return columns, data, None, chart, report_summary


def get_columns(filters):
	return [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 130},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Current Stock"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Reorder Level"), "fieldname": "reorder_level", "fieldtype": "Float", "width": 110},
		{"label": _("Shortage"), "fieldname": "shortage_qty", "fieldtype": "Float", "width": 105},
		{"label": _("Suggested Order Qty"), "fieldname": "reorder_qty", "fieldtype": "Float", "width": 140},
	]


def get_data(filters):
	conditions = ["1=1"]
	params = {}

	if filters.get("warehouse"):
		conditions.append("ir.warehouse = %(warehouse)s")
		params["warehouse"] = filters.warehouse

	if filters.get("item_group"):
		conditions.append("i.item_group = %(item_group)s")
		params["item_group"] = filters.item_group

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			ir.parent as item_code,
			i.item_name,
			i.item_group,
			ir.warehouse,
			i.stock_uom,
			COALESCE(b.actual_qty, 0) as actual_qty,
			ir.warehouse_reorder_level as reorder_level,
			ir.warehouse_reorder_qty as reorder_qty
		FROM `tabItem Reorder` ir
		JOIN `tabItem` i ON i.name = ir.parent
		LEFT JOIN `tabBin` b ON b.item_code = ir.parent AND b.warehouse = ir.warehouse
		WHERE {where_clause}
		ORDER BY (COALESCE(b.actual_qty, 0) - ir.warehouse_reorder_level) ASC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		curr = flt(r.actual_qty, 2)
		lvl = flt(r.reorder_level, 2)
		shortage = flt(lvl - curr, 2) if curr < lvl else 0.0

		data.append({
			"item_code": r.item_code,
			"item_name": r.item_name,
			"item_group": r.item_group,
			"warehouse": r.warehouse,
			"stock_uom": r.stock_uom,
			"actual_qty": curr,
			"reorder_level": lvl,
			"shortage_qty": shortage,
			"reorder_qty": flt(r.reorder_qty, 2) or shortage,
		})

	return data


def get_report_summary(data):
	if not data:
		return None

	tot_items = len(data)
	critical_items = sum(1 for d in data if d["shortage_qty"] > 0)

	return [
		{"value": tot_items, "label": _("Configured Reorder Items"), "datatype": "Int"},
		{"value": critical_items, "label": _("Below Reorder Level"), "datatype": "Int", "indicator": "Red" if critical_items else "Green"},
	]


def get_chart_data(data):
	if not data:
		return None

	critical = [d for d in data if d["shortage_qty"] > 0][:8]
	if not critical:
		return None

	labels = [d["item_name"][:14] for d in critical]
	shortages = [d["shortage_qty"] for d in critical]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Shortage Qty"), "values": shortages}],
		},
		"type": "bar",
		"colors": ["#ef4444"],
	}
