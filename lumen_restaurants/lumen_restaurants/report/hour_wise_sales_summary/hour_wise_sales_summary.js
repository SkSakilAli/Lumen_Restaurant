// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Hour-wise Sales Summary"] = {
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
			default: frappe.datetime.get_today(),
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
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return {
					filters: company ? { company: company } : {},
				};
			},
		},
		{
			fieldname: "order_type",
			label: __("Order Type"),
			fieldtype: "Select",
			options: ["", "Dine In", "Takeaway", "Delivery", "Aggregator"],
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "hour_slot") {
			value = `<b>${value}</b>`;
		}
		return value;
	},
};
