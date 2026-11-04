# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate


DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency") or "USD"

	columns = get_columns(filters, company_currency)
	invoices, payments_map, items_map = get_invoice_data(filters)
	data = prepare_data(invoices, payments_map, items_map, filters)
	report_summary = get_report_summary(data, company_currency)
	chart = get_chart_data(data, filters, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(filters, currency):
	compare_by = filters.get("compare_by") or "Date & Outlet"

	columns = []
	if compare_by in ("Date & Outlet", "Date"):
		columns.append({"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100})
		columns.append({"label": _("Day of Week"), "fieldname": "day_of_week", "fieldtype": "Data", "width": 105})

	if compare_by in ("Date & Outlet", "Outlet"):
		columns.append({
			"label": _("Outlet / POS Profile"),
			"fieldname": "pos_profile",
			"fieldtype": "Link",
			"options": "POS Profile",
			"width": 160,
		})

	columns.extend([
		{"label": _("Total Bills"), "fieldname": "bill_count", "fieldtype": "Int", "width": 85},
		{"label": _("Items Sold"), "fieldname": "total_qty", "fieldtype": "Float", "width": 90},
		{"label": _("Avg Bill Value"), "fieldname": "avg_bill_value", "fieldtype": "Currency", "options": "currency", "width": 115},
		{"label": _("Avg Items / Bill"), "fieldname": "avg_items_per_bill", "fieldtype": "Float", "width": 110},
		{"label": _("Gross Sales"), "fieldname": "gross_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Discounts"), "fieldname": "total_discount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Taxes"), "fieldname": "tax_amount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Bill Value"), "fieldname": "bill_value", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Cash Sales"), "fieldname": "cash_sales", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Card Sales"), "fieldname": "card_sales", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Digital Sales"), "fieldname": "digital_sales", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Other Payments"), "fieldname": "other_sales", "fieldtype": "Currency", "options": "currency", "width": 110},
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

	where_clause = " AND ".join(conditions)

	invoices = frappe.db.sql(
		f"""
		SELECT
			'POS Invoice' as doctype,
			name,
			posting_date,
			pos_profile,
			company,
			total_qty,
			base_total,
			base_net_total,
			base_discount_amount,
			base_total_taxes_and_charges,
			base_rounding_adjustment,
			base_grand_total,
			base_rounded_total,
			is_return
		FROM `tabPOS Invoice`
		WHERE {where_clause}
		ORDER BY posting_date ASC
		""",
		params,
		as_dict=True,
	)

	si_conditions = list(conditions)
	si_conditions.append("(is_pos = 1 OR pos_profile IS NOT NULL)")
	si_where = " AND ".join(si_conditions)

	sales_invoices = frappe.db.sql(
		f"""
		SELECT
			'Sales Invoice' as doctype,
			name,
			posting_date,
			pos_profile,
			company,
			total_qty,
			base_total,
			base_net_total,
			base_discount_amount,
			base_total_taxes_and_charges,
			base_rounding_adjustment,
			base_grand_total,
			base_rounded_total,
			is_return
		FROM `tabSales Invoice`
		WHERE {si_where}
		ORDER BY posting_date ASC
		""",
		params,
		as_dict=True,
	)

	all_invoices = invoices + sales_invoices
	if not all_invoices:
		return [], {}, {}

	invoice_names = [inv.name for inv in all_invoices]

	# Fetch line discount breakdown per invoice
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

	# Fetch payments
	payments_map = defaultdict(lambda: {"cash": 0.0, "card": 0.0, "digital": 0.0, "other": 0.0})
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
	compare_by = filters.get("compare_by") or "Date & Outlet"
	grouped = {}

	for inv in invoices:
		p_date = getdate(inv.posting_date)
		day_name = DAYS_OF_WEEK[p_date.weekday()]

		if compare_by == "Date & Outlet":
			key = (str(inv.posting_date), inv.pos_profile or _("Not Assigned"))
		elif compare_by == "Date":
			key = (str(inv.posting_date),)
		elif compare_by == "Outlet":
			key = (inv.pos_profile or _("Not Assigned"),)
		else:
			key = (str(inv.posting_date), inv.pos_profile or _("Not Assigned"))

		if key not in grouped:
			entry = {
				"bill_count": 0,
				"total_qty": 0.0,
				"gross_sales": 0.0,
				"total_discount": 0.0,
				"net_sales": 0.0,
				"tax_amount": 0.0,
				"bill_value": 0.0,
				"cash_sales": 0.0,
				"card_sales": 0.0,
				"digital_sales": 0.0,
				"other_sales": 0.0,
			}
			if compare_by in ("Date & Outlet", "Date"):
				entry["posting_date"] = inv.posting_date
				entry["day_of_week"] = day_name
			if compare_by in ("Date & Outlet", "Outlet"):
				entry["pos_profile"] = inv.pos_profile or _("Not Assigned")
			grouped[key] = entry

		g = grouped[key]
		g["bill_count"] += 1
		g["total_qty"] += flt(inv.total_qty)

		item_info = items_map.get(inv.name, {"item_discount": 0.0, "gross_amount": 0.0})
		item_disc = flt(item_info["item_discount"])
		bill_disc = flt(inv.base_discount_amount)
		total_disc = item_disc + bill_disc

		net_total = flt(inv.base_net_total)
		gross = net_total + total_disc if (net_total + total_disc) > 0 else flt(inv.base_total)
		if item_info["gross_amount"] > gross:
			gross = item_info["gross_amount"]

		tax = flt(inv.base_total_taxes_and_charges)
		bill_val = flt(inv.base_rounded_total) or flt(inv.base_grand_total)

		g["gross_sales"] += gross
		g["total_discount"] += total_disc
		g["net_sales"] += net_total
		g["tax_amount"] += tax
		g["bill_value"] += bill_val

		pmt = payments_map.get(inv.name, {"cash": 0.0, "card": 0.0, "digital": 0.0, "other": 0.0})
		g["cash_sales"] += pmt["cash"]
		g["card_sales"] += pmt["card"]
		g["digital_sales"] += pmt["digital"]
		g["other_sales"] += pmt["other"]

	data = list(grouped.values())
	for row in data:
		cnt = row["bill_count"] or 1
		row["avg_bill_value"] = flt(row["bill_value"] / cnt, 2)
		row["avg_items_per_bill"] = flt(row["total_qty"] / cnt, 2)

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_bills = sum(d["bill_count"] for d in data)
	tot_qty = sum(d["total_qty"] for d in data)
	tot_net = sum(d["net_sales"] for d in data)
	tot_bill = sum(d["bill_value"] for d in data)
	avg_bill = flt(tot_bill / tot_bills, 2) if tot_bills else 0.0

	return [
		{"value": tot_bill, "label": _("Total Bill Value"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": tot_net, "label": _("Total Net Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_bills, "label": _("Total Bills"), "datatype": "Int"},
		{"value": avg_bill, "label": _("Avg Ticket Size (ABV)"), "datatype": "Currency", "currency": currency, "indicator": "Blue"},
		{"value": tot_qty, "label": _("Items Sold"), "datatype": "Float"},
	]


def get_chart_data(data, filters, currency):
	if not data:
		return None

	compare_by = filters.get("compare_by") or "Date & Outlet"
	labels = []
	net_sales_data = []
	bills_data = []

	for row in data[:20]:
		if compare_by == "Outlet":
			labels.append(str(row.get("pos_profile", "")))
		elif compare_by == "Date":
			labels.append(str(row.get("posting_date", "")))
		else:
			d_str = str(row.get("posting_date", ""))
			p_str = str(row.get("pos_profile", ""))
			labels.append(f"{d_str} ({p_str})")

		net_sales_data.append(flt(row.get("net_sales"), 2))
		bills_data.append(row.get("bill_count", 0))

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Net Sales"), "values": net_sales_data},
			],
		},
		"type": "line" if compare_by == "Date" else "bar",
		"colors": ["#3b82f6"],
	}
