# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""One ticket on the kitchen screen: what to prepare, for whom, since when.

Born either from a table order (the waiter presses "send to kitchen", possibly
several times through a meal) or from a paid takeaway sale, which carries the
short daily number the customer will be called by. The timestamps are written
by the status changes, so "average preparation today" is real, not typed."""

from frappe.model.document import Document
from frappe.utils import now_datetime


class POSKitchenTicket(Document):
    def before_insert(self):
        self.created_at = self.created_at or now_datetime()

    def validate(self):
        stamp = {
            "Preparing": "started_at",
            "Ready": "ready_at",
            "Done": "delivered_at",
        }.get(self.status)
        if stamp and not self.get(stamp):
            self.set(stamp, now_datetime())
