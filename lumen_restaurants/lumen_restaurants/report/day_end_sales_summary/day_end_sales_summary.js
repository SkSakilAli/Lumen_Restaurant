// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Day End Sales Summary"] = {
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
			fieldname: "owner",
			label: __("Cashier / User"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["Outlet & Date", "Outlet", "Date", "Cashier"],
			default: "Outlet & Date",
		},
	],
};
