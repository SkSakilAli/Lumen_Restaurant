# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""A table promised to somebody.

Comes in from the till (a phone call, someone at the counter) or from the
public booking page, where it lands as Requested until a person confirms it.
Nothing is ever seated or cancelled automatically: the till flags, a person
decides, and a no-show stays on the record so a shop learns who books and
never comes."""

import frappe
from frappe import _
from frappe.model.document import Document


class POSTableReservation(Document):
    def validate(self):
        self.customer_name = (self.customer_name or "").strip()
        self.phone = (self.phone or "").strip()
        if not self.customer_name:
            frappe.throw(_("A reservation needs a name"))
        if not self.phone:
            frappe.throw(_("A reservation needs a phone number"))
        if self.guests and self.guests < 1:
            self.guests = 1
        if self.table:
            table_profile = frappe.db.get_value(
                "POS Restaurant Table", self.table, "pos_profile"
            )
            if table_profile != self.pos_profile:
                frappe.throw(_("That table belongs to another outlet"))
