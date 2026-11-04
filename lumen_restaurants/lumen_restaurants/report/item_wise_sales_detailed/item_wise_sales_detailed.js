// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Item-wise Sales Detailed"] = {
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
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return {
					filters: company ? { company: company } : {},
				};
			},
		},
		{
			fieldname: "item_group",
			label: __("Menu Category / Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "item_code",
			label: __("Menu Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "view_type",
			label: __("View Mode"),
			fieldtype: "Select",
			options: ["Detailed (By Invoice Line)", "Summary (By Menu Item)"],
			default: "Detailed (By Invoice Line)",
		},
	],
};
