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
		{"label": _("Invoice Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{"label": _("Invoice No"), "fieldname": "invoice_no", "fieldtype": "Link", "options": "Purchase Invoice", "width": 140},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 130},
		{"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 150},
		{"label": _("Supplier GSTIN"), "fieldname": "tax_id", "fieldtype": "Data", "width": 130},
		{"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Taxes"), "fieldname": "taxes_and_charges", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
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
			pi.posting_date,
			pi.name as invoice_no,
			pi.supplier,
			pi.supplier_name,
			pi.tax_id,
			pi.base_net_total as net_total,
			pi.base_total_taxes_and_charges as taxes_and_charges,
			pi.base_grand_total as grand_total,
			pi.outstanding_amount,
			pi.is_return
		FROM `tabPurchase Invoice` pi
		WHERE {where_clause}
		ORDER BY pi.posting_date DESC, pi.name DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		sign = -1.0 if r.is_return else 1.0
		data.append({
			"posting_date": r.posting_date,
			"invoice_no": r.invoice_no,
			"supplier": r.supplier,
			"supplier_name": r.supplier_name or r.supplier,
			"tax_id": r.tax_id or "-",
			"net_total": flt(r.net_total * sign, 2),
			"taxes_and_charges": flt(r.taxes_and_charges * sign, 2),
			"grand_total": flt(r.grand_total * sign, 2),
			"outstanding_amount": flt(r.outstanding_amount, 2),
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_invs = len(data)
	tot_net = sum(d["net_total"] for d in data)
	tot_tax = sum(d["taxes_and_charges"] for d in data)
	tot_grand = sum(d["grand_total"] for d in data)
	tot_out = sum(d["outstanding_amount"] for d in data)

	return [
		{"value": tot_invs, "label": _("Total Invoices"), "datatype": "Int"},
		{"value": tot_net, "label": _("Taxable Purchases"), "datatype": "Currency", "currency": currency},
		{"value": tot_tax, "label": _("Purchase Tax (ITC)"), "datatype": "Currency", "currency": currency},
		{"value": tot_grand, "label": _("Total Invoiced"), "datatype": "Currency", "currency": currency, "indicator": "Blue"},
		{"value": tot_out, "label": _("Outstanding Dues"), "datatype": "Currency", "currency": currency, "indicator": "Orange" if tot_out else "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_date = defaultdict(float)
	for d in data[:25]:
		by_date[str(d["posting_date"])] += flt(d["grand_total"])

	labels = list(by_date.keys())
	vals = [round(by_date[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Purchase Volume"), "values": vals}],
		},
		"type": "bar",
		"colors": ["#3b82f6"],
	}
