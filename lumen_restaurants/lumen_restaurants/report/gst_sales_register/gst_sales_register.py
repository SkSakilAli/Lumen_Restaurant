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
		{"label": _("Invoice Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{"label": _("Invoice No"), "fieldname": "invoice_no", "fieldtype": "Link", "options": "POS Invoice", "width": 140},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
		{"label": _("Type"), "fieldname": "customer_type", "fieldtype": "Data", "width": 70},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 140},
		{"label": _("GSTIN"), "fieldname": "tax_id", "fieldtype": "Data", "width": 130},
		{"label": _("Place of Supply"), "fieldname": "place_of_supply", "fieldtype": "Data", "width": 120},
		{"label": _("Taxable Value"), "fieldname": "taxable_value", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("CGST"), "fieldname": "cgst", "fieldtype": "Currency", "options": "currency", "width": 100},
		{"label": _("SGST"), "fieldname": "sgst", "fieldtype": "Currency", "options": "currency", "width": 100},
		{"label": _("IGST"), "fieldname": "igst", "fieldtype": "Currency", "options": "currency", "width": 100},
		{"label": _("Cess"), "fieldname": "cess", "fieldtype": "Currency", "options": "currency", "width": 90},
		{"label": _("Round Off"), "fieldname": "round_off", "fieldtype": "Currency", "options": "currency", "width": 90},
		{"label": _("Invoice Total"), "fieldname": "invoice_total", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Credit Note Ref"), "fieldname": "return_against", "fieldtype": "Data", "width": 130},
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

	# Fetch Invoices
	query = f"""
		SELECT
			inv.name as invoice_no,
			inv.posting_date,
			inv.pos_profile,
			inv.customer_name,
			inv.tax_id,
			inv.base_net_total as taxable_value,
			inv.base_total_taxes_and_charges as total_tax,
			inv.base_rounding_adjustment as round_off,
			COALESCE(inv.base_rounded_total, inv.base_grand_total, 0) as invoice_total,
			inv.return_against,
			inv.is_return
		FROM `tabPOS Invoice` inv
		WHERE {where_clause}
		ORDER BY inv.posting_date DESC, inv.name DESC
	"""
	invoices = frappe.db.sql(query, params, as_dict=True)
	if not invoices:
		return []

	inv_names = [i.invoice_no for i in invoices]

	# Fetch tax breakups from Sales Taxes and Charges
	taxes_map = defaultdict(lambda: {"cgst": 0.0, "sgst": 0.0, "igst": 0.0, "cess": 0.0})
	try:
		taxes = frappe.db.sql(
			"""
			SELECT
				parent,
				description,
				account_head,
				base_tax_amount_after_discount_amount as tax_amount
			FROM `tabSales Taxes and Charges`
			WHERE parenttype = 'POS Invoice' AND parent IN %s
			""",
			[inv_names],
			as_dict=True,
		)
		for t in taxes:
			desc = (t.description or "").upper() + " " + (t.account_head or "").upper()
			amt = flt(t.tax_amount, 2)
			if "CGST" in desc:
				taxes_map[t.parent]["cgst"] += amt
			elif "SGST" in desc or "UTGST" in desc:
				taxes_map[t.parent]["sgst"] += amt
			elif "IGST" in desc:
				taxes_map[t.parent]["igst"] += amt
			elif "CESS" in desc:
				taxes_map[t.parent]["cess"] += amt
			else:
				# Split generic GST 50/50 CGST & SGST
				taxes_map[t.parent]["cgst"] += amt / 2.0
				taxes_map[t.parent]["sgst"] += amt / 2.0
	except Exception:
		pass

	data = []
	for inv in invoices:
		tax_info = taxes_map[inv.invoice_no]
		taxable = flt(inv.taxable_value, 2)
		inv_total = flt(inv.invoice_total, 2)

		# If return, reflect sign
		if inv.is_return:
			taxable = -abs(taxable)
			inv_total = -abs(inv_total)

		cust_type = "B2B" if inv.tax_id else "B2C"
		if filters.get("customer_type") and cust_type != filters.customer_type:
			continue

		cgst = flt(tax_info["cgst"], 2)
		sgst = flt(tax_info["sgst"], 2)
		igst = flt(tax_info["igst"], 2)
		cess = flt(tax_info["cess"], 2)

		# Fallback if taxes weren't split in table: split total_tax
		if not (cgst or sgst or igst) and flt(inv.total_tax) > 0:
			half = flt(inv.total_tax, 2) / 2.0
			cgst = half
			sgst = half

		data.append({
			"posting_date": inv.posting_date,
			"invoice_no": inv.invoice_no,
			"pos_profile": inv.pos_profile,
			"customer_type": cust_type,
			"customer_name": inv.customer_name or "Walk-in Guest",
			"tax_id": inv.tax_id or "-",
			"place_of_supply": "Intra-state" if not igst else "Inter-state",
			"taxable_value": taxable,
			"cgst": cgst,
			"sgst": sgst,
			"igst": igst,
			"cess": cess,
			"round_off": flt(inv.round_off, 2),
			"invoice_total": inv_total,
			"return_against": inv.return_against or "",
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_taxable = sum(d["taxable_value"] for d in data)
	tot_cgst = sum(d["cgst"] for d in data)
	tot_sgst = sum(d["sgst"] for d in data)
	tot_igst = sum(d["igst"] for d in data)
	tot_tax = tot_cgst + tot_sgst + tot_igst
	tot_inv = sum(d["invoice_total"] for d in data)
	b2b_count = sum(1 for d in data if d["customer_type"] == "B2B")
	b2c_count = sum(1 for d in data if d["customer_type"] == "B2C")

	return [
		{"value": len(data), "label": _("Total Invoices"), "datatype": "Int"},
		{"value": tot_taxable, "label": _("Taxable Value"), "datatype": "Currency", "currency": currency},
		{"value": tot_cgst, "label": _("Total CGST"), "datatype": "Currency", "currency": currency},
		{"value": tot_sgst, "label": _("Total SGST"), "datatype": "Currency", "currency": currency},
		{"value": tot_tax, "label": _("Total Tax (GST)"), "datatype": "Currency", "currency": currency},
		{"value": tot_inv, "label": _("Invoice Total"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": f"B2B: {b2b_count} | B2C: {b2c_count}", "label": _("Breakup"), "datatype": "Data"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	# Group by Date
	by_date = defaultdict(lambda: {"taxable": 0.0, "tax": 0.0})
	for d in data[:30]:
		k = str(d["posting_date"])
		by_date[k]["taxable"] += flt(d["taxable_value"])
		by_date[k]["tax"] += flt(d["cgst"]) + flt(d["sgst"]) + flt(d["igst"])

	labels = list(by_date.keys())
	taxable_vals = [round(v["taxable"], 2) for v in by_date.values()]
	tax_vals = [round(v["tax"], 2) for v in by_date.values()]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Taxable Value"), "values": taxable_vals},
				{"name": _("Tax Collected"), "values": tax_vals},
			],
		},
		"type": "bar",
		"colors": ["#10b981", "#6366f1"],
	}
