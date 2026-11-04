# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate, date_diff, nowdate


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
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 130},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"label": _("Current Stock"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "options": "currency", "width": 115},
		{"label": _("Dead Capital"), "fieldname": "stock_value", "fieldtype": "Currency", "options": "currency", "width": 125},
		{"label": _("Last Active Date"), "fieldname": "last_movement_date", "fieldtype": "Date", "width": 115},
		{"label": _("Days Inactive"), "fieldname": "days_inactive", "fieldtype": "Int", "width": 110},
		{"label": _("Classification"), "fieldname": "status", "fieldtype": "Data", "width": 120},
	]


def get_data(filters):
	conditions = ["b.actual_qty > 0"]
	params = {}

	if filters.get("warehouse"):
		conditions.append("b.warehouse = %(warehouse)s")
		params["warehouse"] = filters.warehouse

	if filters.get("item_group"):
		conditions.append("i.item_group = %(item_group)s")
		params["item_group"] = filters.item_group

	where_clause = " AND ".join(conditions)

	# Fetch bins with positive stock and their last outward transaction date
	query = f"""
		SELECT
			b.item_code,
			i.item_name,
			i.item_group,
			b.warehouse,
			b.actual_qty,
			b.valuation_rate,
			b.stock_value,
			(
				SELECT MAX(sle.posting_date)
				FROM `tabStock Ledger Entry` sle
				WHERE sle.item_code = b.item_code AND sle.warehouse = b.warehouse AND sle.actual_qty < 0 AND sle.is_cancelled = 0
			) as last_outward_date,
			(
				SELECT MAX(sle2.posting_date)
				FROM `tabStock Ledger Entry` sle2
				WHERE sle2.item_code = b.item_code AND sle2.warehouse = b.warehouse AND sle2.is_cancelled = 0
			) as last_movement_date
		FROM `tabBin` b
		JOIN `tabItem` i ON i.name = b.item_code
		WHERE {where_clause}
		ORDER BY b.stock_value DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	threshold = int(filters.get("inactive_days") or 30)
	today = nowdate()

	data = []
	for r in rows:
		lm_date = r.last_outward_date or r.last_movement_date or today
		days = date_diff(today, lm_date)

		if days < threshold:
			continue

		status = "Non-Moving (>90d)" if days >= 90 else ("Slow-Moving (>60d)" if days >= 60 else "Slow-Moving (>30d)")
		val = flt(r.stock_value, 2) if r.stock_value else flt(r.actual_qty) * flt(r.valuation_rate)

		data.append({
			"item_code": r.item_code,
			"item_name": r.item_name,
			"item_group": r.item_group,
			"warehouse": r.warehouse,
			"actual_qty": flt(r.actual_qty, 2),
			"valuation_rate": flt(r.valuation_rate, 2),
			"stock_value": flt(val, 2),
			"last_movement_date": lm_date,
			"days_inactive": days,
			"status": status,
		})

	data.sort(key=lambda x: x["days_inactive"], reverse=True)
	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_items = len(data)
	tot_dead_capital = sum(d["stock_value"] for d in data)
	non_moving_count = sum(1 for d in data if d["days_inactive"] >= 90)

	return [
		{"value": tot_items, "label": _("Inactive Items"), "datatype": "Int"},
		{"value": tot_dead_capital, "label": _("Locked Inventory Capital"), "datatype": "Currency", "currency": currency, "indicator": "Red"},
		{"value": non_moving_count, "label": _("Critical Non-Moving (>90d)"), "datatype": "Int", "indicator": "Orange"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_status = defaultdict(float)
	for d in data:
		by_status[d["status"]] += flt(d["stock_value"])

	labels = list(by_status.keys())
	vals = [round(by_status[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Tied-up Capital"), "values": vals}],
		},
		"type": "donut",
		"colors": ["#ef4444", "#f59e0b", "#6366f1"],
	}
