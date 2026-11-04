// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Liquor Stock Movement"] = {
	filters: [
		{
			fieldname: "warehouse",
			label: __("Bar Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "item_code",
			label: __("Spirit / Liquor Item"),
			fieldtype: "Link",
			options: "Item",
		},
	],
};
