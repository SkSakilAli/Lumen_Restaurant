# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""The booking page designer's back office.

One shape travels everywhere: the flat fields of POS Booking Page plus its two
child lists, with the prices, names and images of the packages resolved from
ERPNext beside them. The designer edits that shape, the live preview renders
it, the public page renders it, and saving maps it straight back onto the
document. There is no second copy of the design anywhere to drift.

Packages are priced from the outlet's own selling price list, never typed on
the page, so the figure a customer sees when booking is the figure the till
charges when they sit down.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, flt

PAGE = "POS Booking Page"

FLAT = [
    "published", "auto_confirm",
    "title", "title_en", "subtitle", "subtitle_en", "logo", "cover_image",
    "font", "primary_color", "card_color", "corner_style",
    "background_type", "background_color", "background_color_2", "background_image",
    "open_time", "close_time", "slot_minutes", "days_ahead",
    "min_guests", "max_guests", "slot_capacity",
    "closed_sun", "closed_mon", "closed_tue", "closed_wed", "closed_thu", "closed_fri", "closed_sat",
    "show_note", "note_label", "note_label_en",
    "terms", "terms_en", "success_message", "success_message_en",
    "contact_phone", "whatsapp", "maps_url", "website", "instagram", "snapchat", "tiktok", "x_url",
]
FIELD_KEYS = ["key", "label", "label_en", "fieldtype", "options", "required", "placeholder"]
ITEM_KEYS = ["item_code", "title", "title_en", "description", "description_en", "image", "pricing", "required", "max_qty"]
CHECKS = {"published", "auto_confirm", "show_note", "closed_sun", "closed_mon", "closed_tue",
          "closed_wed", "closed_thu", "closed_fri", "closed_sat"}


def _require(ptype):
    if not frappe.has_permission(PAGE, ptype):
        frappe.throw(_("You are not allowed to change the booking page"), frappe.PermissionError)


def _outlet(pos_profile):
    from lumen_restaurants.api import restaurant

    restaurant._assert_outlet(pos_profile)
    return frappe.get_cached_doc("POS Profile", pos_profile)


def load(pos_profile):
    """The saved page, or a fresh unsaved one with sensible defaults."""
    if frappe.db.exists(PAGE, pos_profile):
        return frappe.get_doc(PAGE, pos_profile)
    doc = frappe.new_doc(PAGE)
    # Frappe 13 to 15 give every Time field of a new document the time of day,
    # whatever its default says (16 reads the default), so a new page opened
    # and closed at the minute it was started and took no booking: put the
    # doctype's own hours back.
    for df in doc.meta.get("fields", {"fieldtype": "Time"}):
        if df.default and df.default.lower() != "now":
            doc.set(df.fieldname, df.default)
    doc.pos_profile = pos_profile
    company = frappe.db.get_value("POS Profile", pos_profile, "company")
    doc.title = company or pos_profile
    doc.title_en = company or pos_profile
    doc.subtitle = "احجز طاولتك وبنتصل نأكد الحجز"
    doc.subtitle_en = "Book your table and we will call to confirm"
    return doc


def _price(profile, item_code):
    price_list = profile.selling_price_list
    if not price_list:
        return 0
    return flt(frappe.db.get_value(
        "Item Price", {"item_code": item_code, "price_list": price_list, "selling": 1}, "price_list_rate"
    ))


def serialize(doc):
    """The one shape the designer, the preview and the public page all use."""
    profile = frappe.get_cached_doc("POS Profile", doc.pos_profile)
    data = {"pos_profile": doc.pos_profile}
    for key in FLAT:
        value = doc.get(key)
        if key.endswith("_time") and value is not None:
            value = str(value)[:8]
        data[key] = cint(value) if key in CHECKS else value
    # get(): a page not saved yet has no child lists on Frappe 13.
    data["fields"] = [{k: row.get(k) for k in FIELD_KEYS} for row in (doc.get("fields") or [])]
    data["items"] = [{k: row.get(k) for k in ITEM_KEYS} for row in (doc.get("items") or [])]
    codes = [row["item_code"] for row in data["items"] if row.get("item_code")]
    data["rates"] = {code: _price(profile, code) for code in codes}
    info = {}
    if codes:
        for row in frappe.get_all("Item", filters={"name": ("in", codes)}, fields=["name", "item_name", "image"]):
            info[row.name] = row
    data["item_names"] = {code: (info.get(code) or {}).get("item_name") or code for code in codes}
    data["item_images"] = {code: (info.get(code) or {}).get("image") for code in codes}
    data["currency"] = profile.currency or frappe.get_cached_value("Company", profile.company, "default_currency")
    data["company"] = profile.company
    return data


def apply(doc, page):
    """Map the designer's shape back onto the document."""
    for key in FLAT:
        if key not in page:
            continue
        value = page.get(key)
        if key in CHECKS:
            value = 1 if value else 0
        elif isinstance(value, str):
            value = value.strip() or None
        doc.set(key, value)
    if "fields" in page:
        doc.set("fields", [])
        for row in page.get("fields") or []:
            doc.append("fields", {k: row.get(k) for k in FIELD_KEYS})
    if "items" in page:
        doc.set("items", [])
        for row in page.get("items") or []:
            if row.get("item_code"):
                doc.append("items", {k: row.get(k) for k in ITEM_KEYS})


@frappe.whitelist()
def get_page(pos_profile: str):
    _require("read")
    _outlet(pos_profile)
    doc = load(pos_profile)
    data = serialize(doc)
    data["exists"] = not doc.is_new()
    return data


@frappe.whitelist()
def save_page(pos_profile: str, page: dict | list | str):
    _require("write")
    _outlet(pos_profile)
    if isinstance(page, str):
        page = json.loads(page or "{}")
    doc = load(pos_profile)
    apply(doc, page)
    doc.save(ignore_permissions=True) if not doc.is_new() else doc.insert(ignore_permissions=True)
    data = serialize(doc)
    data["exists"] = True
    return data


@frappe.whitelist()
def copy_design(source: str, target: str):
    """A chain designs one page and pours it into its other branches. The
    target keeps its own publish switch: copying never switches a page on."""
    _require("write")
    _outlet(target)
    if not frappe.db.exists(PAGE, source):
        frappe.throw(_("{0} has no booking page to copy").format(source))
    page = serialize(frappe.get_doc(PAGE, source))
    target_doc = load(target)
    keep = target_doc.published
    apply(target_doc, page)
    target_doc.published = keep
    target_doc.save(ignore_permissions=True) if not target_doc.is_new() else target_doc.insert(ignore_permissions=True)
    return serialize(target_doc)


@frappe.whitelist()
def item_info(pos_profile: str, item_code: str):
    """What the designer shows the moment an item is added to the page."""
    _require("read")
    profile = _outlet(pos_profile)
    row = frappe.db.get_value("Item", item_code, ["item_name", "image", "disabled"], as_dict=True)
    if not row:
        frappe.throw(_("Item {0} not found").format(item_code))
    return {
        "item_code": item_code,
        "item_name": row.item_name,
        "image": row.image,
        "rate": _price(profile, item_code),
        "disabled": cint(row.disabled),
    }
