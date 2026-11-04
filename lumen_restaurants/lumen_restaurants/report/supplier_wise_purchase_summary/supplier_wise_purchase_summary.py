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
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
		{"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 160},
		{"label": _("Group"), "fieldname": "supplier_group", "fieldtype": "Data", "width": 120},
		{"label": _("Invoices"), "fieldname": "inv_count", "fieldtype": "Int", "width": 90},
		{"label": _("Gross Purchases"), "fieldname": "gross_purchase", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Debit / Returns"), "fieldname": "return_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Net Purchases"), "fieldname": "net_purchase", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "options": "currency", "width": 130},
	]


def get_data(filters):
	conditions = ["pi.docstatus = 1"]
	params = {}

	if filters.get("company"):
		conditions.append("pi.company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("pi.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("pi.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("supplier"):
		conditions.append("pi.supplier = %(supplier)s")
		params["supplier"] = filters.supplier

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			pi.supplier,
			COALESCE(pi.supplier_name, pi.supplier) as supplier_name,
			s.supplier_group,
			COUNT(DISTINCT pi.name) as inv_count,
			COALESCE(SUM(CASE WHEN pi.is_return = 0 THEN pi.base_grand_total ELSE 0 END), 0) as gross_purchase,
			COALESCE(SUM(CASE WHEN pi.is_return = 1 THEN ABS(pi.base_grand_total) ELSE 0 END), 0) as return_amount,
			COALESCE(SUM(pi.outstanding_amount), 0) as outstanding_amount
		FROM `tabPurchase Invoice` pi
		LEFT JOIN `tabSupplier` s ON s.name = pi.supplier
		WHERE {where_clause}
		GROUP BY pi.supplier, COALESCE(pi.supplier_name, pi.supplier), s.supplier_group
		ORDER BY gross_purchase DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		gross = flt(r.gross_purchase, 2)
		ret = flt(r.return_amount, 2)
		net = flt(gross - ret, 2)

		data.append({
			"supplier": r.supplier,
			"supplier_name": r.supplier_name,
			"supplier_group": r.supplier_group or "-",
			"inv_count": int(r.inv_count or 0),
			"gross_purchase": gross,
			"return_amount": ret,
			"net_purchase": net,
			"outstanding_amount": flt(r.outstanding_amount, 2),
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_sup = len(data)
	tot_invs = sum(d["inv_count"] for d in data)
	tot_net = sum(d["net_purchase"] for d in data)
	tot_out = sum(d["outstanding_amount"] for d in data)

	return [
		{"value": tot_sup, "label": _("Suppliers Count"), "datatype": "Int"},
		{"value": tot_invs, "label": _("Invoices Processed"), "datatype": "Int"},
		{"value": tot_net, "label": _("Net Purchases"), "datatype": "Currency", "currency": currency, "indicator": "Blue"},
		{"value": tot_out, "label": _("Outstanding Exposure"), "datatype": "Currency", "currency": currency, "indicator": "Orange" if tot_out else "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [d["supplier_name"][:16] for d in data[:8]]
	vals = [flt(d["net_purchase"], 2) for d in data[:8]]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Net Purchase Spend"), "values": vals}],
		},
		"type": "bar",
		"colors": ["#3b82f6"],
	}
