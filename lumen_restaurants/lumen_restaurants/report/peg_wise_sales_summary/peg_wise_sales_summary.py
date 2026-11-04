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
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Beverage Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{"label": _("Portion / Serving"), "fieldname": "portion_label", "fieldtype": "Data", "width": 110},
		{"label": _("Qty Sold"), "fieldname": "qty_sold", "fieldtype": "Float", "width": 90},
		{"label": _("Total ml Sold"), "fieldname": "total_ml", "fieldtype": "Float", "width": 110},
		{"label": _("Gross Sales"), "fieldname": "gross_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
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

	if filters.get("item_code"):
		conditions.append("it.item_code = %(item_code)s")
		params["item_code"] = filters.item_code

	where_clause = " AND ".join(conditions)

	# Fetch beverage item sales joined with bar recipe serving size if available
	query = f"""
		SELECT
			inv.posting_date,
			inv.pos_profile,
			it.item_code,
			it.item_name,
			COALESCE(br.serving_size_ml, 30.0) as serving_ml,
			COALESCE(br.category, 'Spirit / Beverage') as portion_label,
			SUM(it.qty) as qty_sold,
			SUM(it.base_amount) as gross_sales,
			SUM(it.base_net_amount) as net_sales
		FROM `tabPOS Invoice Item` it
		JOIN `tabPOS Invoice` inv ON inv.name = it.parent
		LEFT JOIN `tabPOS Bar Recipe` br ON br.item_code = it.item_code
		WHERE {where_clause}
		GROUP BY inv.posting_date, inv.pos_profile, it.item_code, it.item_name, br.serving_size_ml, br.category
		ORDER BY inv.posting_date DESC, net_sales DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		qty = flt(r.qty_sold, 1)
		ml = flt(r.serving_ml, 1)
		tot_ml = qty * ml
		lbl = f"{int(ml)} ml Peg" if ml in (30, 60, 90) else (r.portion_label or "Portion")

		data.append({
			"posting_date": r.posting_date,
			"pos_profile": r.pos_profile,
			"item_code": r.item_code,
			"item_name": r.item_name,
			"portion_label": lbl,
			"qty_sold": qty,
			"total_ml": tot_ml,
			"gross_sales": flt(r.gross_sales, 2),
			"net_sales": flt(r.net_sales, 2),
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_qty = sum(d["qty_sold"] for d in data)
	tot_ml = sum(d["total_ml"] for d in data)
	tot_liters = flt(tot_ml / 1000.0, 2)
	tot_sales = sum(d["net_sales"] for d in data)

	return [
		{"value": tot_qty, "label": _("Total Portions Sold"), "datatype": "Int"},
		{"value": tot_liters, "label": _("Total Liters Poured"), "datatype": "Float", "indicator": "Blue"},
		{"value": tot_sales, "label": _("Bar Beverage Revenue"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_item = defaultdict(float)
	for d in data:
		by_item[d["item_name"][:18]] += flt(d["net_sales"])

	labels = list(by_item.keys())[:8]
	vals = [round(by_item[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Revenue"), "values": vals}],
		},
		"type": "bar",
		"colors": ["#10b981"],
	}
