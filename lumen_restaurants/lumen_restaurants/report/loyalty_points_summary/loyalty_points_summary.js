// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only

frappe.query_reports["Loyalty Points Summary"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "loyalty_program",
			label: __("Loyalty Program"),
			fieldtype: "Link",
			options: "Loyalty Program",
		},
	],
};
