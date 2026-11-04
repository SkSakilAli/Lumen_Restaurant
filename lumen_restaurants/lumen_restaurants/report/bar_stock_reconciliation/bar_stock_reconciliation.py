# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company_currency = frappe.defaults.get_global_default("currency") or "USD"

	columns = get_columns(filters, company_currency)
	data = get_data(filters)
	report_summary = get_report_summary(data, company_currency)
	chart = get_chart_data(data, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(filters, currency):
	return [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{"label": _("Recon Doc"), "fieldname": "voucher_no", "fieldtype": "Link", "options": "Stock Reconciliation", "width": 140},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 130},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Spirit Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Book Qty"), "fieldname": "current_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Physical Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 105},
		{"label": _("Variance (Bottles)"), "fieldname": "variance_qty", "fieldtype": "Float", "width": 130},
		{"label": _("Variance Value"), "fieldname": "variance_amount", "fieldtype": "Currency", "options": "currency", "width": 125},
	]


def get_data(filters):
	conditions = ["sr.docstatus = 1"]
	params = {}

	if filters.get("from_date"):
		conditions.append("sr.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("sr.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("warehouse"):
		conditions.append("sri.warehouse = %(warehouse)s")
		params["warehouse"] = filters.warehouse

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			sr.posting_date,
			sr.name as voucher_no,
			sri.warehouse,
			sri.item_code,
			sri.item_name,
			sri.current_qty,
			sri.qty,
			sri.current_valuation_rate,
			(sri.qty - sri.current_qty) as variance_qty,
			sri.amount_difference as variance_amount
		FROM `tabStock Reconciliation Item` sri
		JOIN `tabStock Reconciliation` sr ON sr.name = sri.parent
		WHERE {where_clause}
		ORDER BY sr.posting_date DESC, variance_qty ASC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		var_qty = flt(r.variance_qty, 2)
		var_val = flt(r.variance_amount, 2) if r.variance_amount else flt(var_qty * flt(r.current_valuation_rate), 2)

		data.append({
			"posting_date": r.posting_date,
			"voucher_no": r.voucher_no,
			"warehouse": r.warehouse,
			"item_code": r.item_code,
			"item_name": r.item_name,
			"current_qty": flt(r.current_qty, 2),
			"qty": flt(r.qty, 2),
			"variance_qty": var_qty,
			"variance_amount": var_val,
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_recons = len(data)
	tot_shortage_val = sum(abs(d["variance_amount"]) for d in data if d["variance_qty"] < 0)
	tot_surplus_val = sum(d["variance_amount"] for d in data if d["variance_qty"] > 0)

	return [
		{"value": tot_recons, "label": _("Reconciled Lines"), "datatype": "Int"},
		{"value": tot_shortage_val, "label": _("Bar Shortage Loss"), "datatype": "Currency", "currency": currency, "indicator": "Red"},
		{"value": tot_surplus_val, "label": _("Bar Surplus Gain"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	discrepant = [d for d in data if d["variance_qty"] != 0][:8]
	labels = [d["item_name"][:14] for d in discrepant]
	vals = [d["variance_qty"] for d in discrepant]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Variance (Bottles)"), "values": vals}],
		},
		"type": "bar",
		"colors": ["#ef4444"],
	}
