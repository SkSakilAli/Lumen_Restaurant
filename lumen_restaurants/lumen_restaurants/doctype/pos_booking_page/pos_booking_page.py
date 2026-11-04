# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""One outlet's public booking page, as its owner designed it.

The page at /book/<outlet> is drawn entirely from this document: the brand,
the colours and font, the rules (hours, slots, capacity, closed days), the
extra questions the owner added and the packages a customer can pick (a
buffet priced per guest, a birthday cake). Nothing here is trusted from the
browser at booking time: reservations.book_online re-reads this document and
validates every answer and every package against it.

The values are normalised on every save so a bad colour or an impossible rule
can never reach a customer's screen.
"""

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_time

HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")
DEFAULT_COLOURS = {
    "primary_color": "#1463ff",
    "card_color": "#ffffff",
    "background_color": "#f3f5f9",
    "background_color_2": "#dfe7f5",
}


class POSBookingPage(Document):
    def validate(self):
        for field, fallback in DEFAULT_COLOURS.items():
            value = (self.get(field) or "").strip()
            self.set(field, value if HEX.match(value) else fallback)

        self.slot_minutes = min(max(cint(self.slot_minutes) or 30, 10), 240)
        self.days_ahead = min(max(cint(self.days_ahead) or 14, 1), 90)
        self.min_guests = max(cint(self.min_guests) or 1, 1)
        self.max_guests = max(cint(self.max_guests) or 12, self.min_guests)
        self.slot_capacity = max(cint(self.slot_capacity), 0)
        if get_time(str(self.open_time or "12:00:00")) >= get_time(str(self.close_time or "23:30:00")):
            frappe.throw(_("Bookings have to open before they close"))

        for row in self.fields or []:
            row.label = (row.label or "").strip()
            row.label_en = (row.label_en or "").strip() or None
            if not row.key:
                row.key = frappe.generate_hash(length=8)
            if row.fieldtype == "Select":
                choices = [line.strip() for line in (row.options or "").splitlines() if line.strip()]
                if not choices:
                    frappe.throw(_("The list field {0} needs at least one choice").format(row.label))
                row.options = "\n".join(choices)

        seen = set()
        for row in self.items or []:
            if row.item_code in seen:
                frappe.throw(_("{0} is on the page twice").format(row.item_code))
            seen.add(row.item_code)
            row.max_qty = max(cint(row.max_qty) or 10, 1)
            if row.pricing not in ("Per guest", "Per booking"):
                row.pricing = "Per booking"
