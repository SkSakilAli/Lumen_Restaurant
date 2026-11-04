# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company_currency = "USD"
	if filters.get("pos_profile"):
		comp = frappe.get_cached_value("POS Profile", filters.pos_profile, "company")
		if comp:
			company_currency = frappe.get_cached_value("Company", comp, "default_currency") or "USD"

	columns = get_columns(filters, company_currency)
	data = get_data(filters)
	report_summary = get_report_summary(data, company_currency)
	chart = get_chart_data(data, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(filters, currency):
	return [
		{"label": _("Date / Time"), "fieldname": "timestamp", "fieldtype": "Datetime", "width": 140},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
		{"label": _("Order No"), "fieldname": "order_no", "fieldtype": "Link", "options": "POS Restaurant Order", "width": 130},
		{"label": _("Table"), "fieldname": "table_label", "fieldtype": "Data", "width": 80},
		{"label": _("Type"), "fieldname": "cancellation_type", "fieldtype": "Data", "width": 120},
		{"label": _("Void Value"), "fieldname": "void_value", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Reason"), "fieldname": "reason", "fieldtype": "Data", "width": 180},
		{"label": _("Cancelled By"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 130},
	]


def get_data(filters):
	conditions = ["1=1"]
	params = {}

	if filters.get("from_date"):
		conditions.append("DATE(ro.opened_at) >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("DATE(ro.opened_at) <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("pos_profile"):
		conditions.append("ro.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	if filters.get("user"):
		conditions.append("ro.opened_by = %(user)s")
		params["user"] = filters.user

	where_clause = " AND ".join(conditions)

	data = []

	# 1. Fetch Cancelled Restaurant Orders
	try:
		ro_query = f"""
			SELECT
				ro.opened_at as timestamp,
				ro.pos_profile,
				ro.name as order_no,
				ro.table_label,
				'Order Cancellation' as cancellation_type,
				COALESCE(ro.total, 0) as void_value,
				COALESCE(ro.cancel_reason, 'No reason specified') as reason,
				ro.opened_by as user
			FROM `tabPOS Restaurant Order` ro
			WHERE ro.status = 'Cancelled' AND {where_clause}
			ORDER BY ro.opened_at DESC
		"""
		orders = frappe.db.sql(ro_query, params, as_dict=True)
		for o in orders:
			data.append({
				"timestamp": o.timestamp,
				"pos_profile": o.pos_profile,
				"order_no": o.order_no,
				"table_label": o.table_label or "-",
				"cancellation_type": o.cancellation_type,
				"void_value": flt(o.void_value, 2),
				"reason": o.reason,
				"user": o.user,
			})
	except Exception:
		pass

	# 2. Fetch Audit Log Voids
	try:
		audit_conditions = ["al.action LIKE '%Void%' OR al.action LIKE '%Cancel%'"]
		if filters.get("from_date"):
			audit_conditions.append("DATE(al.creation) >= %(from_date)s")
		if filters.get("to_date"):
			audit_conditions.append("DATE(al.creation) <= %(to_date)s")
		if filters.get("pos_profile"):
			audit_conditions.append("al.pos_profile = %(pos_profile)s")
		if filters.get("user"):
			audit_conditions.append("al.user = %(user)s")

		a_where = " AND ".join(audit_conditions)
		a_query = f"""
			SELECT
				al.creation as timestamp,
				al.pos_profile,
				al.reference_name as order_no,
				'-' as table_label,
				al.action as cancellation_type,
				COALESCE(al.amount, 0) as void_value,
				al.detail as reason,
				al.user
			FROM `tabLumenPOS Audit Log` al
			WHERE {a_where}
			ORDER BY al.creation DESC
		"""
		logs = frappe.db.sql(a_query, params, as_dict=True)
		for l in logs:
			# Avoid duplicating order if already tracked
			if not any(d["order_no"] == l.order_no for d in data):
				data.append({
					"timestamp": l.timestamp,
					"pos_profile": l.pos_profile,
					"order_no": l.order_no,
					"table_label": "-",
					"cancellation_type": l.cancellation_type,
					"void_value": flt(l.void_value, 2),
					"reason": l.reason or "Voided in POS",
					"user": l.user,
				})
	except Exception:
		pass

	data.sort(key=lambda x: str(x["timestamp"]), reverse=True)
	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_count = len(data)
	tot_void_val = sum(d["void_value"] for d in data)

	return [
		{"value": tot_count, "label": _("Total Voids / Cancels"), "datatype": "Int", "indicator": "Red"},
		{"value": tot_void_val, "label": _("Total Void Value"), "datatype": "Currency", "currency": currency, "indicator": "Red"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_reason = defaultdict(float)
	for d in data:
		r = d["reason"][:20] if d["reason"] else "Other"
		by_reason[r] += flt(d["void_value"])

	labels = list(by_reason.keys())[:10]
	values = [round(by_reason[k], 2) for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Void Amount"), "values": values}],
		},
		"type": "bar",
		"colors": ["#ef4444"],
	}
