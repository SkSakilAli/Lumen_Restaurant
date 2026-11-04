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
		{"label": _("Session ID"), "fieldname": "session_id", "fieldtype": "Link", "options": "POS Register Session", "width": 140},
		{"label": _("Date"), "fieldname": "business_date", "fieldtype": "Date", "width": 95},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 140},
		{"label": _("Cashier"), "fieldname": "cashier", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 80},
		{"label": _("Opening Float"), "fieldname": "opening_float", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Cash Sales"), "fieldname": "cash_sales", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Non-Cash Sales"), "fieldname": "non_cash_sales", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Cash In / Out"), "fieldname": "cash_movement_net", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Expected Cash"), "fieldname": "expected_cash", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Physical Cash"), "fieldname": "counted_cash", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Short / Over"), "fieldname": "short_over", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Variance Reason"), "fieldname": "variance_reason", "fieldtype": "Data", "width": 140},
	]


def get_data(filters):
	conditions = ["1=1"]
	params = {}

	if filters.get("from_date"):
		conditions.append("DATE(s.opened_at) >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("DATE(s.opened_at) <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("pos_profile"):
		conditions.append("s.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	if filters.get("opened_by"):
		conditions.append("s.opened_by = %(opened_by)s")
		params["opened_by"] = filters.opened_by

	if filters.get("status"):
		conditions.append("s.status = %(status)s")
		params["status"] = filters.status

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			s.name as session_id,
			DATE(s.opened_at) as business_date,
			s.pos_profile,
			s.opened_by as cashier,
			s.status,
			COALESCE(s.opening_float, 0) as opening_float,
			COALESCE(s.total_sales, 0) as total_sales,
			s.variance_reason
		FROM `tabPOS Register Session` s
		WHERE {where_clause}
		ORDER BY s.opened_at DESC
	"""
	sessions = frappe.db.sql(query, params, as_dict=True)
	if not sessions:
		return []

	session_ids = [s.session_id for s in sessions]

	# Payment counts (Cash vs Non-cash)
	counts_map = defaultdict(lambda: {"cash_expected": 0.0, "cash_counted": 0.0, "non_cash": 0.0})
	try:
		counts = frappe.db.sql(
			"""
			SELECT
				parent,
				mode_of_payment,
				expected_amount,
				counted_amount,
				difference
			FROM `tabPOS Register Payment Count`
			WHERE parent IN %s
			""",
			[session_ids],
			as_dict=True,
		)
		for c in counts:
			mop = (c.mode_of_payment or "").upper()
			if "CASH" in mop:
				counts_map[c.parent]["cash_expected"] += flt(c.expected_amount)
				counts_map[c.parent]["cash_counted"] += flt(c.counted_amount)
			else:
				counts_map[c.parent]["non_cash"] += flt(c.expected_amount)
	except Exception:
		pass

	# Cash movements (Pay-in / Pay-out)
	movements_map = defaultdict(float)
	try:
		movs = frappe.db.sql(
			"""
			SELECT parent, movement_type, amount
			FROM `tabPOS Cash Movement`
			WHERE parent IN %s
			""",
			[session_ids],
			as_dict=True,
		)
		for m in movs:
			amt = flt(m.amount)
			m_type = (m.movement_type or "").upper()
			if "IN" in m_type:
				movements_map[m.parent] += amt
			else:
				movements_map[m.parent] -= amt
	except Exception:
		pass

	data = []
	for s in sessions:
		c_info = counts_map[s.session_id]
		m_net = movements_map[s.session_id]
		flt_val = flt(s.opening_float, 2)
		cash_sales = flt(c_info["cash_expected"], 2)
		non_cash = flt(c_info["non_cash"], 2)

		# Fallback if counts not populated yet:
		if not cash_sales and not non_cash and flt(s.total_sales) > 0:
			cash_sales = flt(s.total_sales, 2)

		expected_cash = flt_val + cash_sales + m_net
		physical_cash = flt(c_info["cash_counted"], 2) if s.status == "Closed" else expected_cash
		short_over = flt(physical_cash - expected_cash, 2) if s.status == "Closed" else 0.0

		data.append({
			"session_id": s.session_id,
			"business_date": s.business_date,
			"pos_profile": s.pos_profile,
			"cashier": s.cashier,
			"status": s.status,
			"opening_float": flt_val,
			"cash_sales": cash_sales,
			"non_cash_sales": non_cash,
			"cash_movement_net": m_net,
			"expected_cash": expected_cash,
			"counted_cash": physical_cash,
			"short_over": short_over,
			"variance_reason": s.variance_reason or "-",
		})

	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_sessions = len(data)
	tot_cash_sales = sum(d["cash_sales"] for d in data)
	tot_non_cash = sum(d["non_cash_sales"] for d in data)
	tot_expected = sum(d["expected_cash"] for d in data)
	tot_counted = sum(d["counted_cash"] for d in data)
	tot_variance = sum(d["short_over"] for d in data)

	return [
		{"value": tot_sessions, "label": _("Sessions Count"), "datatype": "Int"},
		{"value": tot_cash_sales, "label": _("Total Cash Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_non_cash, "label": _("Non-Cash Sales"), "datatype": "Currency", "currency": currency},
		{"value": tot_expected, "label": _("Expected Cash"), "datatype": "Currency", "currency": currency},
		{"value": tot_counted, "label": _("Physical Cash"), "datatype": "Currency", "currency": currency},
		{"value": tot_variance, "label": _("Net Short / Over"), "datatype": "Currency", "currency": currency, "indicator": "Red" if tot_variance < 0 else "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	labels = [f"{d['business_date']} ({d['cashier'][:8]})" for d in data[:15]]
	expected_vals = [flt(d["expected_cash"], 2) for d in data[:15]]
	counted_vals = [flt(d["counted_cash"], 2) for d in data[:15]]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Expected Cash"), "values": expected_vals},
				{"name": _("Physical Count"), "values": counted_vals},
			],
		},
		"type": "bar",
		"colors": ["#6366f1", "#10b981"],
	}
