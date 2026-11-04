# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns(filters)
	data = get_data(filters)
	report_summary = get_report_summary(data)
	chart = get_chart_data(data)

	return columns, data, None, chart, report_summary


def get_columns(filters):
	return [
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
		{"label": _("Loyalty Program"), "fieldname": "loyalty_program", "fieldtype": "Link", "options": "Loyalty Program", "width": 140},
		{"label": _("Points Earned"), "fieldname": "points_earned", "fieldtype": "Int", "width": 110},
		{"label": _("Points Redeemed"), "fieldname": "points_redeemed", "fieldtype": "Int", "width": 120},
		{"label": _("Balance Points"), "fieldname": "balance_points", "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	conditions = ["1=1"]
	params = {}

	if filters.get("customer"):
		conditions.append("lpe.customer = %(customer)s")
		params["customer"] = filters.customer

	if filters.get("loyalty_program"):
		conditions.append("lpe.loyalty_program = %(loyalty_program)s")
		params["loyalty_program"] = filters.loyalty_program

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			lpe.customer,
			c.customer_name,
			lpe.loyalty_program,
			SUM(CASE WHEN lpe.loyalty_points > 0 THEN lpe.loyalty_points ELSE 0 END) as points_earned,
			SUM(CASE WHEN lpe.loyalty_points < 0 THEN ABS(lpe.loyalty_points) ELSE 0 END) as points_redeemed,
			SUM(lpe.loyalty_points) as balance_points
		FROM `tabLoyalty Point Entry` lpe
		LEFT JOIN `tabCustomer` c ON c.name = lpe.customer
		WHERE {where_clause}
		GROUP BY lpe.customer, c.customer_name, lpe.loyalty_program
		ORDER BY balance_points DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	data = []
	for r in rows:
		data.append({
			"customer": r.customer,
			"customer_name": r.customer_name or r.customer,
			"loyalty_program": r.loyalty_program or "-",
			"points_earned": int(r.points_earned or 0),
			"points_redeemed": int(r.points_redeemed or 0),
			"balance_points": int(r.balance_points or 0),
		})

	return data


def get_report_summary(data):
	if not data:
		return None

	tot_earned = sum(d["points_earned"] for d in data)
	tot_redeemed = sum(d["points_redeemed"] for d in data)
	tot_balance = sum(d["balance_points"] for d in data)

	return [
		{"value": len(data), "label": _("Enrolled Members"), "datatype": "Int"},
		{"value": tot_earned, "label": _("Total Points Earned"), "datatype": "Int"},
		{"value": tot_redeemed, "label": _("Total Points Redeemed"), "datatype": "Int"},
		{"value": tot_balance, "label": _("Outstanding Balance"), "datatype": "Int", "indicator": "Green"},
	]


def get_chart_data(data):
	if not data:
		return None

	labels = [d["customer_name"][:16] for d in data[:8]]
	balances = [d["balance_points"] for d in data[:8]]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Balance Points"), "values": balances}],
		},
		"type": "bar",
		"colors": ["#10b981"],
	}
