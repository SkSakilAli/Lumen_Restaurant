// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Daily Cashier Closing"] = {
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
			fieldname: "opened_by",
			label: __("Cashier / User"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "status",
			label: __("Session Status"),
			fieldtype: "Select",
			options: ["", "Open", "Closed"],
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "short_over") {
			const num = flt(data.short_over);
			if (num < 0) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (num > 0) {
				value = `<span style="color: green; font-weight: bold;">+${value}</span>`;
			}
		}
		return value;
	},
};
