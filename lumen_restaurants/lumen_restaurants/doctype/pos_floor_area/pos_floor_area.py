# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""One area of a restaurant's floor plan (the hall, the family section, the
terrace): its walls, doors and the rest, and a photo of the real floor under
it. Lumen Restaurants 0.1.0-r14.

The tables are not listed here: each POS Restaurant Table names its area, as it
always did, so a site that never opens the plan keeps working as before. An
area is made the first time a manager saves the plan of an outlet whose tables
already name it.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class POSFloorArea(Document):
    def validate(self):
        self.area_name = (self.area_name or "").strip()
        if not self.area_name:
            frappe.throw(_("Give the area a name"))
        twin = frappe.db.exists(
            "POS Floor Area",
            {"pos_profile": self.pos_profile, "area_name": self.area_name, "name": ("!=", self.name or "")},
        )
        if twin:
            frappe.throw(_("{0} already has an area named {1}").format(self.pos_profile, self.area_name))
        opacity = self.photo_opacity if self.photo_opacity is not None else 50
        self.photo_opacity = min(100, max(10, int(opacity or 50)))

    def on_trash(self):
        tables = frappe.db.count(
            "POS Restaurant Table", {"pos_profile": self.pos_profile, "area": self.area_name}
        )
        if tables:
            frappe.throw(
                _("{0} still has {1} tables. Move them to another area first.").format(self.area_name, tables)
            )
