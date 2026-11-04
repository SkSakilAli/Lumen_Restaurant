# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Lumen Restaurants: the floor plan of a restaurant outlet (0.1.0-r14).

The Tables screen draws each area of the outlet as a plan: its tables with
their chairs, in their shape and where they stand, and the walls, doors and
the rest around them (POS Floor Area). An outlet switches it off on its POS
Profile (`lr_floor_plan`) and keeps the list of tables only, as before. Who
may change the plan is its own permission, "Edit the floor plan"
(permissions.EDIT_FLOOR), closed until a restaurant names someone.

The screen's calls are in api/floor.py, the floor itself in
api/restaurant.get_floor.
"""

import frappe
from frappe.utils import cint

CUSTOM_FIELDS = {
    "POS Profile": [
        dict(
            fieldname="lr_floor_plan",
            label="Show the tables as a floor plan",
            fieldtype="Check",
            default="1",
            insert_after="lr_addons_free_on_receipt",
            depends_on="lumenpos_restaurant_mode",
            description="On: the Tables screen draws the plan and the list stays available. "
            "Off: the list only.",
        ),
    ],
}

# The kinds of things drawn on a plan, as stored (POS Floor Object, kind) and
# as the screen names them.
KINDS = {
    "Wall": "wall",
    "Door": "door",
    "Window": "window",
    "Fence": "fence",
    "Plant": "plant",
    "Cashier": "cashier",
    "Kitchen": "kitchen",
    "Restrooms": "wc",
    "Hand wash": "sink",
}
SHAPES = {"Round": "round", "Square": "square", "Rectangle": "rect", "Booth": "booth"}

# The drawing is 1000 by 648 units: the floor runs from 30 to 970 across and
# from 30 to 590 down, and anything may stand a little outside it.
LIMIT_X = (0, 1000)
LIMIT_Y = (0, 640)


def ensure_setup():
    """after_install and after_migrate: the outlet's switch, next to the
    add-on switches. A commit first, Frappe refuses the table change after a
    write in the same transaction."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    # Before the table change: MariaDB commits by itself on DDL, and Frappe
    # refuses DDL after a write in the same transaction.
    frappe.db.commit()  # nosemgrep
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)


def plan_on(profile):
    """Does this outlet draw its tables as a plan? A site that has not
    migrated yet has no such field and reads the default, on."""
    if isinstance(profile, str):
        profile = frappe.get_cached_doc("POS Profile", profile)
    value = profile.get("lr_floor_plan")
    return bool(cint(profile.get("lumenpos_restaurant_mode")) and (1 if value is None else cint(value)))
