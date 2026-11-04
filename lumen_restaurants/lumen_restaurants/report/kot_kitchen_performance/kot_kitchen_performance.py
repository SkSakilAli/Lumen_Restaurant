# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate, time_diff_in_seconds


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns(filters)
	data = get_data(filters)
	report_summary = get_report_summary(data)
	chart = get_chart_data(data)

	return columns, data, None, chart, report_summary


def get_columns(filters):
	return [
		{"label": _("Date"), "fieldname": "business_date", "fieldtype": "Date", "width": 95},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
		{"label": _("KOT No"), "fieldname": "kot_no", "fieldtype": "Link", "options": "POS Kitchen Ticket", "width": 140},
		{"label": _("Order No"), "fieldname": "order_no", "fieldtype": "Data", "width": 110},
		{"label": _("Table"), "fieldname": "table_label", "fieldtype": "Data", "width": 80},
		{"label": _("Station"), "fieldname": "station", "fieldtype": "Data", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("Fired At"), "fieldname": "created_at", "fieldtype": "Datetime", "width": 135},
		{"label": _("Ready At"), "fieldname": "ready_at", "fieldtype": "Datetime", "width": 135},
		{"label": _("Prep Time (min)"), "fieldname": "prep_mins", "fieldtype": "Float", "width": 115},
		{"label": _("SLA (min)"), "fieldname": "sla_mins", "fieldtype": "Int", "width": 85},
		{"label": _("Delay (min)"), "fieldname": "delay_mins", "fieldtype": "Float", "width": 105},
	]


def get_data(filters):
	conditions = ["1=1"]
	params = {}

	if filters.get("from_date"):
		conditions.append("DATE(kt.creation) >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("DATE(kt.creation) <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("pos_profile"):
		conditions.append("kt.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	if filters.get("station"):
		conditions.append("kt.station = %(station)s")
		params["station"] = filters.station

	if filters.get("status"):
		conditions.append("kt.status = %(status)s")
		params["status"] = filters.status

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			DATE(kt.creation) as business_date,
			kt.pos_profile,
			kt.name as kot_no,
			kt.order_no,
			kt.table_label,
			kt.station,
			kt.status,
			COALESCE(kt.created_at, kt.creation) as created_at,
			kt.started_at,
			kt.ready_at
		FROM `tabPOS Kitchen Ticket` kt
		WHERE {where_clause}
		ORDER BY kt.creation DESC
	"""
	tickets = frappe.db.sql(query, params, as_dict=True)

	standard_sla_mins = 15.0

	data = []
	for t in tickets:
		prep_mins = 0.0
		delay_mins = 0.0

		if t.created_at and t.ready_at:
			try:
				sec = time_diff_in_seconds(t.ready_at, t.created_at)
				prep_mins = flt(sec / 60.0, 1)
				if prep_mins > standard_sla_mins:
					delay_mins = flt(prep_mins - standard_sla_mins, 1)
			except Exception:
				pass

		data.append({
			"business_date": t.business_date,
			"pos_profile": t.pos_profile,
			"kot_no": t.kot_no,
			"order_no": t.order_no or "-",
			"table_label": t.table_label or "-",
			"station": t.station or "Kitchen",
			"status": t.status or "Pending",
			"created_at": t.created_at,
			"ready_at": t.ready_at,
			"prep_mins": prep_mins,
			"sla_mins": int(standard_sla_mins),
			"delay_mins": delay_mins,
		})

	return data


def get_report_summary(data):
	if not data:
		return None

	tot_tickets = len(data)
	completed = [d for d in data if d["prep_mins"] > 0]
	avg_prep = flt(sum(d["prep_mins"] for d in completed) / len(completed), 1) if completed else 0.0
	delayed_count = sum(1 for d in data if d["delay_mins"] > 0)
	on_time_pct = flt(((len(completed) - delayed_count) / len(completed)) * 100, 1) if completed else 100.0

	return [
		{"value": tot_tickets, "label": _("Total KOTs"), "datatype": "Int"},
		{"value": avg_prep, "label": _("Avg Prep Time (mins)"), "datatype": "Float", "indicator": "Green" if avg_prep <= 15 else "Orange"},
		{"value": delayed_count, "label": _("Delayed Tickets (>15m)"), "datatype": "Int", "indicator": "Red" if delayed_count else "Green"},
		{"value": on_time_pct, "label": _("On-Time SLA %"), "datatype": "Percent", "indicator": "Green" if on_time_pct >= 90 else "Red"},
	]


def get_chart_data(data):
	if not data:
		return None

	by_station = defaultdict(lambda: {"total_prep": 0.0, "count": 0})
	for d in data:
		if d["prep_mins"] > 0:
			st = d["station"] or "Kitchen"
			by_station[st]["total_prep"] += d["prep_mins"]
			by_station[st]["count"] += 1

	labels = list(by_station.keys())
	avg_vals = [flt(by_station[k]["total_prep"] / by_station[k]["count"], 1) if by_station[k]["count"] else 0 for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Avg Prep Minutes"), "values": avg_vals}],
		},
		"type": "bar",
		"colors": ["#6366f1"],
	}
