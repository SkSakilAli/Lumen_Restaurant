# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""The little machine behind "order number 47".

One row per outlet per day. The number a takeaway customer is called by has to
be SHORT (nobody shouts an invoice name across a food court), START AT 1 EACH
DAY, and never repeat within the day even with two tills selling at once.
So the row is taken with a row lock inside the sale's own transaction: if the
sale fails, the number was never handed out.

The day is the restaurant's working day, the day the shift opened: a shift
that sells on past midnight keeps counting until it closes, and the first
shift of the next day starts again at 1 (the owner, 2026-10-01).
"""

import frappe
from frappe.model.document import Document
from frappe.utils import cint, getdate, nowdate


class POSDailyCounter(Document):
    def autoname(self):
        self.name = f"{self.pos_profile} - {self.date}"


def next_order_no(pos_profile, day=None):
    """The next number of the day for this outlet, race safe. `day` is the
    working day the number belongs to (the day the sale's shift opened),
    today when not given.

    SELECT ... FOR UPDATE serialises two tills asking at the same moment. The
    insert race on the very first order of the day is settled by the unique
    document name, and the loser simply reads the row the winner made."""
    today = getdate(day).isoformat() if day else nowdate()
    name = f"{pos_profile} - {today}"
    for _ in range(3):
        current = frappe.db.get_value("POS Daily Counter", name, "current", for_update=True)
        if current is None:
            try:
                frappe.get_doc(
                    {
                        "doctype": "POS Daily Counter",
                        "pos_profile": pos_profile,
                        "date": today,
                        "current": 0,
                    }
                ).insert(ignore_permissions=True)
            except frappe.DuplicateEntryError:
                pass
            current = frappe.db.get_value("POS Daily Counter", name, "current", for_update=True)
            if current is None:
                continue
        nxt = cint(current) + 1
        frappe.db.set_value("POS Daily Counter", name, "current", nxt, update_modified=False)
        return nxt
    frappe.throw(frappe._("Could not reserve an order number, try again"))
