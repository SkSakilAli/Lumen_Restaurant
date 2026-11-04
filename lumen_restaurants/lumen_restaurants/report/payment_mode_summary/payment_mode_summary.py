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
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 140},
		{"label": _("Payment Mode"), "fieldname": "mode_of_payment", "fieldtype": "Link", "options": "Mode of Payment", "width": 130},
		{"label": _("Cashier"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Txn Count"), "fieldname": "txn_count", "fieldtype": "Int", "width": 90},
		{"label": _("Tender Amount"), "fieldname": "tender_amount", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Refunds"), "fieldname": "refund_amount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("Net Collection"), "fieldname": "net_collection", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Share %"), "fieldname": "share_pct", "fieldtype": "Percent", "width": 90},
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

	if filters.get("mode_of_payment"):
		conditions.append("pay.mode_of_payment = %(mode_of_payment)s")
		params["mode_of_payment"] = filters.mode_of_payment

	if filters.get("owner"):
		conditions.append("inv.owner = %(owner)s")
		params["owner"] = filters.owner

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			inv.posting_date,
			inv.pos_profile,
			pay.mode_of_payment,
			inv.owner,
			inv.is_return,
			COUNT(DISTINCT inv.name) as txn_count,
			COALESCE(SUM(pay.base_amount), 0) as amount
		FROM `tabSales Invoice Payment` pay
		JOIN `tabPOS Invoice` inv ON inv.name = pay.parent
		WHERE {where_clause}
		GROUP BY inv.posting_date, inv.pos_profile, pay.mode_of_payment, inv.owner, inv.is_return
		ORDER BY inv.posting_date DESC, amount DESC
	"""
	rows = frappe.db.sql(query, params, as_dict=True)

	# Group by (posting_date, pos_profile, mode_of_payment, owner)
	grouped = defaultdict(lambda: {
		"txn_count": 0,
		"tender_amount": 0.0,
		"refund_amount": 0.0,
		"net_collection": 0.0,
	})

	for r in rows:
		key = (r.posting_date, r.pos_profile, r.mode_of_payment, r.owner)
		amt = flt(r.amount, 2)
		if r.is_return:
			grouped[key]["refund_amount"] += abs(amt)
		else:
			grouped[key]["tender_amount"] += amt
		grouped[key]["txn_count"] += int(r.txn_count or 0)

	tot_net = sum(g["tender_amount"] - g["refund_amount"] for g in grouped.values())

	data = []
	for (p_date, pos_prof, mop, owner), vals in grouped.items():
		net = flt(vals["tender_amount"] - vals["refund_amount"], 2)
		share = flt((net / tot_net) * 100, 2) if tot_net else 0

		data.append({
			"posting_date": p_date,
			"pos_profile": pos_prof,
			"mode_of_payment": mop,
			"owner": owner,
			"txn_count": vals["txn_count"],
			"tender_amount": flt(vals["tender_amount"], 2),
			"refund_amount": flt(vals["refund_amount"], 2),
			"net_collection": net,
			"share_pct": share,
		})

	# Sort by date desc, net_collection desc
	data.sort(key=lambda x: (x["posting_date"], x["net_collection"]), reverse=True)
	return data


def get_report_summary(data, currency):
	if not data:
		return None

	tot_txns = sum(d["txn_count"] for d in data)
	tot_tender = sum(d["tender_amount"] for d in data)
	tot_refunds = sum(d["refund_amount"] for d in data)
	tot_net = sum(d["net_collection"] for d in data)

	return [
		{"value": tot_txns, "label": _("Total Transactions"), "datatype": "Int"},
		{"value": tot_tender, "label": _("Total Tender"), "datatype": "Currency", "currency": currency},
		{"value": tot_refunds, "label": _("Total Refunds"), "datatype": "Currency", "currency": currency, "indicator": "Red" if tot_refunds else "Grey"},
		{"value": tot_net, "label": _("Net Collections"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
	]


def get_chart_data(data, currency):
	if not data:
		return None

	by_mop = defaultdict(float)
	for d in data:
		by_mop[d["mode_of_payment"] or "Other"] += flt(d["net_collection"])

	labels = list(by_mop.keys())
	values = [round(v, 2) for v in by_mop.values()]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Net Collection"), "values": values}],
		},
		"type": "donut",
		"colors": ["#10b981", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6"],
	}
