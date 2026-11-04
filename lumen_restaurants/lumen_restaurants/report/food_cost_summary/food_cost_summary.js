// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Food Cost Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
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
			fieldname: "pos_profile",
			label: __("Outlet / POS Profile"),
			fieldtype: "Link",
			options: "POS Profile",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "food_cost_pct") {
			const pct = flt(data.food_cost_pct);
			if (pct > 35) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (pct <= 30) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			}
		}
		return value;
	},
};
