// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Reorder Minimum Stock Report"] = {
	filters: [
		{
			fieldname: "warehouse",
			label: __("Warehouse / Kitchen Store"),
			fieldtype: "Link",
			options: "Warehouse",
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
		if (column.fieldname === "shortage_qty" && flt(data.shortage_qty) > 0) {
			value = `<span style="color: red; font-weight: bold;">-${value}</span>`;
		}
		return value;
	},
};
