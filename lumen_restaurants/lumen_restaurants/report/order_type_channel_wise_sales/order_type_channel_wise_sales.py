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
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 140},
		{"label": _("Order Type"), "fieldname": "order_type", "fieldtype": "Data", "width": 120},
		{"label": _("Channel"), "fieldname": "channel", "fieldtype": "Data", "width": 120},
		{"label": _("Orders"), "fieldname": "order_count", "fieldtype": "Int", "width": 80},
		{"label": _("Gross Sales"), "fieldname": "gross_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Restaurant Discount"), "fieldname": "rest_discount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Platform Discount"), "fieldname": "platform_discount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Avg Order Value"), "fieldname": "aov", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Cancelled Orders"), "fieldname": "cancelled_count", "fieldtype": "Int", "width": 110},
		{"label": _("Share %"), "fieldname": "share_pct", "fieldtype": "Percent", "width": 90},
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

	if filters.get("pos_profile"):
		conditions.append("inv.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	where_clause = " AND ".join(conditions)

	# Join POS Invoice with POS Restaurant Order to identify channel and order type
	# If POS Restaurant Order is not linked, fallback to order_type on invoice or 'Dine In'
	query = f"""
		SELECT
			inv.posting_date,
			inv.pos_profile,
			COALESCE(ro.order_type, 'Dine In') as order_type,
			COALESCE(ro.app_type, 'Direct') as channel,
			COUNT(DISTINCT inv.name) as order_count,
			COALESCE(SUM(inv.base_total), 0) as gross_sales,
			COALESCE(SUM(inv.base_discount_amount), 0) as rest_discount,
			0.0 as platform_discount,
			COALESCE(SUM(inv.base_net_total), 0) as net_sales
		FROM `tabPOS Invoice` inv
		LEFT JOIN `tabPOS Restaurant Order` ro ON ro.invoices LIKE CONCAT('%%', inv.name, '%%')
		WHERE {where_clause}
		GROUP BY inv.posting_date, inv.pos_profile, COALESCE(ro.order_type, 'Dine In'), COALESCE(ro.app_type, 'Direct')
		ORDER BY inv.posting_date DESC, net_sales DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	# Fetch cancelled orders count
	cancelled_counts = defaultdict(int)
	try:
		c_query = f"""
			SELECT
				DATE(ro.opened_at) as p_date,
				ro.pos_profile,
				COALESCE(ro.order_type, 'Dine In') as order_type,
				COALESCE(ro.app_type, 'Direct') as channel,
				COUNT(ro.name) as c_count
			FROM `tabPOS Restaurant Order` ro
			WHERE ro.status = 'Cancelled'
				AND DATE(ro.opened_at) >= %(from_date)s
				AND DATE(ro.opened_at) <= %(to_date)s
			GROUP BY DATE(ro.opened_at), ro.pos_profile, ro.order_type, ro.app_type
		"""
		for cr in frappe.db.sql(c_query, params, as_dict=True):
			k = (cr.p_date, cr.pos_profile, cr.order_type, cr.channel)
			cancelled_counts[k] = cr.c_count
	except Exception:
		pass

	tot_net = sum(flt(r.net_sales) for r in rows)

	data = []
	for r in rows:
		k = (r.posting_date, r.pos_profile, r.order_type, r.channel)
		order_count = int(r.order_count or 0)
		net = flt(r.net_sales, 2)
		aov = flt(net / order_count, 2) if order_count else 0
		share = flt((net / tot_net) * 100, 2) if tot_net else 0

		data.append({
			"posting_date": r.posting_date,
			"pos_profile": r.pos_profile,
			"order_type": r.order_type,
			"channel": r.channel,
			"order_count": order_count,
			"gross_sales": flt(r.gross_sales, 2),
			"rest_discount": flt(r.rest_discount, 2),
			"platform_discount": 0.0,
			"net_sales": net,
			"aov": aov,
			"cancelled_count": cancelled_counts.get(k, 0),
			"share_pct": share,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_orders = sum(d["order_count"] for d in data)
	tot_gross = sum(d["gross_sales"] for d in data)
	tot_disc = sum(d["rest_discount"] for d in data)
	tot_net = sum(d["net_sales"] for d in data)
	tot_cancelled = sum(d["cancelled_count"] for d in data)
	avg_aov = flt(tot_net / tot_orders, 2) if tot_orders else 0

	return [
		{"value": tot_orders, "label": _("Total Orders"), "datatype": "Int"},
		{"value": tot_gross, "label": _("Gross Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_disc, "label": _("Discounts"), "datatype": "Currency", "currency": currency},
		{"value": tot_net, "label": _("Net Sales"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": avg_aov, "label": _("Avg Order Value"), "datatype": "Currency", "currency": currency},
		{"value": tot_cancelled, "label": _("Cancelled Orders"), "datatype": "Int", "indicator": "Red" if tot_cancelled else "Grey"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_channel = defaultdict(float)
	for d in data:
		lbl = f"{d['order_type']} ({d['channel']})"
		by_channel[lbl] += flt(d["net_sales"])

	labels = list(by_channel.keys())
	values = [round(v, 2) for v in by_channel.values()]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Net Sales"), "values": values}],
		},
		"type": "donut",
		"colors": ["#10b981", "#6366f1", "#f59e0b", "#ec4899", "#8b5cf6"],
	}
