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
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{"label": _("Bill No"), "fieldname": "invoice_no", "fieldtype": "Link", "options": "POS Invoice", "width": 140},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
		{"label": _("Cashier"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 130},
		{"label": _("Gross Sales"), "fieldname": "gross_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Discount Amount"), "fieldname": "discount_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Discount %"), "fieldname": "discount_pct", "fieldtype": "Percent", "width": 95},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
	]


def get_data(filters):
	conditions = ["inv.docstatus = 1", "inv.base_discount_amount > 0"]
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

	if filters.get("owner"):
		conditions.append("inv.owner = %(owner)s")
		params["owner"] = filters.owner

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			inv.posting_date,
			inv.name as invoice_no,
			inv.pos_profile,
			inv.owner,
			inv.customer_name,
			inv.base_total as gross_sales,
			inv.base_discount_amount as discount_amount,
			inv.base_net_total as net_sales
		FROM `tabPOS Invoice` inv
		WHERE {where_clause}
		ORDER BY inv.posting_date DESC, inv.base_discount_amount DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		gross = flt(r.gross_sales, 2)
		disc = flt(r.discount_amount, 2)
		net = flt(r.net_sales, 2)
		pct = flt((disc / gross) * 100, 2) if gross else 0.0

		data.append({
			"posting_date": r.posting_date,
			"invoice_no": r.invoice_no,
			"pos_profile": r.pos_profile,
			"owner": r.owner,
			"customer_name": r.customer_name or "Walk-in Guest",
			"gross_sales": gross,
			"discount_amount": disc,
			"discount_pct": pct,
			"net_sales": net,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_bills = len(data)
	tot_gross = sum(d["gross_sales"] for d in data)
	tot_disc = sum(d["discount_amount"] for d in data)
	avg_pct = flt((tot_disc / tot_gross) * 100, 2) if tot_gross else 0.0

	return [
		{"value": tot_bills, "label": _("Discounted Bills"), "datatype": "Int"},
		{"value": tot_gross, "label": _("Gross Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_disc, "label": _("Total Discounts"), "datatype": "Currency", "currency": currency, "indicator": "Orange"},
		{"value": avg_pct, "label": _("Overall Discount %"), "datatype": "Percent"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_cashier = defaultdict(float)
	for d in data:
		by_cashier[d["owner"] or "Other"] += flt(d["discount_amount"])

	labels = list(by_cashier.keys())[:8]
	vals = [round(by_cashier[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Discount Value"), "values": vals}],
		},
		"type": "bar",
		"colors": ["#f59e0b"],
	}
