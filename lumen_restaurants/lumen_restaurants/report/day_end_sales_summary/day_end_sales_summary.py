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
	invoices, payments_map, items_map = get_invoice_data(filters)
	data = prepare_data(invoices, payments_map, items_map, filters)
	report_summary = get_report_summary(data, company_currency)
	chart = get_chart_data(data, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(filters, currency):
	group_by = filters.get("group_by") or "Outlet & Date"

	columns = []
	if group_by in ("Outlet & Date", "Date"):
		columns.append({
			"label": _("Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100,
		})
	if group_by in ("Outlet & Date", "Outlet"):
		columns.append({
			"label": _("Outlet / POS Profile"),
			"fieldname": "pos_profile",
			"fieldtype": "Link",
			"options": "POS Profile",
			"width": 160,
		})
	if group_by == "Cashier":
		columns.append({
			"label": _("Cashier / User"),
			"fieldname": "owner",
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		})

	columns.extend([
		{"label": _("Total Bills"), "fieldname": "bill_count", "fieldtype": "Int", "width": 85},
		{"label": _("Qty Sold"), "fieldname": "total_qty", "fieldtype": "Float", "width": 85},
		{"label": _("Gross Sales"), "fieldname": "gross_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Item Discounts"), "fieldname": "item_discount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Bill Discounts"), "fieldname": "bill_discount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Total Discounts"), "fieldname": "total_discount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Taxes"), "fieldname": "tax_amount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Rounding"), "fieldname": "rounding_adjustment", "fieldtype": "Currency", "options": "currency", "width": 90},
		{"label": _("Bill Value"), "fieldname": "bill_value", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Cash Paid"), "fieldname": "cash_paid", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Card Paid"), "fieldname": "card_paid", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Digital Paid"), "fieldname": "digital_paid", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Other / Credit Paid"), "fieldname": "other_paid", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Total Paid"), "fieldname": "total_paid", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Returns (Bills)"), "fieldname": "returns_count", "fieldtype": "Int", "width": 95},
		{"label": _("Returns Value"), "fieldname": "returns_amount", "fieldtype": "Currency", "options": "currency", "width": 110},
	])

	return columns


def get_invoice_data(filters):
	conditions = ["docstatus = 1"]
	params = {}

	if filters.get("company"):
		conditions.append("company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("pos_profile"):
		conditions.append("pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	if filters.get("owner"):
		conditions.append("owner = %(owner)s")
		params["owner"] = filters.owner

	where_clause = " AND ".join(conditions)

	# 1. Fetch POS Invoices
	invoices = frappe.db.sql(
		f"""
		SELECT
			'POS Invoice' as doctype,
			name,
			posting_date,
			posting_time,
			pos_profile,
			owner,
			company,
			customer,
			total_qty,
			base_total,
			base_net_total,
			base_discount_amount,
			base_total_taxes_and_charges,
			base_rounding_adjustment,
			base_grand_total,
			base_rounded_total,
			base_paid_amount,
			base_change_amount,
			outstanding_amount,
			is_return,
			return_against
		FROM `tabPOS Invoice`
		WHERE {where_clause}
		ORDER BY posting_date DESC, posting_time DESC
		""",
		params,
		as_dict=True,
	)

	# 2. Also check Sales Invoices posted through POS
	si_conditions = list(conditions)
	si_conditions.append("(is_pos = 1 OR pos_profile IS NOT NULL)")
	si_where = " AND ".join(si_conditions)

	sales_invoices = frappe.db.sql(
		f"""
		SELECT
			'Sales Invoice' as doctype,
			name,
			posting_date,
			posting_time,
			pos_profile,
			owner,
			company,
			customer,
			total_qty,
			base_total,
			base_net_total,
			base_discount_amount,
			base_total_taxes_and_charges,
			base_rounding_adjustment,
			base_grand_total,
			base_rounded_total,
			base_paid_amount,
			base_change_amount,
			outstanding_amount,
			is_return,
			return_against
		FROM `tabSales Invoice`
		WHERE {si_where}
		ORDER BY posting_date DESC, posting_time DESC
		""",
		params,
		as_dict=True,
	)

	all_invoices = invoices + sales_invoices
	if not all_invoices:
		return [], {}, {}

	invoice_names = [inv.name for inv in all_invoices]

	# 3. Fetch item discount breakdown per invoice
	items_map = defaultdict(lambda: {"item_discount": 0.0, "gross_amount": 0.0})
	
	if invoices:
		pos_names = [inv.name for inv in invoices]
		pos_item_data = frappe.db.sql(
			"""
			SELECT
				parent,
				sum(qty * coalesce(price_list_rate, rate)) as gross_amount,
				sum(
					case
						when discount_amount > 0 then discount_amount * qty
						when discount_percentage > 0 then (coalesce(price_list_rate, rate) * discount_percentage / 100.0) * qty
						else 0
					end
				) as item_discount
			FROM `tabPOS Invoice Item`
			WHERE parent IN %(names)s
			GROUP BY parent
			""",
			{"names": pos_names},
			as_dict=True,
		)
		for row in pos_item_data:
			items_map[row.parent]["item_discount"] = flt(row.item_discount)
			items_map[row.parent]["gross_amount"] = flt(row.gross_amount)

	if sales_invoices:
		si_names = [inv.name for inv in sales_invoices]
		si_item_data = frappe.db.sql(
			"""
			SELECT
				parent,
				sum(qty * coalesce(price_list_rate, rate)) as gross_amount,
				sum(
					case
						when discount_amount > 0 then discount_amount * qty
						when discount_percentage > 0 then (coalesce(price_list_rate, rate) * discount_percentage / 100.0) * qty
						else 0
					end
				) as item_discount
			FROM `tabSales Invoice Item`
			WHERE parent IN %(names)s
			GROUP BY parent
			""",
			{"names": si_names},
			as_dict=True,
		)
		for row in si_item_data:
			items_map[row.parent]["item_discount"] = flt(row.item_discount)
			items_map[row.parent]["gross_amount"] = flt(row.gross_amount)

	# 4. Fetch Payments per invoice
	payments_map = defaultdict(lambda: {"cash": 0.0, "card": 0.0, "digital": 0.0, "other": 0.0, "total": 0.0})
	payment_rows = frappe.db.sql(
		"""
		SELECT
			parent,
			mode_of_payment,
			sum(base_amount) as amount
		FROM `tabSales Invoice Payment`
		WHERE parent IN %(names)s
		GROUP BY parent, mode_of_payment
		""",
		{"names": invoice_names},
		as_dict=True,
	)

	for row in payment_rows:
		amt = flt(row.amount)
		mop = (row.mode_of_payment or "").lower()
		payments_map[row.parent]["total"] += amt
		if "cash" in mop:
			payments_map[row.parent]["cash"] += amt
		elif any(k in mop for k in ("card", "visa", "master", "amex", "pos", "credit card", "debit card", "mada")):
			payments_map[row.parent]["card"] += amt
		elif any(k in mop for k in ("upi", "paytm", "gpay", "phonepe", "apple", "google", "online", "wallet", "digital", "transfer")):
			payments_map[row.parent]["digital"] += amt
		else:
			payments_map[row.parent]["other"] += amt

	return all_invoices, payments_map, items_map


def prepare_data(invoices, payments_map, items_map, filters):
	group_by = filters.get("group_by") or "Outlet & Date"
	grouped = {}

	for inv in invoices:
		if group_by == "Outlet & Date":
			key = (inv.posting_date, inv.pos_profile or _("Not Assigned"))
		elif group_by == "Outlet":
			key = (inv.pos_profile or _("Not Assigned"),)
		elif group_by == "Date":
			key = (inv.posting_date,)
		elif group_by == "Cashier":
			key = (inv.owner or _("System"),)
		else:
			key = (inv.posting_date, inv.pos_profile or _("Not Assigned"))

		if key not in grouped:
			entry = {
				"bill_count": 0,
				"total_qty": 0.0,
				"gross_sales": 0.0,
				"item_discount": 0.0,
				"bill_discount": 0.0,
				"total_discount": 0.0,
				"net_sales": 0.0,
				"tax_amount": 0.0,
				"rounding_adjustment": 0.0,
				"bill_value": 0.0,
				"cash_paid": 0.0,
				"card_paid": 0.0,
				"digital_paid": 0.0,
				"other_paid": 0.0,
				"total_paid": 0.0,
				"outstanding_amount": 0.0,
				"returns_count": 0,
				"returns_amount": 0.0,
			}
			if group_by in ("Outlet & Date", "Date"):
				entry["posting_date"] = inv.posting_date
			if group_by in ("Outlet & Date", "Outlet"):
				entry["pos_profile"] = inv.pos_profile or _("Not Assigned")
			if group_by == "Cashier":
				entry["owner"] = inv.owner or _("System")
			grouped[key] = entry

		g = grouped[key]
		g["bill_count"] += 1
		g["total_qty"] += flt(inv.total_qty)

		# Line-level discounts
		item_info = items_map.get(inv.name, {"item_discount": 0.0, "gross_amount": 0.0})
		item_disc = flt(item_info["item_discount"])
		bill_disc = flt(inv.base_discount_amount)
		total_disc = item_disc + bill_disc

		# Net total from invoice
		net_total = flt(inv.base_net_total)
		# Gross sales = Net Sales + Total Discounts
		gross = net_total + total_disc if (net_total + total_disc) > 0 else flt(inv.base_total)
		if item_info["gross_amount"] > gross:
			gross = item_info["gross_amount"]

		tax = flt(inv.base_total_taxes_and_charges)
		rounding = flt(inv.base_rounding_adjustment)
		bill_val = flt(inv.base_rounded_total) or flt(inv.base_grand_total)

		g["gross_sales"] += gross
		g["item_discount"] += item_disc
		g["bill_discount"] += bill_disc
		g["total_discount"] += total_disc
		g["net_sales"] += net_total
		g["tax_amount"] += tax
		g["rounding_adjustment"] += rounding
		g["bill_value"] += bill_val
		g["outstanding_amount"] += flt(inv.outstanding_amount)

		# Payments
		pmt = payments_map.get(inv.name, {"cash": 0.0, "card": 0.0, "digital": 0.0, "other": 0.0, "total": 0.0})
		g["cash_paid"] += pmt["cash"]
		g["card_paid"] += pmt["card"]
		g["digital_paid"] += pmt["digital"]
		g["other_paid"] += pmt["other"]
		g["total_paid"] += (pmt["total"] or (flt(inv.base_paid_amount) - flt(inv.base_change_amount)))

		if inv.is_return:
			g["returns_count"] += 1
			g["returns_amount"] += abs(bill_val)

	data = list(grouped.values())
	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_bills = sum(d["bill_count"] for d in data)
	tot_gross = sum(d["gross_sales"] for d in data)
	tot_disc = sum(d["total_discount"] for d in data)
	tot_net = sum(d["net_sales"] for d in data)
	tot_tax = sum(d["tax_amount"] for d in data)
	tot_bill = sum(d["bill_value"] for d in data)
	tot_paid = sum(d["total_paid"] for d in data)
	tot_out = sum(d["outstanding_amount"] for d in data)

	return [
		{"value": tot_bills, "label": _("Total Bills"), "datatype": "Int"},
		{"value": tot_gross, "label": _("Gross Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_disc, "label": _("Discounts"), "datatype": "Currency", "currency": currency},
		{"value": tot_net, "label": _("Net Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_tax, "label": _("Taxes"), "datatype": "Currency", "currency": currency},
		{"value": tot_bill, "label": _("Bill Value"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": tot_paid, "label": _("Total Paid"), "datatype": "Currency", "currency": currency},
		{"value": tot_out, "label": _("Outstanding"), "datatype": "Currency", "currency": currency, "indicator": "Red" if tot_out > 0 else "Grey"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	# If there are multiple rows (e.g. across dates or outlets), show bar comparison
	labels = []
	net_sales_data = []
	tax_data = []
	discount_data = []

	for row in data[:15]:
		label_parts = []
		if row.get("posting_date"):
			label_parts.append(str(row["posting_date"]))
		if row.get("pos_profile"):
			label_parts.append(str(row["pos_profile"]))
		if row.get("owner"):
			label_parts.append(str(row["owner"]))
		labels.append(" - ".join(label_parts) or "Summary")
		net_sales_data.append(flt(row.get("net_sales"), 2))
		tax_data.append(flt(row.get("tax_amount"), 2))
		discount_data.append(flt(row.get("total_discount"), 2))

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Net Sales"), "values": net_sales_data},
				{"name": _("Taxes"), "values": tax_data},
				{"name": _("Discounts"), "values": discount_data},
			],
		},
		"type": "bar",
		"colors": ["#10b981", "#6366f1", "#f59e0b"],
	}
