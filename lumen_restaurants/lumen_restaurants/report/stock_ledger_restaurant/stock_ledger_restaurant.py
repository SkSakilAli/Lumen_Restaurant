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
		{"label": _("Time"), "fieldname": "posting_time", "fieldtype": "Time", "width": 80},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 130},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 130},
		{"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 140},
		{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 90},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 90},
		{"label": _("Balance Qty"), "fieldname": "qty_after_transaction", "fieldtype": "Float", "width": 105},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "options": "currency", "width": 115},
		{"label": _("Balance Value"), "fieldname": "stock_value", "fieldtype": "Currency", "options": "currency", "width": 120},
	]


def get_data(filters):
	conditions = ["sle.is_cancelled = 0"]
	params = {}

	if filters.get("company"):
		conditions.append("sle.company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("sle.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("sle.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("warehouse"):
		conditions.append("sle.warehouse = %(warehouse)s")
		params["warehouse"] = filters.warehouse

	if filters.get("item_code"):
		conditions.append("sle.item_code = %(item_code)s")
		params["item_code"] = filters.item_code

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			sle.posting_date,
			sle.posting_time,
			sle.item_code,
			i.item_name,
			sle.warehouse,
			sle.voucher_type,
			sle.voucher_no,
			sle.actual_qty,
			sle.qty_after_transaction,
			sle.valuation_rate,
			sle.stock_value
		FROM `tabStock Ledger Entry` sle
		JOIN `tabItem` i ON i.name = sle.item_code
		WHERE {where_clause}
		ORDER BY sle.posting_date DESC, sle.posting_time DESC, sle.creation DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		act = flt(r.actual_qty, 2)
		in_qty = act if act > 0 else 0.0
		out_qty = abs(act) if act < 0 else 0.0

		data.append({
			"posting_date": r.posting_date,
			"posting_time": r.posting_time,
			"item_code": r.item_code,
			"item_name": r.item_name,
			"warehouse": r.warehouse,
			"voucher_type": r.voucher_type,
			"voucher_no": r.voucher_no,
			"in_qty": in_qty,
			"out_qty": out_qty,
			"qty_after_transaction": flt(r.qty_after_transaction, 2),
			"valuation_rate": flt(r.valuation_rate, 2),
			"stock_value": flt(r.stock_value, 2),
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_txns = len(data)
	tot_in = sum(d["in_qty"] for d in data)
	tot_out = sum(d["out_qty"] for d in data)

	return [
		{"value": tot_txns, "label": _("Transactions"), "datatype": "Int"},
		{"value": tot_in, "label": _("Total Inward Qty"), "datatype": "Float", "indicator": "Green"},
		{"value": tot_out, "label": _("Total Outward Qty"), "datatype": "Float", "indicator": "Orange"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_date = defaultdict(lambda: {"in": 0.0, "out": 0.0})
	for d in data[:30]:
		k = str(d["posting_date"])
		by_date[k]["in"] += d["in_qty"]
		by_date[k]["out"] += d["out_qty"]

	labels = list(by_date.keys())
	in_vals = [round(v["in"], 1) for v in by_date.values()]
	out_vals = [round(v["out"], 1) for v in by_date.values()]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Inward"), "values": in_vals},
				{"name": _("Outward"), "values": out_vals},
			],
		},
		"type": "bar",
		"colors": ["#10b981", "#f59e0b"],
	}
