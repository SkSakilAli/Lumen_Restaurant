# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Something drawn on a floor plan that is not a table: a wall, a door, a
window, a fence, a plant, or a place the guests see (the cashier, the kitchen,
the restrooms, the hand wash). Lumen Restaurants 0.1.0-r14."""

from frappe.model.document import Document


class POSFloorObject(Document):
    pass
