# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""An order that is still being served: a table, a takeaway, a delivery.

Nothing here is accounting. The money only exists once the order is paid, and
then it is an ordinary POS Invoice like any other sale, linked back from
`invoices`. What this document holds is what the restaurant needs while the
guests are still sitting there: which table, how many of them, what has been
ordered, who opened it and when.

The lines are DERIVED from the cart snapshot, never typed: `cart` is what the
till sends (prices, discounts, bundles, serials and all), and `items` is the
readable, reportable view of it that Desk, a report or the kitchen can use. One
source, two shapes, so they cannot disagree.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class POSRestaurantOrder(Document):
    def validate(self):
        if self.pos_profile and not self.company:
            self.company = frappe.db.get_value("POS Profile", self.pos_profile, "company")
        self._check_table()
        for row in self.items or []:
            row.amount = flt(flt(row.qty) * flt(row.rate), 2)
        self.total = flt(sum(flt(row.amount) for row in (self.items or [])), 2)
        if self.customer and not self.customer_name:
            self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")
        if flt(self.guests) < 0:
            self.guests = 0

    def _check_table(self):
        """A table belongs to one outlet, and serves one open order at a time."""
        if not self.table:
            self.table_label = None
            return
        table = frappe.db.get_value(
            "POS Restaurant Table", self.table, ["pos_profile", "table_no", "area"], as_dict=True
        )
        if not table:
            frappe.throw(_("Table {0} no longer exists").format(self.table))
        if table.pos_profile != self.pos_profile:
            frappe.throw(_("Table {0} belongs to another outlet").format(table.table_no))
        self.table_label = f"{table.area} {table.table_no}".strip() if table.area else table.table_no
        if self.status != "Open":
            return
        twin = frappe.db.exists(
            "POS Restaurant Order",
            {"table": self.table, "status": "Open", "name": ("!=", self.name or "")},
        )
        if twin:
            frappe.throw(
                _("Table {0} already has an open order ({1})").format(table.table_no, twin)
            )
