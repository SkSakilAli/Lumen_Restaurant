# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency") or "USD"

	view_type = filters.get("view_type") or "Detailed (By Invoice Line)"
	is_detailed = view_type.startswith("Detailed")

	columns = get_columns(is_detailed, company_currency)
	items = get_item_sales(filters)
	data = prepare_data(items, is_detailed)
	report_summary = get_report_summary(data, is_detailed, company_currency)
	chart = get_chart_data(data, is_detailed, company_currency)

	return columns, data, None, chart, report_summary


def get_columns(is_detailed, currency):
	if is_detailed:
		return [
			{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
			{"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "DynamicLink", "options": "doctype", "width": 140},
			{"label": _("Outlet"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
			{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
			{"label": _("Menu Category"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 120},
			{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
			{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 70},
			{"label": _("Menu Price"), "fieldname": "menu_price", "fieldtype": "Currency", "options": "currency", "width": 110},
			{"label": _("Selling Rate"), "fieldname": "selling_rate", "fieldtype": "Currency", "options": "currency", "width": 110},
			{"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "options": "currency", "width": 115},
			{"label": _("Item Discount"), "fieldname": "item_discount", "fieldtype": "Currency", "options": "currency", "width": 110},
			{"label": _("Bill Discount"), "fieldname": "bill_discount", "fieldtype": "Currency", "options": "currency", "width": 110},
			{"label": _("Total Discount"), "fieldname": "total_discount", "fieldtype": "Currency", "options": "currency", "width": 115},
			{"label": _("Net Revenue"), "fieldname": "net_revenue", "fieldtype": "Currency", "options": "currency", "width": 125},
			{"label": _("Effective Rate"), "fieldname": "effective_rate", "fieldtype": "Currency", "options": "currency", "width": 115},
		]
	else:
		return [
			{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
			{"label": _("Menu Category"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 130},
			{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
			{"label": _("Qty Sold"), "fieldname": "total_qty", "fieldtype": "Float", "width": 90},
			{"label": _("Menu Price"), "fieldname": "avg_menu_price", "fieldtype": "Currency", "options": "currency", "width": 110},
			{"label": _("Avg Selling Rate"), "fieldname": "avg_selling_rate", "fieldtype": "Currency", "options": "currency", "width": 115},
			{"label": _("Gross Revenue"), "fieldname": "gross_revenue", "fieldtype": "Currency", "options": "currency", "width": 120},
			{"label": _("Item Discounts"), "fieldname": "total_item_discount", "fieldtype": "Currency", "options": "currency", "width": 110},
			{"label": _("Bill Discounts"), "fieldname": "total_bill_discount", "fieldtype": "Currency", "options": "currency", "width": 110},
			{"label": _("Total Discounts"), "fieldname": "total_discount", "fieldtype": "Currency", "options": "currency", "width": 120},
			{"label": _("Net Revenue"), "fieldname": "net_revenue", "fieldtype": "Currency", "options": "currency", "width": 130},
			{"label": _("Effective Rate"), "fieldname": "effective_rate", "fieldtype": "Currency", "options": "currency", "width": 115},
			{"label": _("Sales Contribution %"), "fieldname": "revenue_pct", "fieldtype": "Percent", "width": 135},
		]


def get_item_sales(filters):
	parent_conditions = ["p.docstatus = 1"]
	item_conditions = []
	params = {}

	if filters.get("company"):
		parent_conditions.append("p.company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		parent_conditions.append("p.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		parent_conditions.append("p.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("pos_profile"):
		parent_conditions.append("p.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.pos_profile

	if filters.get("item_group"):
		item_conditions.append("i.item_group = %(item_group)s")
		params["item_group"] = filters.item_group

	if filters.get("item_code"):
		item_conditions.append("i.item_code = %(item_code)s")
		params["item_code"] = filters.item_code

	pos_conds = " AND ".join(parent_conditions + item_conditions)
	si_conds = " AND ".join(parent_conditions + ["(p.is_pos = 1 OR p.pos_profile IS NOT NULL)"] + item_conditions)

	pos_items = frappe.db.sql(
		f"""
		SELECT
			'POS Invoice' as doctype,
			p.name as invoice,
			p.posting_date,
			p.pos_profile,
			p.customer,
			i.item_code,
			i.item_name,
			i.item_group,
			i.uom,
			i.qty,
			coalesce(i.base_price_list_rate, i.price_list_rate, i.base_rate, i.rate) as menu_price,
			coalesce(i.base_rate, i.rate) as selling_rate,
			coalesce(i.base_amount, i.amount) as amount,
			i.discount_percentage,
			i.discount_amount,
			coalesce(i.distributed_discount_amount, 0) as distributed_discount_amount,
			coalesce(i.base_net_amount, i.net_amount) as net_amount,
			coalesce(i.base_net_rate, i.net_rate) as net_rate
		FROM `tabPOS Invoice Item` i
		JOIN `tabPOS Invoice` p ON p.name = i.parent
		WHERE {pos_conds}
		ORDER BY p.posting_date DESC, i.item_code ASC
		""",
		params,
		as_dict=True,
	)

	si_items = frappe.db.sql(
		f"""
		SELECT
			'Sales Invoice' as doctype,
			p.name as invoice,
			p.posting_date,
			p.pos_profile,
			p.customer,
			i.item_code,
			i.item_name,
			i.item_group,
			i.uom,
			i.qty,
			coalesce(i.base_price_list_rate, i.price_list_rate, i.base_rate, i.rate) as menu_price,
			coalesce(i.base_rate, i.rate) as selling_rate,
			coalesce(i.base_amount, i.amount) as amount,
			i.discount_percentage,
			i.discount_amount,
			coalesce(i.distributed_discount_amount, 0) as distributed_discount_amount,
			coalesce(i.base_net_amount, i.net_amount) as net_amount,
			coalesce(i.base_net_rate, i.net_rate) as net_rate
		FROM `tabSales Invoice Item` i
		JOIN `tabSales Invoice` p ON p.name = i.parent
		WHERE {si_conds}
		ORDER BY p.posting_date DESC, i.item_code ASC
		""",
		params,
		as_dict=True,
	)

	return pos_items + si_items


def prepare_data(items, is_detailed):
	if is_detailed:
		rows = []
		for item in items:
			qty = flt(item.qty)
			menu_price = flt(item.menu_price) or flt(item.selling_rate)
			selling_rate = flt(item.selling_rate)
			gross_amt = qty * menu_price

			# Calculate line discount
			if flt(item.discount_amount) > 0:
				item_disc = flt(item.discount_amount) * qty
			elif flt(item.discount_percentage) > 0:
				item_disc = (menu_price * flt(item.discount_percentage) / 100.0) * qty
			else:
				item_disc = max(0.0, (menu_price - selling_rate) * qty)

			bill_disc = flt(item.distributed_discount_amount)
			total_disc = item_disc + bill_disc
			net_rev = flt(item.net_amount) if flt(item.net_amount) != 0 else (gross_amt - total_disc)
			effective_rate = flt(net_rev / qty, 2) if qty else 0.0

			rows.append({
				"doctype": item.doctype,
				"invoice": item.invoice,
				"posting_date": item.posting_date,
				"pos_profile": item.pos_profile,
				"item_code": item.item_code,
				"item_name": item.item_name,
				"item_group": item.item_group,
				"uom": item.uom,
				"qty": qty,
				"menu_price": menu_price,
				"selling_rate": selling_rate,
				"gross_amount": gross_amt,
				"item_discount": item_disc,
				"bill_discount": bill_disc,
				"total_discount": total_disc,
				"net_revenue": net_rev,
				"effective_rate": effective_rate,
			})
		return rows

	# Aggregated Summary View
	grouped = {}
	total_overall_net = 0.0

	for item in items:
		key = item.item_code
		qty = flt(item.qty)
		menu_price = flt(item.menu_price) or flt(item.selling_rate)
		selling_rate = flt(item.selling_rate)
		gross_amt = qty * menu_price

		if flt(item.discount_amount) > 0:
			item_disc = flt(item.discount_amount) * qty
		elif flt(item.discount_percentage) > 0:
			item_disc = (menu_price * flt(item.discount_percentage) / 100.0) * qty
		else:
			item_disc = max(0.0, (menu_price - selling_rate) * qty)

		bill_disc = flt(item.distributed_discount_amount)
		total_disc = item_disc + bill_disc
		net_rev = flt(item.net_amount) if flt(item.net_amount) != 0 else (gross_amt - total_disc)

		if key not in grouped:
			grouped[key] = {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"item_group": item.item_group,
				"uom": item.uom,
				"total_qty": 0.0,
				"menu_prices": [],
				"selling_rates": [],
				"gross_revenue": 0.0,
				"total_item_discount": 0.0,
				"total_bill_discount": 0.0,
				"total_discount": 0.0,
				"net_revenue": 0.0,
			}

		g = grouped[key]
		g["total_qty"] += qty
		g["menu_prices"].append((menu_price, qty))
		g["selling_rates"].append((selling_rate, qty))
		g["gross_revenue"] += gross_amt
		g["total_item_discount"] += item_disc
		g["total_bill_discount"] += bill_disc
		g["total_discount"] += total_disc
		g["net_revenue"] += net_rev
		total_overall_net += net_rev

	summary_rows = []
	for g in grouped.values():
		t_qty = g["total_qty"] or 1.0
		# Weighted average menu price and selling rate
		avg_menu = sum(p * q for p, q in g["menu_prices"]) / t_qty if g["menu_prices"] else 0.0
		avg_selling = sum(s * q for s, q in g["selling_rates"]) / t_qty if g["selling_rates"] else 0.0

		g["avg_menu_price"] = flt(avg_menu, 2)
		g["avg_selling_rate"] = flt(avg_selling, 2)
		g["effective_rate"] = flt(g["net_revenue"] / t_qty, 2)
		g["revenue_pct"] = flt((g["net_revenue"] / total_overall_net * 100.0), 2) if total_overall_net else 0.0
		del g["menu_prices"]
		del g["selling_rates"]
		summary_rows.append(g)

	summary_rows.sort(key=lambda x: x["net_revenue"], reverse=True)
	return summary_rows


def get_report_summary(data, is_detailed, currency):
	if not data:
		return None

	if is_detailed:
		tot_qty = sum(d["qty"] for d in data)
		tot_gross = sum(d["gross_amount"] for d in data)
		tot_disc = sum(d["total_discount"] for d in data)
		tot_net = sum(d["net_revenue"] for d in data)
	else:
		tot_qty = sum(d["total_qty"] for d in data)
		tot_gross = sum(d["gross_revenue"] for d in data)
		tot_disc = sum(d["total_discount"] for d in data)
		tot_net = sum(d["net_revenue"] for d in data)

	top_item_name = data[0].get("item_name") or data[0].get("item_code") if data else "-"

	return [
		{"value": tot_qty, "label": _("Total Qty Sold"), "datatype": "Float"},
		{"value": tot_gross, "label": _("Gross Revenue"), "datatype": "Currency", "currency": currency},
		{"value": tot_disc, "label": _("Total Discounts"), "datatype": "Currency", "currency": currency},
		{"value": tot_net, "label": _("Net Revenue"), "datatype": "Currency", "currency": currency, "indicator": "Green"},
		{"value": top_item_name, "label": _("Top Selling Item"), "datatype": "Data", "indicator": "Blue"},
	]


def get_chart_data(data, is_detailed, currency):
	if not data:
		return None

	# If detailed, aggregate by item first for the top chart
	if is_detailed:
		item_totals = defaultdict(float)
		for row in data:
			item_totals[row["item_name"] or row["item_code"]] += flt(row["net_revenue"])
		sorted_items = sorted(item_totals.items(), key=lambda x: x[1], reverse=True)[:10]
		labels = [item[0] for item in sorted_items]
		values = [flt(item[1], 2) for item in sorted_items]
	else:
		top_data = data[:10]
		labels = [row["item_name"] or row["item_code"] for row in top_data]
		values = [flt(row["net_revenue"], 2) for row in top_data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Net Revenue"), "values": values},
			],
		},
		"type": "bar",
		"colors": ["#10b981"],
	}
