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
		{"label": _("Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 130},
		{"label": _("Kitchen Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"label": _("Consumed Qty"), "fieldname": "consumed_qty", "fieldtype": "Float", "width": 115},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Total Cost"), "fieldname": "consumed_cost", "fieldtype": "Currency", "options": "currency", "width": 130},
	]


def get_data(filters):
	conditions = ["se.docstatus = 1", "(se.purpose = 'Material Issue' OR se.purpose = 'Manufacture')"]
	params = {}

	if filters.get("company"):
		conditions.append("se.company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("se.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("se.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("warehouse"):
		conditions.append("sed.s_warehouse = %(warehouse)s")
		params["warehouse"] = filters.warehouse

	if filters.get("item_code"):
		conditions.append("sed.item_code = %(item_code)s")
		params["item_code"] = filters.item_code

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			sed.item_code,
			sed.item_name,
			i.item_group,
			sed.s_warehouse as warehouse,
			sed.uom,
			SUM(sed.qty) as consumed_qty,
			SUM(sed.amount) as consumed_cost
		FROM `tabStock Entry Detail` sed
		JOIN `tabStock Entry` se ON se.name = sed.parent
		JOIN `tabItem` i ON i.name = sed.item_code
		WHERE {where_clause}
		GROUP BY sed.item_code, sed.item_name, i.item_group, sed.s_warehouse, sed.uom
		ORDER BY consumed_cost DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		data.append({
			"item_code": r.item_code,
			"item_name": r.item_name,
			"item_group": r.item_group,
			"warehouse": r.warehouse,
			"uom": r.uom,
			"consumed_qty": flt(r.consumed_qty, 2),
			"consumed_cost": flt(r.consumed_cost, 2),
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_items = len(data)
	tot_cost = sum(d["consumed_cost"] for d in data)

	return [
		{"value": tot_items, "label": _("Ingredients Consumed"), "datatype": "Int"},
		{"value": tot_cost, "label": _("Total Kitchen Consumption Cost"), "datatype": "Currency", "currency": currency, "indicator": "Blue"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [d["item_name"][:14] for d in data[:8]]
	costs = [d["consumed_cost"] for d in data[:8]]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Consumption Cost"), "values": costs}],
		},
		"type": "bar",
		"colors": ["#10b981"],
	}
