// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Slow-moving Stock Report"] = {
	filters: [
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "inactive_days",
			label: __("Inactive Days Threshold"),
			fieldtype: "Int",
			default: 30,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "days_inactive") {
			const days = flt(data.days_inactive);
			if (days >= 90) {
				value = `<span style="color: red; font-weight: bold;">${value} days</span>`;
			} else if (days >= 60) {
				value = `<span style="color: orange; font-weight: bold;">${value} days</span>`;
			}
		}
		return value;
	},
};
