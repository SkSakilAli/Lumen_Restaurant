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
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
		{"label": _("First Visit"), "fieldname": "first_visit", "fieldtype": "Date", "width": 100},
		{"label": _("Last Visit"), "fieldname": "last_visit", "fieldtype": "Date", "width": 100},
		{"label": _("Visits (Bills)"), "fieldname": "visit_count", "fieldtype": "Int", "width": 100},
		{"label": _("Gross Spend"), "fieldname": "gross_spend", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Discounts Given"), "fieldname": "discount_spend", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Net Spend"), "fieldname": "net_spend", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Avg Spend / Visit"), "fieldname": "avg_spend", "fieldtype": "Currency", "options": "currency", "width": 130},
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

	if filters.get("customer"):
		conditions.append("inv.customer = %(customer)s")
		params["customer"] = filters.customer

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			inv.customer,
			COALESCE(inv.customer_name, inv.customer) as customer_name,
			MIN(inv.posting_date) as first_visit,
			MAX(inv.posting_date) as last_visit,
			COUNT(DISTINCT inv.name) as visit_count,
			COALESCE(SUM(inv.base_total), 0) as gross_spend,
			COALESCE(SUM(inv.base_discount_amount), 0) as discount_spend,
			COALESCE(SUM(inv.base_net_total), 0) as net_spend
		FROM `tabPOS Invoice` inv
		WHERE {where_clause}
		GROUP BY inv.customer, COALESCE(inv.customer_name, inv.customer)
		HAVING visit_count >= %(min_visits)s
		ORDER BY net_spend DESC
	"""
	params["min_visits"] = int(filters.get("min_visits") or 1)
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		visits = int(r.visit_count or 0)
		net = flt(r.net_spend, 2)
		avg = flt(net / visits, 2) if visits else 0.0

		data.append({
			"customer": r.customer,
			"customer_name": r.customer_name or "Walk-in Guest",
			"first_visit": r.first_visit,
			"last_visit": r.last_visit,
			"visit_count": visits,
			"gross_spend": flt(r.gross_spend, 2),
			"discount_spend": flt(r.discount_spend, 2),
			"net_spend": net,
			"avg_spend": avg,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_cust = len(data)
	tot_visits = sum(d["visit_count"] for d in data)
	tot_spend = sum(d["net_spend"] for d in data)
	avg_spend = flt(tot_spend / tot_visits, 2) if tot_visits else 0.0

	return [
		{"value": tot_cust, "label": _("Unique Guests"), "datatype": "Int"},
		{"value": tot_visits, "label": _("Total Visits"), "datatype": "Int"},
		{"value": tot_spend, "label": _("Total Spend"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": avg_spend, "label": _("Avg Spend / Visit"), "datatype": "Currency", "currency": currency},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [d["customer_name"][:16] for d in data[:8]]
	spend = [flt(d["net_spend"], 2) for d in data[:8]]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Net Spend"), "values": spend}],
		},
		"type": "bar",
		"colors": ["#6366f1"],
	}
