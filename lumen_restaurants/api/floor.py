# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""The floor plan's own calls (Lumen Restaurants 0.1.0-r14): the outlet's
switch in Settings, and saving the plan from the Tables screen's edit mode.

Saving takes the whole plan at once, areas and tables, and checks all of it
before anything is written, so a plan is never saved half way: two tables with
one number, a table with an open order taken out of service or deleted, an
area deleted while tables still stand in it, all refuse the save as a whole.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint

from lumen_restaurants import floor
from lumen_restaurants.api import permissions, restaurant

TABLE = restaurant.TABLE
ORDER = restaurant.ORDER
AREA = "POS Floor Area"

# How many seats each shape takes, as the screen offers them.
SEAT_RANGE = {"round": (1, 12), "square": (1, 8), "rect": (2, 12), "booth": (2, 8)}
SHAPE_NAMES = {code: name for name, code in floor.SHAPES.items()}
KIND_NAMES = {code: name for name, code in floor.KINDS.items()}
MAX_TABLES = 400
MAX_AREAS = 40
MAX_OBJECTS = 300


def _load(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _clean(value, limit=140):
    return str(value or "").strip()[:limit]


def _clamp(value, low, high):
    return max(low, min(high, cint(value)))


@frappe.whitelist()
def get_outlet_options(pos_profile: str):
    restaurant._assert_outlet(pos_profile)
    return {"floor_plan": floor.plan_on(pos_profile)}


@frappe.whitelist()
def save_outlet_options(pos_profile: str, options: dict | list | str):
    """The outlet's switch: draw the tables as a plan, or list them. A
    manager's call, like the add-on switches."""
    restaurant._assert_outlet(pos_profile)
    if not permissions.is_manager():
        frappe.throw(_("Only a manager can change this"), frappe.PermissionError)
    options = _load(options, {})
    doc = frappe.get_doc("POS Profile", pos_profile)
    if "floor_plan" in options and doc.meta.has_field("lr_floor_plan"):
        doc.lr_floor_plan = 1 if cint(options["floor_plan"]) else 0
    # Only this switch changes: ERPNext's own checks of the profile are for
    # the fields its form edits.
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)
    return {"floor_plan": floor.plan_on(doc)}


def _clean_objects(rows):
    out = []
    for row in (rows or [])[:MAX_OBJECTS]:
        kind = KIND_NAMES.get(row.get("kind"))
        if not kind:
            continue
        out.append(
            {
                "kind": kind,
                "label": _clean(row.get("label")) or None,
                "pos_x": _clamp(row.get("x"), *floor.LIMIT_X),
                "pos_y": _clamp(row.get("y"), *floor.LIMIT_Y),
                "width": _clamp(row.get("w"), 0, 1000),
                "depth": _clamp(row.get("h"), 0, 1000),
                "rotation": cint(row.get("rot")) % 360,
            }
        )
    return out


def _attach_photo(url, area):
    """A photo uploaded in edit mode is private and belongs to nobody yet: give
    it to its area, so everyone who may see the floor may see the photo."""
    if not url or not url.startswith("/private/files/"):
        return
    for name in frappe.get_all("File", filters={"file_url": url, "attached_to_name": ["is", "not set"]}, pluck="name"):
        frappe.db.set_value(
            "File", name, {"attached_to_doctype": AREA, "attached_to_name": area, "attached_to_field": "photo"}
        )


@frappe.whitelist()
def save_plan(pos_profile: str, plan: dict | list | str):
    """Save the floor plan of an outlet as the edit mode left it.

    `plan` = {areas: [{name, area_name, old_name, photo, photo_opacity,
    objects: [{kind, label, x, y, w, h, rot}]}], tables: [{name, table_no,
    area, seats, shape, x, y, rot, disabled}], deleted_tables: [name],
    deleted_areas: [name]}. A table or an area without a name is new. A table
    names its area by the area's name in this same plan."""
    restaurant._assert_outlet(pos_profile)
    restaurant._assert_enabled(pos_profile)
    if not floor.plan_on(pos_profile):
        frappe.throw(
            _("The floor plan is switched off for {0}. Switch it on in Settings, General, Restaurant.").format(
                pos_profile
            )
        )
    if not permissions.can_edit_floor():
        frappe.throw(
            _("You are not allowed to do that: {0}").format(_(permissions.EDIT_FLOOR)),
            frappe.PermissionError,
        )
    plan = _load(plan, {})
    areas = plan.get("areas") or []
    tables = plan.get("tables") or []
    deleted_tables = set(plan.get("deleted_tables") or [])
    deleted_areas = set(plan.get("deleted_areas") or [])
    if len(areas) > MAX_AREAS or len(tables) > MAX_TABLES:
        frappe.throw(_("That plan is too big to save at once"))

    # ---- everything is checked before anything is written ----------------
    records = {
        r.name: r
        for r in frappe.get_all(AREA, filters={"pos_profile": pos_profile}, fields=["name", "area_name"])
    }
    area_names = []
    renames = []
    for area in areas:
        name = _clean(area.get("area_name"))
        if not name:
            frappe.throw(_("Give every area a name"))
        if name.casefold() in (n.casefold() for n in area_names):
            frappe.throw(_("Two areas are named {0}").format(name))
        area_names.append(name)
        if area.get("name") and area["name"] not in records:
            frappe.throw(_("That area belongs to another outlet"))
        old = records[area["name"]].area_name if area.get("name") else area.get("old_name")
        if old is not None and _clean(old) != name:
            renames.append((_clean(old), name))
    for name in deleted_areas:
        if name not in records:
            frappe.throw(_("That area belongs to another outlet"))
    known = {
        r.name: r
        for r in frappe.get_all(TABLE, filters={"pos_profile": pos_profile}, fields=["name", "table_no", "area", "disabled"])
    }
    open_on = {
        row.table: row.name
        for row in frappe.get_all(
            ORDER, filters={"pos_profile": pos_profile, "status": "Open", "table": ["is", "set"]}, fields=["name", "table"]
        )
    }
    for name in deleted_tables:
        if name not in known:
            frappe.throw(_("That table belongs to another outlet"))
        if name in open_on:
            frappe.throw(
                _("Table {0} has an open order. Move or close it first.").format(known[name].table_no)
            )
        # Its past orders and bookings point at it: it stays in the records.
        if frappe.db.exists(ORDER, {"table": name}) or frappe.db.exists("POS Table Reservation", {"table": name}):
            frappe.throw(
                _("Table {0} has past orders or bookings, so it stays in the records. Take it out of service instead.").format(
                    known[name].table_no
                )
            )
    numbers = {}
    cleaned = []
    for row in tables:
        name = row.get("name") or None
        if name and name not in known:
            frappe.throw(_("That table belongs to another outlet"))
        if name in deleted_tables:
            continue
        number = _clean(row.get("table_no"), 40)
        if not number:
            frappe.throw(_("Give every table a number"))
        if number.casefold() in numbers:
            frappe.throw(_("Two tables are numbered {0}").format(number))
        numbers[number.casefold()] = name
        area = _clean(row.get("area"))
        if area not in area_names:
            frappe.throw(_("Table {0} stands in an area that is not on the plan").format(number))
        shape = row.get("shape") if row.get("shape") in SEAT_RANGE else "square"
        low, high = SEAT_RANGE[shape]
        disabled = 1 if cint(row.get("disabled")) else 0
        if disabled and name in open_on:
            frappe.throw(_("Table {0} has an open order. Move or close it first.").format(number))
        cleaned.append(
            {
                "name": name,
                "table_no": number,
                "area": area,
                "seats": _clamp(row.get("seats") or low, low, high),
                "shape": SHAPE_NAMES[shape],
                "pos_x": _clamp(row.get("x"), *floor.LIMIT_X),
                "pos_y": _clamp(row.get("y"), *floor.LIMIT_Y),
                "rotation": cint(row.get("rot")) % 360,
                "disabled": disabled,
            }
        )
    in_plan = {row["name"] for row in cleaned if row["name"]}
    # A table made elsewhere while the plan was open (Settings) keeps its number.
    moved = dict(renames)
    for name, row in known.items():
        if name in in_plan or name in deleted_tables:
            continue
        if (row.table_no or "").strip().casefold() in numbers:
            frappe.throw(_("Table {0} already exists at this outlet").format(row.table_no))
        area = moved.get((row.area or "").strip(), (row.area or "").strip())
        if area not in area_names:
            frappe.throw(_("Table {0} stands in an area that is not on the plan").format(row.table_no))
    leaving = {records[name].area_name for name in deleted_areas}
    for area in leaving:
        if area in area_names:
            continue
        if any(row["area"] == area for row in cleaned):
            frappe.throw(_("{0} still has tables. Move them to another area first.").format(area))

    # ---- write -------------------------------------------------------------
    # The tables follow their area's new name, a swap of two names included.
    for i, (old, _new) in enumerate(renames):
        frappe.db.sql(
            "update `tabPOS Restaurant Table` set area = %s where pos_profile = %s and ifnull(area, '') = %s",
            (f"\x01{i}", pos_profile, old),
        )
    for i, (_old, new) in enumerate(renames):
        frappe.db.sql(
            "update `tabPOS Restaurant Table` set area = %s where pos_profile = %s and area = %s",
            (new, pos_profile, f"\x01{i}"),
        )
    # Checked above: no table stands in an area being deleted once the plan is
    # saved (its own check would count the tables before they move).
    for name in deleted_areas:
        frappe.delete_doc(AREA, name, ignore_permissions=True, ignore_on_trash=True)
    # Two areas trading names would meet half way: out of the way first.
    for area in areas:
        if area.get("name"):
            frappe.db.set_value(AREA, area["name"], "area_name", f"\x01{area['name']}", update_modified=False)
    for i, area in enumerate(areas):
        doc = frappe.get_doc(AREA, area["name"]) if area.get("name") else frappe.new_doc(AREA)
        doc.pos_profile = pos_profile
        doc.area_name = _clean(area.get("area_name"))
        doc.sort_order = i
        photo = _clean(area.get("photo"), 500) or None
        doc.photo = photo if photo and photo.startswith(("/files/", "/private/files/")) else None
        doc.photo_opacity = _clamp(area.get("photo_opacity") or 50, 10, 100)
        doc.set("objects", _clean_objects(area.get("objects")))
        doc.save(ignore_permissions=True)
        _attach_photo(doc.photo, doc.name)
    # Two tables trading numbers would meet half way too.
    for row in cleaned:
        if row["name"] and (known[row["name"]].table_no or "").strip() != row["table_no"]:
            frappe.db.set_value(TABLE, row["name"], "table_no", f"\x01{row['name']}", update_modified=False)
    for name in deleted_tables:
        frappe.delete_doc(TABLE, name, ignore_permissions=True)
    for row in cleaned:
        doc = frappe.get_doc(TABLE, row["name"]) if row["name"] else frappe.new_doc(TABLE)
        doc.pos_profile = pos_profile
        for field in ("table_no", "area", "seats", "shape", "pos_x", "pos_y", "rotation", "disabled"):
            doc.set(field, row[field])
        doc.save(ignore_permissions=True)
    return restaurant.get_floor(pos_profile)
