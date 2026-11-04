# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Lumen Restaurants: the settings a restaurant site starts with where
LumenPOS's defaults are a shop's (0.1.0-r15).

"A shift belongs to" (LumenPOS Settings, `shift_scope`). LumenPOS 0.60.1 made
"Per cashier" its default: each cashier opens a shift of their own. A
restaurant has several waiters taking money on one shift at one register, and
on ERPNext 16 an outlet allows one open shift at a time, so with "Per cashier"
a new restaurant site would let only one of them sell. A Lumen Restaurants site
therefore starts on "Per outlet": one shift for the outlet, everyone assigned
to it sells on it. The restaurant can still choose otherwise in Settings,
General, Register and shifts, and a stored choice is never changed here.

LumenPOS's own code and its default stay as they are (its patch
v0_60.keep_shift_scope keeps a site that already has shifts on what it ran).
This module writes the choice down: at install, and once on a site installed
before r15 that never stored one (patch lr_r15.restaurant_shift_scope).
"""

import frappe

DOCTYPE = "LumenPOS Settings"
SHIFT_SCOPE = "Per outlet"


def _stored():
    row = frappe.db.sql("select value from tabSingles where doctype=%s and field='shift_scope'", DOCTYPE)
    return row[0][0] if row else None


def _has_shifts():
    if not frappe.db.table_exists("POS Register Session"):
        return False
    return bool(frappe.db.sql("select name from `tabPOS Register Session` limit 1"))


def _write(value):
    frappe.db.sql("delete from tabSingles where doctype=%s and field='shift_scope'", DOCTYPE)
    frappe.db.sql("insert into tabSingles (doctype, field, value) values (%s, 'shift_scope', %s)", (DOCTYPE, value))
    frappe.clear_cache(doctype=DOCTYPE)


def _ready():
    return frappe.db.exists("DocType", DOCTYPE) and frappe.get_meta(DOCTYPE).has_field("shift_scope")


def after_install():
    """A site that has never sold starts on "Per outlet", whatever the install
    itself stored. A site that already has shifts (one moved across from
    LumenPOS) keeps its stored choice, or the "Per outlet" it ran through the
    old fallback when it stored none."""
    if not _ready():
        return
    if _has_shifts() and _stored():
        return
    _write(SHIFT_SCOPE)


def keep_restaurant_default():
    """The patch: a site that never stored a choice gets the restaurant's."""
    if not _ready() or _stored():
        return
    _write(SHIFT_SCOPE)
