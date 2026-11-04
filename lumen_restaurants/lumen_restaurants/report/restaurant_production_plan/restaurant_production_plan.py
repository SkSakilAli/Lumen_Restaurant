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
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{"label": _("Plan ID"), "fieldname": "plan_id", "fieldtype": "Link", "options": "Production Plan", "width": 140},
		{"label": _("Kitchen Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Planned Qty"), "fieldname": "planned_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Produced Qty"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 115},
		{"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	conditions = ["pp.docstatus < 2"]
	params = {}

	if filters.get("company"):
		conditions.append("pp.company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("pp.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("pp.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			pp.posting_date,
			pp.name as plan_id,
			ppi.item_code,
			i.item_name,
			ppi.planned_qty,
			ppi.produced_qty,
			(ppi.planned_qty - ppi.produced_qty) as pending_qty,
			pp.status
		FROM `tabProduction Plan Item` ppi
		JOIN `tabProduction Plan` pp ON pp.name = ppi.parent
		JOIN `tabItem` i ON i.name = ppi.item_code
		WHERE {where_clause}
		ORDER BY pp.posting_date DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		p_qty = flt(r.planned_qty, 2)
		prod = flt(r.produced_qty, 2)
		pend = max(0.0, flt(p_qty - prod, 2))

		data.append({
			"posting_date": r.posting_date,
			"plan_id": r.plan_id,
			"item_code": r.item_code,
			"item_name": r.item_name,
			"planned_qty": p_qty,
			"produced_qty": prod,
			"pending_qty": pend,
			"status": r.status or "In Process",
		})

	return data


def get_report_summary(data):
	if not data:
		return None

	tot_planned = sum(d["planned_qty"] for d in data)
	tot_produced = sum(d["produced_qty"] for d in data)
	tot_pending = sum(d["pending_qty"] for d in data)
	fulfillment = flt((tot_produced / tot_planned) * 100, 1) if tot_planned else 100.0

	return [
		{"value": len(data), "label": _("Prep Batch Items"), "datatype": "Int"},
		{"value": tot_planned, "label": _("Total Planned"), "datatype": "Float"},
		{"value": tot_produced, "label": _("Total Produced"), "datatype": "Float", "indicator": "Green"},
		{"value": fulfillment, "label": _("Prep Completion %"), "datatype": "Percent", "indicator": "Green" if fulfillment >= 85 else "Orange"},
	]


def get_chart_data(data):
	if not data:
		return None

	labels = [d["item_name"][:14] for d in data[:8]]
	planned = [d["planned_qty"] for d in data[:8]]
	produced = [d["produced_qty"] for d in data[:8]]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Planned"), "values": planned},
				{"name": _("Produced"), "values": produced},
			],
		},
		"type": "bar",
		"colors": ["#6366f1", "#10b981"],
	}
