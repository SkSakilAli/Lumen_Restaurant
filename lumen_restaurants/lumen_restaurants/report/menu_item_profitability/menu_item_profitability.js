// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Menu Item Profitability"] = {
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
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "classification") {
			if (data.classification === "Star ⭐") {
				value = `<span style="color: #10b981; font-weight: bold;">${value}</span>`;
			} else if (data.classification === "Dog 🐶") {
				value = `<span style="color: #ef4444; font-weight: bold;">${value}</span>`;
			} else if (data.classification === "Plowhorse 🐴") {
				value = `<span style="color: #3b82f6; font-weight: bold;">${value}</span>`;
			} else if (data.classification === "Puzzle 🧩") {
				value = `<span style="color: #f59e0b; font-weight: bold;">${value}</span>`;
			}
		}
		return value;
	},
};
