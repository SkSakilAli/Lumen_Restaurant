// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Cancelled Orders Void Bills"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
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
			fieldname: "pos_profile",
			label: __("Outlet / POS Profile"),
			fieldtype: "Link",
			options: "POS Profile",
		},
		{
			fieldname: "user",
			label: __("User / Cashier"),
			fieldtype: "Link",
			options: "User",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "reason") {
			value = `<span style="color: #ef4444;">${value}</span>`;
		}
		return value;
	},
};
