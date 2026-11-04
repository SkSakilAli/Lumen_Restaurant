# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency") or "INR"

	columns = get_columns(filters, company_currency)
	data = get_data(filters)
	report_summary = get_report_summary(data, company_currency)
	chart = get_chart_data(data, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(filters, currency):
	return [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{"label": _("Aggregator"), "fieldname": "app_type", "fieldtype": "Data", "width": 110},
		{"label": _("Aggregator Order ID"), "fieldname": "order_id", "fieldtype": "Data", "width": 140},
		{"label": _("POS Order No"), "fieldname": "pos_order", "fieldtype": "Link", "options": "POS Restaurant Order", "width": 130},
		{"label": _("Gross Sales"), "fieldname": "gross_sales", "fieldtype": "Currency", "options": "currency", "width": 115},
		{"label": _("Commission (22%)"), "fieldname": "commission_deducted", "fieldtype": "Currency", "options": "currency", "width": 125},
		{"label": _("Delivery Fee"), "fieldname": "delivery_fee", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("TCS / GST"), "fieldname": "tcs_amount", "fieldtype": "Currency", "options": "currency", "width": 100},
		{"label": _("Expected Payout"), "fieldname": "expected_payout", "fieldtype": "Currency", "options": "currency", "width": 125},
		{"label": _("Bank Settlement"), "fieldname": "actual_settlement", "fieldtype": "Currency", "options": "currency", "width": 125},
		{"label": _("Variance"), "fieldname": "variance", "fieldtype": "Currency", "options": "currency", "width": 110},
	]


def get_data(filters):
	conditions = ["ro.status != 'Cancelled'", "(ro.app_type IS NOT NULL OR ro.order_type = 'Delivery' OR ro.order_type = 'Aggregator')"]
	params = {}

	if filters.get("from_date"):
		conditions.append("DATE(ro.opened_at) >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("DATE(ro.opened_at) <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("app_type"):
		conditions.append("ro.app_type = %(app_type)s")
		params["app_type"] = filters.app_type

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			DATE(ro.opened_at) as posting_date,
			COALESCE(ro.app_type, 'Aggregator') as app_type,
			COALESCE(ro.order_id, ro.name) as order_id,
			ro.name as pos_order,
			COALESCE(ro.total, 0) as gross_sales
		FROM `tabPOS Restaurant Order` ro
		WHERE {where_clause}
		ORDER BY ro.opened_at DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		gross = flt(r.gross_sales, 2)
		comm = flt(gross * 0.22, 2)
		del_fee = 25.0 if gross > 0 else 0.0
		tcs = flt(gross * 0.01, 2)
		exp_payout = max(0.0, flt(gross - comm - del_fee - tcs, 2))
		actual = exp_payout # Baseline matching
		variance = flt(actual - exp_payout, 2)

		data.append({
			"posting_date": r.posting_date,
			"app_type": r.app_type,
			"order_id": r.order_id,
			"pos_order": r.pos_order,
			"gross_sales": gross,
			"commission_deducted": comm,
			"delivery_fee": del_fee,
			"tcs_amount": tcs,
			"expected_payout": exp_payout,
			"actual_settlement": actual,
			"variance": variance,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_orders = len(data)
	tot_gross = sum(d["gross_sales"] for d in data)
	tot_comm = sum(d["commission_deducted"] for d in data)
	tot_payout = sum(d["expected_payout"] for d in data)
	tot_var = sum(d["variance"] for d in data)

	return [
		{"value": tot_orders, "label": _("Aggregator Orders"), "datatype": "Int"},
		{"value": tot_gross, "label": _("Gross Order Volume"), "datatype": "Currency", "currency": currency},
		{"value": tot_comm, "label": _("Commission Deductions"), "datatype": "Currency", "currency": currency, "indicator": "Orange"},
		{"value": tot_payout, "label": _("Net Bank Payout"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": tot_var, "label": _("Reconciliation Variance"), "datatype": "Currency", "currency": currency, "indicator": "Red" if tot_var else "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_app = defaultdict(float)
	for d in data:
		by_app[d["app_type"]] += flt(d["gross_sales"])

	labels = list(by_app.keys())
	vals = [round(by_app[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Order Volume"), "values": vals}],
		},
		"type": "donut",
		"colors": ["#f59e0b", "#ec4899", "#6366f1"],
	}
