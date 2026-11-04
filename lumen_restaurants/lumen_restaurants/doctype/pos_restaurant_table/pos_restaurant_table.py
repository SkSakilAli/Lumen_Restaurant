# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""A table in a restaurant outlet.

The document name is a stable TBL-#### so a table can be renumbered or moved to
another area without breaking the orders that point at it. What the staff see
is `table_no`, and it is the outlet that makes it unique: two branches may both
have a table 12, one branch may not.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class POSRestaurantTable(Document):
    def validate(self):
        self.table_no = (self.table_no or "").strip()
        self.area = (self.area or "").strip()
        if not self.table_no:
            frappe.throw(_("Give the table a number or a name"))
        twin = frappe.db.exists(
            "POS Restaurant Table",
            {"pos_profile": self.pos_profile, "table_no": self.table_no, "name": ("!=", self.name)},
        )
        if twin:
            frappe.throw(_("Table {0} already exists at this outlet").format(self.table_no))

    def on_trash(self):
        open_order = frappe.db.exists(
            "POS Restaurant Order", {"table": self.name, "status": "Open"}
        )
        if open_order:
            frappe.throw(
                _("Table {0} has an open order ({1}). Close or cancel it first.").format(
                    self.table_no, open_order
                )
            )

    @property
    def label(self):
        return f"{self.area} {self.table_no}".strip() if self.area else self.table_no
