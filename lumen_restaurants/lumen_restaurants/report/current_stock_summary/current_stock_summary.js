// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Current Stock Summary"] = {
	filters: [
		{
			fieldname: "warehouse",
			label: __("Warehouse / Outlet Store"),
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
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
	],
};
