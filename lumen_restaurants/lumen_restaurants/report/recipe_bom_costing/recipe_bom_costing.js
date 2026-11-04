// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Recipe BOM Costing"] = {
	filters: [
		{
			fieldname: "item_code",
			label: __("Menu Dish / Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "is_active",
			label: __("Active Only"),
			fieldtype: "Check",
			default: 1,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "food_cost_pct") {
			const pct = flt(data.food_cost_pct);
			if (pct > 35) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (pct <= 28) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			}
		}
		return value;
	},
};
