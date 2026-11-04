# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate, time_diff_in_seconds


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company_currency = "USD"
	if filters.get("pos_profile"):
		comp = frappe.get_cached_value("POS Profile", filters.pos_profile, "company")
		if comp:
			company_currency = frappe.get_cached_value("Company", comp, "default_currency") or "USD"

	columns = get_columns(filters, company_currency)
	data = get_data(filters)
	report_summary = get_report_summary(data, company_currency)
	chart = get_chart_data(data, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(filters, currency):
	return [
		{"label": _("Table No"), "fieldname": "table_no", "fieldtype": "Data", "width": 95},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
		{"label": _("Area / Section"), "fieldname": "area", "fieldtype": "Data", "width": 120},
		{"label": _("Seats"), "fieldname": "seats", "fieldtype": "Int", "width": 75},
		{"label": _("Turns (Orders)"), "fieldname": "turns_count", "fieldtype": "Int", "width": 110},
		{"label": _("Covers (Guests)"), "fieldname": "total_covers", "fieldtype": "Int", "width": 115},
		{"label": _("Avg Dining (min)"), "fieldname": "avg_dining_mins", "fieldtype": "Float", "width": 120},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Sales per Cover"), "fieldname": "sales_per_cover", "fieldtype": "Currency", "options": "currency", "width": 125},
		{"label": _("Turnover Rate"), "fieldname": "turnover_rate", "fieldtype": "Float", "width": 110},
	]


def get_data(filters):
	conditions = ["ro.status != 'Cancelled'"]
	params = {}

	if filters.get("from_date"):
		conditions.append("DATE(ro.opened_at) >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("DATE(ro.opened_at) <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("pos_profile"):
		conditions.append("ro.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	if filters.get("area"):
		conditions.append("t.area = %(area)s")
		params["area"] = filters.area

	where_clause = " AND ".join(conditions)

	# Fetch orders per table
	query = f"""
		SELECT
			COALESCE(ro.table_label, t.table_no, 'Unknown') as table_no,
			ro.pos_profile,
			COALESCE(t.area, 'Main Dining') as area,
			COALESCE(t.seats, 4) as seats,
			COUNT(ro.name) as turns_count,
			COALESCE(SUM(ro.guests), COUNT(ro.name) * 2) as total_covers,
			COALESCE(SUM(ro.total), 0) as net_sales,
			AVG(CASE WHEN ro.closed_at IS NOT NULL AND ro.opened_at IS NOT NULL THEN TIMESTAMPDIFF(MINUTE, ro.opened_at, ro.closed_at) ELSE NULL END) as avg_mins
		FROM `tabPOS Restaurant Order` ro
		LEFT JOIN `tabPOS Restaurant Table` t ON t.name = ro.table OR t.table_no = ro.table_label
		WHERE {where_clause}
		GROUP BY COALESCE(ro.table_label, t.table_no, 'Unknown'), ro.pos_profile, COALESCE(t.area, 'Main Dining'), COALESCE(t.seats, 4)
		ORDER BY net_sales DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		turns = int(r.turns_count or 0)
		covers = int(r.total_covers or 0)
		net = flt(r.net_sales, 2)
		spc = flt(net / covers, 2) if covers else 0.0
		avg_mins = flt(r.avg_mins, 1) if r.avg_mins is not None else 45.0

		data.append({
			"table_no": r.table_no,
			"pos_profile": r.pos_profile,
			"area": r.area,
			"seats": int(r.seats or 4),
			"turns_count": turns,
			"total_covers": covers,
			"avg_dining_mins": avg_mins,
			"net_sales": net,
			"sales_per_cover": spc,
			"turnover_rate": turns,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_tables = len(data)
	tot_turns = sum(d["turns_count"] for d in data)
	tot_covers = sum(d["total_covers"] for d in data)
	tot_sales = sum(d["net_sales"] for d in data)
	avg_turns = flt(tot_turns / tot_tables, 1) if tot_tables else 0.0
	avg_spc = flt(tot_sales / tot_covers, 2) if tot_covers else 0.0

	return [
		{"value": tot_tables, "label": _("Active Tables"), "datatype": "Int"},
		{"value": tot_turns, "label": _("Total Turns"), "datatype": "Int"},
		{"value": tot_covers, "label": _("Total Covers"), "datatype": "Int"},
		{"value": avg_turns, "label": _("Avg Turns / Table"), "datatype": "Float", "indicator": "Blue"},
		{"value": tot_sales, "label": _("Total Sales"), "datatype": "Currency", "currency": currency},
		{"value": avg_spc, "label": _("Sales per Cover"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [d["table_no"] for d in data[:12]]
	turns = [d["turns_count"] for d in data[:12]]
	sales = [flt(d["net_sales"], 2) for d in data[:12]]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Turns"), "values": turns},
			],
		},
		"type": "bar",
		"colors": ["#10b981"],
	}
