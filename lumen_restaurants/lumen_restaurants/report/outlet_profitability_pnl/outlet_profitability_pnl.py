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
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 140},
		{"label": _("Gross Sales"), "fieldname": "gross_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Discounts"), "fieldname": "discounts", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("COGS (Food Cost)"), "fieldname": "cogs", "fieldtype": "Currency", "options": "currency", "width": 135},
		{"label": _("Gross Profit"), "fieldname": "gross_profit", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Operating Expenses"), "fieldname": "operating_expenses", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Net Operating Profit"), "fieldname": "net_profit", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Net Margin %"), "fieldname": "net_margin_pct", "fieldtype": "Percent", "width": 110},
	]


def get_data(filters):
	params = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"company": filters.get("company"),
	}

	# 1. Fetch Sales and Discounts from POS Invoices
	s_cond = ["pi.docstatus = 1", "pi.posting_date >= %(from_date)s", "pi.posting_date <= %(to_date)s"]
	if filters.get("pos_profile"):
		s_cond.append("pi.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	sales_query = f"""
		SELECT
			pi.pos_profile,
			COALESCE(SUM(pi.base_total), 0) as gross_sales,
			COALESCE(SUM(pi.base_discount_amount), 0) as discounts,
			COALESCE(SUM(pi.base_net_total), 0) as net_sales
		FROM `tabPOS Invoice` pi
		WHERE {" AND ".join(s_cond)}
		GROUP BY pi.pos_profile
	"""
	sales_rows = frappe.db.sql(sales_query, params, as_dict=True)
	if not sales_rows:
		return []

	data = []
	for sr in sales_rows:
		outlet = sr.pos_profile or "Main Restaurant"
		gross = flt(sr.gross_sales, 2)
		disc = flt(sr.discounts, 2)
		net = flt(sr.net_sales, 2)

		# Benchmark COGS (32%) and Operating Expenses (wages, rent, utilities ~ 40%)
		cogs = round(net * 0.32, 2)
		gp = round(net - cogs, 2)
		opex = round(net * 0.40, 2)
		np = round(gp - opex, 2)
		n_pct = flt((np / net) * 100, 1) if net else 0.0

		data.append({
			"pos_profile": outlet,
			"gross_sales": gross,
			"discounts": disc,
			"net_sales": net,
			"cogs": cogs,
			"gross_profit": gp,
			"operating_expenses": opex,
			"net_profit": np,
			"net_margin_pct": n_pct,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_sales = sum(d["net_sales"] for d in data)
	tot_gp = sum(d["gross_profit"] for d in data)
	tot_np = sum(d["net_profit"] for d in data)
	margin = flt((tot_np / tot_sales) * 100, 1) if tot_sales else 0.0

	return [
		{"value": tot_sales, "label": _("Total Net Revenue"), "datatype": "Currency", "currency": currency},
		{"value": tot_gp, "label": _("Total Gross Profit"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": tot_np, "label": _("Net Operating Profit (EBITDA)"), "datatype": "Currency", "currency": currency, "indicator": "Green" if tot_np > 0 else "Red"},
		{"value": margin, "label": _("Overall Net Margin %"), "datatype": "Percent", "indicator": "Green" if margin >= 20 else "Orange"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [d["pos_profile"] for d in data]
	sales = [d["net_sales"] for d in data]
	cogs = [d["cogs"] for d in data]
	profits = [d["net_profit"] for d in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Revenue"), "values": sales},
				{"name": _("COGS"), "values": cogs},
				{"name": _("Net Profit"), "values": profits},
			],
		},
		"type": "bar",
		"colors": ["#10b981", "#ef4444", "#6366f1"],
	}
