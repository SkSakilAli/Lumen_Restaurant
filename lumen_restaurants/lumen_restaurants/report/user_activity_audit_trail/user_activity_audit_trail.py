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
		{"label": _("Timestamp"), "fieldname": "timestamp", "fieldtype": "Datetime", "width": 140},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
		{"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Action"), "fieldname": "action", "fieldtype": "Data", "width": 140},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Ref DocType"), "fieldname": "ref_doctype", "fieldtype": "Data", "width": 120},
		{"label": _("Ref Name"), "fieldname": "ref_name", "fieldtype": "Dynamic Link", "options": "ref_doctype", "width": 140},
		{"label": _("Details"), "fieldname": "detail", "fieldtype": "Data", "width": 220},
	]


def get_data(filters):
	conditions = ["1=1"]
	params = {}

	if filters.get("from_date"):
		conditions.append("DATE(al.creation) >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("DATE(al.creation) <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("pos_profile"):
		conditions.append("al.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	if filters.get("user"):
		conditions.append("al.user = %(user)s")
		params["user"] = filters.user

	if filters.get("action"):
		conditions.append("al.action LIKE %(action)s")
		params["action"] = f"%{filters.action}%"

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			al.creation as timestamp,
			al.pos_profile,
			al.user,
			al.action,
			COALESCE(al.amount, 0) as amount,
			al.reference_doctype as ref_doctype,
			al.reference_name as ref_name,
			al.detail
		FROM `tabLumenPOS Audit Log` al
		WHERE {where_clause}
		ORDER BY al.creation DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		data.append({
			"timestamp": r.timestamp,
			"pos_profile": r.pos_profile,
			"user": r.user,
			"action": r.action,
			"amount": flt(r.amount, 2),
			"ref_doctype": r.ref_doctype,
			"ref_name": r.ref_name,
			"detail": r.detail or "-",
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_events = len(data)
	actions = set(d["action"] for d in data)
	users = set(d["user"] for d in data)

	return [
		{"value": tot_events, "label": _("Audit Events"), "datatype": "Int", "indicator": "Blue"},
		{"value": len(actions), "label": _("Action Types"), "datatype": "Int"},
		{"value": len(users), "label": _("Active Users"), "datatype": "Int"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_action = defaultdict(int)
	for d in data:
		act = d["action"] or "Other"
		by_action[act] += 1

	labels = list(by_action.keys())[:8]
	vals = [by_action[k] for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Event Count"), "values": vals}],
		},
		"type": "bar",
		"colors": ["#6366f1"],
	}
