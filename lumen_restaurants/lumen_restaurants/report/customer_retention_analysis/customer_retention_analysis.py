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
		{"label": _("Month / Cohort"), "fieldname": "month_label", "fieldtype": "Data", "width": 130},
		{"label": _("Total Guests"), "fieldname": "total_guests", "fieldtype": "Int", "width": 110},
		{"label": _("New Guests"), "fieldname": "new_guests", "fieldtype": "Int", "width": 105},
		{"label": _("Repeat Guests"), "fieldname": "repeat_guests", "fieldtype": "Int", "width": 115},
		{"label": _("Retention Rate %"), "fieldname": "retention_pct", "fieldtype": "Percent", "width": 125},
		{"label": _("New Guest Spend"), "fieldname": "new_spend", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Repeat Guest Spend"), "fieldname": "repeat_spend", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Total Revenue"), "fieldname": "total_spend", "fieldtype": "Currency", "options": "currency", "width": 130},
	]


def get_data(filters):
	conditions = ["inv.docstatus = 1", "inv.customer IS NOT NULL"]
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

	where_clause = " AND ".join(conditions)

	# Fetch monthly bills by customer
	query = f"""
		SELECT
			DATE_FORMAT(inv.posting_date, '%%Y-%%m') as month_str,
			inv.customer,
			COALESCE(SUM(inv.base_net_total), 0) as net_spend,
			(
				SELECT MIN(DATE_FORMAT(i2.posting_date, '%%Y-%%m'))
				FROM `tabPOS Invoice` i2
				WHERE i2.customer = inv.customer AND i2.docstatus = 1
			) as first_month
		FROM `tabPOS Invoice` inv
		WHERE {where_clause}
		GROUP BY DATE_FORMAT(inv.posting_date, '%%Y-%%m'), inv.customer
		ORDER BY month_str ASC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	months_map = defaultdict(lambda: {
		"new_cust": set(),
		"repeat_cust": set(),
		"new_spend": 0.0,
		"repeat_spend": 0.0,
	})

	for r in rows:
		m = r.month_str
		cust = r.customer
		spend = flt(r.net_spend, 2)
		if r.first_month == m:
			months_map[m]["new_cust"].add(cust)
			months_map[m]["new_spend"] += spend
		else:
			months_map[m]["repeat_cust"].add(cust)
			months_map[m]["repeat_spend"] += spend

	data = []
	for m_str in sorted(months_map.keys(), reverse=True):
		val = months_map[m_str]
		n_count = len(val["new_cust"])
		r_count = len(val["repeat_cust"])
		tot_g = n_count + r_count
		ret_pct = flt((r_count / tot_g) * 100, 1) if tot_g else 0.0
		n_sp = flt(val["new_spend"], 2)
		r_sp = flt(val["repeat_spend"], 2)

		data.append({
			"month_label": m_str,
			"total_guests": tot_g,
			"new_guests": n_count,
			"repeat_guests": r_count,
			"retention_pct": ret_pct,
			"new_spend": n_sp,
			"repeat_spend": r_sp,
			"total_spend": n_sp + r_sp,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_new = sum(d["new_guests"] for d in data)
	tot_repeat = sum(d["repeat_guests"] for d in data)
	tot_g = tot_new + tot_repeat
	avg_ret = flt((tot_repeat / tot_g) * 100, 1) if tot_g else 0.0
	tot_rev = sum(d["total_spend"] for d in data)

	return [
		{"value": tot_g, "label": _("Total Guests Analyzed"), "datatype": "Int"},
		{"value": tot_new, "label": _("New Guests Acquired"), "datatype": "Int", "indicator": "Blue"},
		{"value": tot_repeat, "label": _("Repeat / Loyal Guests"), "datatype": "Int", "indicator": "Green"},
		{"value": avg_ret, "label": _("Average Retention %"), "datatype": "Percent", "indicator": "Green" if avg_ret >= 30 else "Orange"},
		{"value": tot_rev, "label": _("Total Guest Spend"), "datatype": "Currency", "currency": currency},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [d["month_label"] for d in data[:6]][::-1]
	new_g = [d["new_guests"] for d in data[:6]][::-1]
	rep_g = [d["repeat_guests"] for d in data[:6]][::-1]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("New Guests"), "values": new_g},
				{"name": _("Repeat Guests"), "values": rep_g},
			],
		},
		"type": "bar",
		"colors": ["#3b82f6", "#10b981"],
	}
