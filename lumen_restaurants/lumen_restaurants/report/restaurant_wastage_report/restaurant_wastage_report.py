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
		{"label": _("Source"), "fieldname": "voucher_no", "fieldtype": "Data", "width": 140},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 130},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{"label": _("Waste Type"), "fieldname": "waste_type", "fieldtype": "Data", "width": 120},
		{"label": _("Wasted Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 95},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 75},
		{"label": _("Cost Loss"), "fieldname": "cost_loss", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Reason"), "fieldname": "reason", "fieldtype": "Data", "width": 160},
	]


def get_data(filters):
	conditions = ["se.docstatus = 1", "(se.purpose = 'Material Issue' OR se.purpose = 'Scrap')"]
	params = {}

	if filters.get("company"):
		conditions.append("se.company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("se.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("se.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	where_clause = " AND ".join(conditions)

	data = []

	# 1. Fetch Material Issue / Scrap Stock Entries
	query = f"""
		SELECT
			se.posting_date,
			se.name as voucher_no,
			sed.s_warehouse as warehouse,
			sed.item_code,
			sed.item_name,
			'Kitchen Spoilage / Scrap' as waste_type,
			sed.qty,
			sed.uom,
			sed.amount as cost_loss,
			COALESCE(sed.description, se.remarks, 'Spoilage') as reason
		FROM `tabStock Entry Detail` sed
		JOIN `tabStock Entry` se ON se.name = sed.parent
		WHERE {where_clause}
		ORDER BY se.posting_date DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)
	for r in rows:
		data.append({
			"posting_date": r.posting_date,
			"voucher_no": r.voucher_no,
			"warehouse": r.warehouse,
			"item_code": r.item_code,
			"item_name": r.item_name,
			"waste_type": r.waste_type,
			"qty": flt(r.qty, 2),
			"uom": r.uom,
			"cost_loss": flt(r.cost_loss, 2),
			"reason": r.reason,
		})

	# 2. Fetch Bar Spillage
	try:
		sp_cond = ["1=1"]
		if filters.get("from_date"):
			sp_cond.append("DATE(sp.creation) >= %(from_date)s")
		if filters.get("to_date"):
			sp_cond.append("DATE(sp.creation) <= %(to_date)s")

		sp_query = f"""
			SELECT
				DATE(sp.creation) as posting_date,
				sp.name as voucher_no,
				sp.warehouse,
				spi.item_code,
				spi.item_name,
				'Bar Spillage / Breakage' as waste_type,
				spi.qty,
				spi.uom,
				spi.cost as cost_loss,
				sp.reason
			FROM `tabPOS Bar Spillage Item` spi
			JOIN `tabPOS Bar Spillage` sp ON sp.name = spi.parent
			WHERE {" AND ".join(sp_cond)}
			ORDER BY sp.creation DESC
		"""
		for s in frappe.db.sql(sp_query, params, as_dict=True):
			data.append({
				"posting_date": s.posting_date,
				"voucher_no": s.voucher_no,
				"warehouse": s.warehouse,
				"item_code": s.item_code,
				"item_name": s.item_name,
				"waste_type": s.waste_type,
				"qty": flt(s.qty, 2),
				"uom": s.uom or "Nos",
				"cost_loss": flt(s.cost_loss, 2),
				"reason": s.reason or "Bar Spill",
			})
	except Exception:
		pass

	data.sort(key=lambda x: str(x["posting_date"]), reverse=True)
	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_incidents = len(data)
	tot_loss = sum(d["cost_loss"] for d in data)

	return [
		{"value": tot_incidents, "label": _("Waste Incidents"), "datatype": "Int"},
		{"value": tot_loss, "label": _("Total Wastage Loss"), "datatype": "Currency", "currency": currency, "indicator": "Red"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_item = defaultdict(float)
	for d in data:
		by_item[d["item_name"][:16]] += flt(d["cost_loss"])

	labels = list(by_item.keys())[:8]
	vals = [round(by_item[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Wastage Loss"), "values": vals}],
		},
		"type": "bar",
		"colors": ["#ef4444"],
	}
