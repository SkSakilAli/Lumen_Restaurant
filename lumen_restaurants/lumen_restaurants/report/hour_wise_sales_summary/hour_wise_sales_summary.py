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
		{"label": _("Hour Slot"), "fieldname": "hour_slot", "fieldtype": "Data", "width": 140},
		{"label": _("Bills"), "fieldname": "bill_count", "fieldtype": "Int", "width": 80},
		{"label": _("Covers"), "fieldname": "covers", "fieldtype": "Int", "width": 80},
		{"label": _("Gross Sales"), "fieldname": "gross_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Discount"), "fieldname": "discount_amount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Tax"), "fieldname": "tax_amount", "fieldtype": "Currency", "options": "currency", "width": 100},
		{"label": _("Bill Value"), "fieldname": "bill_value", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Average Bill Value"), "fieldname": "avg_bill_value", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Sales per Cover"), "fieldname": "sales_per_cover", "fieldtype": "Currency", "options": "currency", "width": 130},
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

	# Fetch hourly aggregates from POS Invoices
	query = f"""
		SELECT
			HOUR(inv.posting_time) as hour_num,
			COUNT(DISTINCT inv.name) as bill_count,
			COALESCE(SUM(inv.base_total), 0) as gross_sales,
			COALESCE(SUM(inv.base_discount_amount), 0) as discount_amount,
			COALESCE(SUM(inv.base_net_total), 0) as net_sales,
			COALESCE(SUM(inv.base_total_taxes_and_charges), 0) as tax_amount,
			COALESCE(SUM(inv.base_rounded_total), SUM(inv.base_grand_total), 0) as bill_value
		FROM `tabPOS Invoice` inv
		WHERE {where_clause}
		GROUP BY HOUR(inv.posting_time)
		ORDER BY HOUR(inv.posting_time) ASC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	# Fetch covers from POS Restaurant Order if present
	covers_by_hour = defaultdict(int)
	try:
		covers_query = f"""
			SELECT
				HOUR(ro.opened_at) as hour_num,
				COALESCE(SUM(ro.guests), 0) as total_guests
			FROM `tabPOS Restaurant Order` ro
			WHERE ro.docstatus < 2
				AND DATE(ro.opened_at) >= %(from_date)s
				AND DATE(ro.opened_at) <= %(to_date)s
			GROUP BY HOUR(ro.opened_at)
		"""
		covers_rows = frappe.db.sql(covers_query, params, as_dict=True)
		for cr in covers_rows:
			if cr.hour_num is not None:
				covers_by_hour[int(cr.hour_num)] = int(cr.total_guests or 0)
	except Exception:
		pass

	# Map rows into 24-hour slots
	hour_map = {r.hour_num: r for r in rows if r.hour_num is not None}

	data = []
	for h in range(24):
		slot_label = f"{h:02d}:00 - {(h + 1) % 24:02d}:00"
		item = hour_map.get(h)
		if item:
			bill_count = int(item.bill_count or 0)
			covers = covers_by_hour.get(h, bill_count) or bill_count
			gross = flt(item.gross_sales, 2)
			disc = flt(item.discount_amount, 2)
			net = flt(item.net_sales, 2)
			tax = flt(item.tax_amount, 2)
			val = flt(item.bill_value, 2)
			avg_bill = flt(net / bill_count, 2) if bill_count else 0
			per_cover = flt(net / covers, 2) if covers else avg_bill

			data.append({
				"hour_slot": slot_label,
				"hour_num": h,
				"bill_count": bill_count,
				"covers": covers,
				"gross_sales": gross,
				"discount_amount": disc,
				"net_sales": net,
				"tax_amount": tax,
				"bill_value": val,
				"avg_bill_value": avg_bill,
				"sales_per_cover": per_cover,
			})
		else:
			# Only show active slots if filter is applied, or show all with 0 if summary
			# To keep report clean, show rows where there is at least activity, or full 24h
			pass

	# If all 0 or empty, ensure empty list
	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_bills = sum(d["bill_count"] for d in data)
	tot_covers = sum(d["covers"] for d in data)
	tot_gross = sum(d["gross_sales"] for d in data)
	tot_net = sum(d["net_sales"] for d in data)
	tot_bill = sum(d["bill_value"] for d in data)
	avg_bill = flt(tot_net / tot_bills, 2) if tot_bills else 0

	# Peak hour
	peak = max(data, key=lambda x: x["net_sales"]) if data else None
	peak_str = peak["hour_slot"] if peak else "-"

	return [
		{"value": tot_bills, "label": _("Total Bills"), "datatype": "Int"},
		{"value": tot_covers, "label": _("Total Covers"), "datatype": "Int"},
		{"value": tot_gross, "label": _("Gross Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_net, "label": _("Net Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_bill, "label": _("Bill Value"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": avg_bill, "label": _("Avg Bill Value"), "datatype": "Currency", "currency": currency},
		{"value": peak_str, "label": _("Peak Hour"), "datatype": "Data", "indicator": "Blue"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [d["hour_slot"] for d in data]
	net_sales = [flt(d["net_sales"], 2) for d in data]
	bills = [d["bill_count"] for d in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Net Sales"), "values": net_sales, "chartType": "line"},
				{"name": _("Bills"), "values": bills, "chartType": "bar"},
			],
		},
		"type": "axis-mixed",
		"colors": ["#10b981", "#6366f1"],
	}
