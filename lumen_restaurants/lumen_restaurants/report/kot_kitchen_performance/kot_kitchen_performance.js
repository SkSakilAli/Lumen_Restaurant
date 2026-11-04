// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["KOT Kitchen Performance"] = {
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
			fieldname: "station",
			label: __("Kitchen Station"),
			fieldtype: "Data",
		},
		{
			fieldname: "status",
			label: __("KOT Status"),
			fieldtype: "Select",
			options: ["", "Pending", "Started", "Ready", "Delivered", "Cancelled"],
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "delay_mins") {
			const d = flt(data.delay_mins);
			if (d > 0) {
				value = `<span style="color: red; font-weight: bold;">+${value} min</span>`;
			}
		}
		return value;
	},
};
