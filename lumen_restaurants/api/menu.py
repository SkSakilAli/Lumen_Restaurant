# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""The till's Menu page: dishes, their prices and their add-ons in one place.

A restaurant adds a dish here without going into ERPNext's own screens, and it
is still ERPNext underneath: a dish is an Item in a section (an Item Group)
with its price in the outlet's price list, and a paid add-on is an Item too,
made here the first time a choice is given a price.

Every call that reads or changes the menu needs the "Edit the menu" permission
(permissions.py: closed until a restaurant names a role or a person, managers
always pass) at a restaurant outlet the user works at. The page is the gate,
so the writes themselves skip ERPNext's own document permissions, as the rest
of the till does. get_modifiers is the till's read of the add-ons, open to
every cashier of the outlet.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from lumen_restaurants import modifiers
from lumen_restaurants.api import permissions, restaurant

GROUP = "POS Modifier Group"
KITCHEN_STYLES = ("Normal", "Without", "Heat", "Cooking")


def _load(value, default):
    if isinstance(value, str):
        try:
            return json.loads(value or "null") or default
        except ValueError:
            return default
    return value if value is not None else default


# ---------------------------------------------------------------------------
# the till


@frappe.whitelist()
def get_modifiers(pos_profile: str):
    """The add-ons the till offers at this outlet (modifiers.till_data)."""
    restaurant._assert_outlet(pos_profile)
    return modifiers.till_data(pos_profile)


# ---------------------------------------------------------------------------
# guards and reads


def _guard(pos_profile):
    restaurant._assert_outlet(pos_profile)
    restaurant._assert_enabled(pos_profile)
    if not permissions.can_edit_menu():
        frappe.throw(_("You are not allowed to edit the menu"), frappe.PermissionError)
    return frappe.get_cached_doc("POS Profile", pos_profile)


def _listed(profile):
    """The outlet's own list of sections, or None when it lists none or lists
    the whole tree (its root, "All Item Groups"), exactly as the till reads it
    (catalog.item_groups_under, session.get_bootstrap)."""
    from lumen_restaurants.api.catalog import item_groups_under

    listed = [row.item_group for row in (profile.item_groups or []) if row.item_group]
    if not listed or item_groups_under(listed) is None:
        return None
    return listed


def _sections(profile):
    """The sections the page shows, the till's own chips: the outlet's list, or
    every section with no sub-sections. Never the Item Group of the add-on
    items. A listed parent section (Food, with Burgers and Drinks beneath it)
    is one section here too, and covers the dishes of the groups beneath it."""
    hidden = modifiers.addon_group()
    listed = _listed(profile)
    if listed is None:
        listed = frappe.get_all("Item Group", filters={"is_group": 0}, order_by="name", pluck="name")
    return [name for name in listed if name != hidden]


def _section_of(profile):
    """{item group: the shown section it falls under}, every group a shown
    section covers (itself and the groups beneath it)."""
    from lumen_restaurants.api.catalog import item_group_and_below

    sections = _sections(profile)
    if _listed(profile) is None:
        # Every leaf group is a section of its own: nothing beneath them.
        return {section: section for section in sections}
    hidden = _addon_groups()
    out = {}
    for section in sections:
        for group in item_group_and_below(section):
            if group not in hidden:
                out.setdefault(group, section)
    return out


def _addon_groups():
    """The Item Group of the add-on items and anything beneath it: never a
    dish's, wherever it sits in the tree."""
    hidden = modifiers.addon_group()
    return modifiers.covered_groups([hidden]) if hidden else set()


def _dish_filters(profile):
    """The dishes of this outlet's menu: sales items of the groups its sections
    cover, never LumenPOS's placeholder items (gift card, hold deposit)."""
    from lumen_restaurants.api.catalog import internal_item_codes

    filters = {"is_sales_item": 1, "has_variants": 0, "item_group": ["in", list(_section_of(profile)) or [""]]}
    internal = internal_item_codes()
    if internal:
        filters["name"] = ["not in", sorted(internal)]
    return filters


def _filing(profile, section_of=None):
    """The groups a dish can be filed in from this page: the groups without
    sub-groups that the shown sections cover, each with its section."""
    section_of = section_of or _section_of(profile)
    leaves = set(frappe.get_all("Item Group", filters={"name": ["in", list(section_of) or [""]], "is_group": 0}, pluck="name"))
    hidden = modifiers.addon_group()
    return sorted(
        ({"name": g, "section": s} for g, s in section_of.items() if g in leaves and g != hidden),
        key=lambda row: row["name"],
    )


def _list_prices(profile, codes):
    """The price each item carries in the outlet's own price list: what this
    page shows and changes."""
    from lumen_restaurants.price_books import get_price_map

    codes = [c for c in codes if c]
    if not codes:
        return {}
    uoms = dict(frappe.get_all("Item", filters={"name": ["in", codes]}, fields=["name", "stock_uom"], as_list=True))
    return get_price_map(codes, profile.selling_price_list, uoms)


def _groups(profile):
    groups = frappe.get_all(
        GROUP,
        fields=["name", "group_name", "multiple", "required", "max_choices", "kitchen_style", "print_default", "disabled"],
        order_by="creation asc",
    )
    if not groups:
        return []
    names = [g.name for g in groups]
    child = {"parent": ["in", names], "parenttype": GROUP}
    options = frappe.get_all(
        "POS Modifier Option", filters=child, fields=["name", "parent", "option_name", "is_default", "item"], order_by="idx asc"
    )
    prices = _list_prices(profile, [o.item for o in options])
    by_group = {}
    for o in options:
        by_group.setdefault(o.parent, []).append(
            {
                "id": o.name,
                "option_name": o.option_name,
                "is_default": cint(o.is_default),
                "item": o.item or None,
                "price": flt(prices.get(o.item)) if o.item else 0,
            }
        )
    sections, dishes = {}, {}
    for row in frappe.get_all("POS Modifier Item Group", filters=child, fields=["parent", "item_group"], order_by="idx asc"):
        sections.setdefault(row.parent, []).append(row.item_group)
    for row in frappe.get_all("POS Modifier Item", filters=child, fields=["parent", "item"], order_by="idx asc"):
        dishes.setdefault(row.parent, []).append(row.item)
    return [
        {
            "name": g.name,
            "group_name": g.group_name,
            "multiple": cint(g.multiple),
            "required": cint(g.required),
            "max_choices": cint(g.max_choices),
            "kitchen_style": g.kitchen_style or "Normal",
            "print_default": cint(g.print_default),
            "disabled": cint(g.disabled),
            "options": by_group.get(g.name, []),
            "sections": sections.get(g.name, []),
            "dishes": dishes.get(g.name, []),
        }
        for g in groups
    ]


@frappe.whitelist()
def get_menu(pos_profile: str):
    """Everything the Menu page shows: the outlet's sections, its dishes with
    their prices, and every add-on group with its choices and its ties."""
    profile = _guard(pos_profile)
    sections = _sections(profile)
    section_of = _section_of(profile)
    dishes = frappe.get_all(
        "Item",
        filters=_dish_filters(profile),
        fields=["name as item_code", "item_name", "item_group", "image", "disabled"],
        order_by="item_name asc",
        limit_page_length=0,
    )
    prices = _list_prices(profile, [d.item_code for d in dishes])
    for dish in dishes:
        dish["price"] = flt(prices.get(dish.item_code))
        dish["on_sale"] = 0 if cint(dish.pop("disabled")) else 1
        # The shown section it falls under: its own group, or the listed
        # parent section above it.
        dish["section"] = section_of.get(dish.item_group, dish.item_group)
    groups = _groups(profile)
    # Each tied section's sub-sections, so a group tied to a parent section
    # covers the dishes of its children here as it does at the till.
    covers = {}
    for g in groups:
        for section in g["sections"]:
            covers.setdefault(section, sorted(modifiers.covered_groups([section])))
    return {
        "pos_profile": profile.name,
        "price_list": profile.selling_price_list,
        "currency": frappe.db.get_value("Price List", profile.selling_price_list, "currency"),
        "sections": sections,
        "filing": _filing(profile, section_of),
        "dishes": dishes,
        "groups": groups,
        "covers": covers,
        "options": modifiers.outlet_options(profile),
        "can_change_options": bool(permissions.is_manager()),
        "outlet_lists_sections": bool(profile.item_groups),
    }


# ---------------------------------------------------------------------------
# dishes


def _default_uom():
    uom = frappe.db.get_single_value("Stock Settings", "stock_uom")
    if uom and frappe.db.exists("UOM", uom):
        return uom
    return "Nos" if frappe.db.exists("UOM", "Nos") else frappe.db.get_value("UOM", {}, "name")


def _new_code(name):
    """The item code for a new item: ERPNext's naming series when the site
    names items that way, otherwise the name itself, made unique."""
    if frappe.db.get_default("item_naming_by") == "Naming Series":
        return None
    base = name[:130].strip()
    code, n = base, 1
    while frappe.db.exists("Item", code):
        n += 1
        code = f"{base} {n}"
    return code


def _set_price(item_code, price_list, price, uom):
    """Put the item's price in the price list: the row in effect today when
    there is one, a new row otherwise. A price of 0 takes the item off the
    list (the till never sells at 0, see price_books.get_price_map)."""
    today = getdate(nowdate())
    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code, "price_list": price_list},
        fields=["name", "uom", "valid_from", "valid_upto", "customer", "supplier"],
        order_by="valid_from desc",
    )
    live = [
        r
        for r in rows
        if not r.customer
        and not r.supplier
        and (not r.uom or r.uom == uom)
        and (not r.valid_from or getdate(r.valid_from) <= today)
        and (not r.valid_upto or getdate(r.valid_upto) >= today)
    ]
    if flt(price) <= 0:
        for r in live:
            frappe.delete_doc("Item Price", r.name, ignore_permissions=True)
        return
    if live:
        doc = frappe.get_doc("Item Price", live[0].name)
        if flt(doc.price_list_rate) != flt(price):
            doc.price_list_rate = flt(price)
            doc.save(ignore_permissions=True)
        return
    frappe.get_doc(
        {
            "doctype": "Item Price",
            "item_code": item_code,
            "price_list": price_list,
            "price_list_rate": flt(price),
            "uom": uom,
        }
    ).insert(ignore_permissions=True)


def _dish(profile, item_code):
    row = frappe.db.get_value("Item", item_code, ["name as item_code", "item_name", "item_group", "image", "disabled"], as_dict=True)
    row["price"] = flt(_list_prices(profile, [item_code]).get(item_code))
    row["on_sale"] = 0 if cint(row.pop("disabled")) else 1
    row["section"] = _section_of(profile).get(row.item_group, row.item_group)
    return row


def _check_section(profile, group):
    """A dish is filed in a group without sub-groups that a section covers."""
    if not group or group not in {row["name"] for row in _filing(profile)}:
        frappe.throw(_("Pick a section of this outlet for the dish"))


def _check_dishes(profile, codes):
    from lumen_restaurants.api.catalog import internal_item_codes

    codes = set(codes or [])
    filters = _dish_filters(profile)
    filters["name"] = ["in", sorted(codes) or [""]]
    allowed = set(frappe.get_all("Item", filters=filters, pluck="name")) - internal_item_codes()
    if len(allowed) != len(codes):
        frappe.throw(_("Some of these dishes are not on this outlet's menu"))


@frappe.whitelist()
def save_dish(pos_profile: str, dish: dict | list | str):
    """Add a dish, or change one: its name, section and price, and the add-on
    groups tied to it alone (the section's own groups come with it)."""
    profile = _guard(pos_profile)
    dish = _load(dish, {})
    name = (dish.get("item_name") or "").strip()
    if not name:
        frappe.throw(_("Give the dish a name"))
    price = flt(dish.get("price"))
    if price <= 0:
        frappe.throw(_("Give {0} a price").format(name))
    section = dish.get("item_group")
    _check_section(profile, section)
    code = dish.get("item_code")
    if code:
        _check_dishes(profile, [code])
        doc = frappe.get_doc("Item", code)
        if doc.item_name != name or doc.item_group != section:
            doc.item_name = name
            doc.item_group = section
            doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": _new_code(name),
                "item_name": name,
                "item_group": section,
                "stock_uom": _default_uom(),
                "is_stock_item": 0,
                "is_sales_item": 1,
                "include_item_in_manufacturing": 0,
                "description": name,
            }
        )
        doc.insert(ignore_permissions=True)
    _set_price(doc.name, profile.selling_price_list, price, doc.stock_uom)
    if "groups" in dish:
        _tie_single(doc.name, [g for g in (dish.get("groups") or []) if frappe.db.exists(GROUP, g)])
    return _dish(profile, doc.name)


def _tie_single(item_code, wanted):
    """The groups tied to this one dish, exactly `wanted` (its section's groups
    are not touched: they come with the section)."""
    for name in frappe.get_all("POS Modifier Item", filters={"item": item_code, "parenttype": GROUP}, pluck="parent"):
        if name not in wanted:
            doc = frappe.get_doc(GROUP, name)
            doc.set("items", [row for row in doc.items if row.item != item_code])
            doc.save(ignore_permissions=True)
    for name in wanted:
        doc = frappe.get_doc(GROUP, name)
        if not any(row.item == item_code for row in doc.items):
            doc.append("items", {"item": item_code})
            doc.save(ignore_permissions=True)


@frappe.whitelist()
def set_on_sale(pos_profile: str, items: dict | list | str, on_sale: int | str | bool):
    """Take dishes off sale, or put them back. It is ERPNext's own switch on
    the item, so a dish off sale is off at every outlet."""
    profile = _guard(pos_profile)
    codes = [c for c in _load(items, []) if c]
    _check_dishes(profile, codes)
    flag = 0 if cint(on_sale) else 1
    for code in codes:
        frappe.db.set_value("Item", code, "disabled", flag)
    return {"items": codes, "on_sale": 0 if flag else 1}


@frappe.whitelist()
def new_section(pos_profile: str, name: str):
    """A new section for the menu: an Item Group next to the outlet's other
    sections, and on the outlet's own list when it keeps one, so the till shows
    it at once."""
    profile = _guard(pos_profile)
    name = (name or "").strip()
    if not name:
        frappe.throw(_("Give the section a name"))
    if frappe.db.exists("Item Group", name):
        frappe.throw(_("There is already a section called {0}").format(name))
    from frappe.utils.nestedset import get_root_of

    listed = _listed(profile) or []
    branches = [s for s in listed if frappe.db.get_value("Item Group", s, "is_group")]
    if len(branches) == 1:
        # The outlet sells a parent section (Food): the new one goes beneath
        # it, and the outlet covers it without being told.
        parent, add_to_list = branches[0], False
    else:
        parents = {frappe.db.get_value("Item Group", s, "parent_item_group") for s in _sections(profile)}
        parents.discard(None)
        parent = parents.pop() if len(parents) == 1 else get_root_of("Item Group")
        add_to_list = bool(listed)
    frappe.get_doc(
        {"doctype": "Item Group", "item_group_name": name, "parent_item_group": parent, "is_group": 0}
    ).insert(ignore_permissions=True)
    if add_to_list:
        doc = frappe.get_doc("POS Profile", profile.name)
        doc.append("item_groups", {"item_group": name})
        doc.flags.ignore_validate = True
        doc.save(ignore_permissions=True)
    return {"name": name, "sections": _sections(frappe.get_cached_doc("POS Profile", profile.name))}


# ---------------------------------------------------------------------------
# add-on groups


def _addon_item(title, uom):
    """The item a paid choice is billed as: a non-stock item in the add-ons
    section, named after the choice."""
    group = modifiers.addon_group(create=True)
    doc = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": _new_code(title),
            "item_name": title,
            "item_group": group,
            "stock_uom": uom,
            "is_stock_item": 0,
            "is_sales_item": 1,
            "include_item_in_manufacturing": 0,
            "description": title,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def save_group(pos_profile: str, group: dict | list | str):
    """Add an add-on group or change one: its name, its rules, its choices and
    their prices at this outlet. A choice given a price is billed as an item
    (made here on first use), a choice at 0 is a free instruction."""
    profile = _guard(pos_profile)
    data = _load(group, {})
    name = data.get("name")
    doc = frappe.get_doc(GROUP, name) if name else frappe.new_doc(GROUP)
    doc.group_name = (data.get("group_name") or "").strip()
    doc.multiple = 1 if cint(data.get("multiple")) else 0
    doc.required = 1 if cint(data.get("required")) else 0
    doc.max_choices = max(0, cint(data.get("max_choices")))
    style = data.get("kitchen_style") or "Normal"
    doc.kitchen_style = style if style in KITCHEN_STYLES else "Normal"
    doc.print_default = 1 if cint(data.get("print_default")) else 0
    doc.disabled = 1 if cint(data.get("disabled")) else 0
    addon_section = modifiers.addon_group()
    uom = _default_uom()
    # get(): a new group on Frappe 13 has no options list until one is set.
    rows = {row.name: row for row in (doc.get("options") or [])}
    kept = []
    for option in data.get("options") or []:
        title = (option.get("option_name") or "").strip()
        if not title:
            continue
        # An existing choice keeps its row (its id is what the till's lines
        # carry), a new one starts as a plain row.
        row = rows.get(option.get("id")) or frappe._dict(item=None)
        row.option_name = title
        row.is_default = 1 if cint(option.get("is_default")) else 0
        price = flt(option.get("price"))
        ours = bool(row.item) and bool(addon_section) and frappe.db.get_value("Item", row.item, "item_group") in modifiers.covered_groups([addon_section])
        if price > 0:
            if not row.item:
                row.item = _addon_item(title, uom)
            elif ours and frappe.db.get_value("Item", row.item, "item_name") != title:
                frappe.db.set_value("Item", row.item, {"item_name": title, "description": title})
            _set_price(row.item, profile.selling_price_list, price, frappe.db.get_value("Item", row.item, "stock_uom"))
        elif row.item:
            if ours:
                # Kept for later, and free at this outlet: no price in its list.
                _set_price(row.item, profile.selling_price_list, 0, frappe.db.get_value("Item", row.item, "stock_uom"))
            else:
                row.item = None
        kept.append(row)
    doc.set("options", [])
    for idx, row in enumerate(kept, 1):
        if isinstance(row, frappe._dict):
            doc.append("options", {"option_name": row.option_name, "is_default": row.is_default, "item": row.item, "idx": idx})
        else:
            row.idx = idx
            doc.append("options", row)
    doc.save(ignore_permissions=True)
    return next(g for g in _groups(profile) if g["name"] == doc.name)


@frappe.whitelist()
def delete_group(pos_profile: str, name: str):
    """Remove an add-on group. Sales, orders and tickets keep the choices they
    were made with (they carry the words, not a link)."""
    _guard(pos_profile)
    frappe.delete_doc(GROUP, name, ignore_permissions=True)
    return {"deleted": name}


def _dishes_under(section):
    """Every dish filed in a section or in the groups beneath it, never an
    add-on choice's item nor LumenPOS's placeholder items."""
    from lumen_restaurants.api.catalog import internal_item_codes

    groups = (modifiers.covered_groups([section]) or {section}) - _addon_groups()
    names = frappe.get_all(
        "Item",
        filters={"item_group": ["in", sorted(groups) or [""]], "is_sales_item": 1, "has_variants": 0},
        pluck="name",
    )
    internal = internal_item_codes()
    return [name for name in names if name not in internal]


def _promote(doc):
    """A section whose every dish is tied one by one becomes a whole-section
    tie, which also covers the dishes added to it later. And a whole section
    keeps no single ties of its own dishes."""
    singles = {row.item for row in doc.items}
    covered = modifiers.covered_groups([row.item_group for row in doc.item_groups])
    by_section = {}
    for code in singles:
        by_section.setdefault(frappe.db.get_value("Item", code, "item_group"), set()).add(code)
    for section, codes in by_section.items():
        if section in covered:
            continue
        everything = set(_dishes_under(section))
        if everything and everything <= codes:
            doc.append("item_groups", {"item_group": section})


@frappe.whitelist()
def tie_group(pos_profile: str, name: str, sections: dict | list | str | None = None, items: dict | list | str | None = None):
    """Say exactly which sections and which single dishes the group shows with."""
    profile = _guard(pos_profile)
    sections = [s for s in _load(sections, []) if s]
    items = [c for c in _load(items, []) if c]
    allowed = set(_sections(profile))
    unknown = [s for s in sections if s not in allowed and not frappe.db.exists("Item Group", s)]
    if unknown:
        frappe.throw(_("Unknown section: {0}").format(", ".join(unknown)))
    _check_dishes(profile, items)
    doc = frappe.get_doc(GROUP, name)
    doc.set("item_groups", [{"item_group": s} for s in dict.fromkeys(sections)])
    doc.set("items", [{"item": c} for c in dict.fromkeys(items)])
    _promote(doc)
    doc.save(ignore_permissions=True)
    return next(g for g in _groups(profile) if g["name"] == doc.name)


@frappe.whitelist()
def bulk_tie(pos_profile: str, name: str, items: dict | list | str, tie: int | str | bool = 1):
    """Tie the group to the dishes picked on the Dishes tab, or untie it. A dish
    untied from a whole section leaves the rest of its section tied one by one."""
    profile = _guard(pos_profile)
    codes = [c for c in _load(items, []) if c]
    _check_dishes(profile, codes)
    doc = frappe.get_doc(GROUP, name)
    if cint(tie):
        have = {row.item for row in doc.items}
        for code in codes:
            if code not in have:
                doc.append("items", {"item": code})
    else:
        drop = set(codes)
        for code in codes:
            group = frappe.db.get_value("Item", code, "item_group")
            # Every tied section that covers this dish (its own, or one above
            # it) gives way to its other dishes, tied one by one.
            for row in list(doc.item_groups):
                if group not in modifiers.covered_groups([row.item_group]):
                    continue
                doc.set("item_groups", [r for r in doc.item_groups if r.item_group != row.item_group])
                have = {r.item for r in doc.items}
                for other in _dishes_under(row.item_group):
                    if other not in drop and other not in have:
                        doc.append("items", {"item": other})
        doc.set("items", [row for row in doc.items if row.item not in drop])
    _promote(doc)
    doc.save(ignore_permissions=True)
    return next(g for g in _groups(profile) if g["name"] == doc.name)


# ---------------------------------------------------------------------------
# the outlet's switches (Settings, Restaurant)


@frappe.whitelist()
def get_outlet_options(pos_profile: str):
    restaurant._assert_outlet(pos_profile)
    return modifiers.outlet_options(pos_profile)


@frappe.whitelist()
def save_outlet_options(pos_profile: str, options: dict | list | str):
    """The three add-on switches of an outlet. A manager's call."""
    restaurant._assert_outlet(pos_profile)
    if not permissions.is_manager():
        frappe.throw(_("Only a manager can change this"), frappe.PermissionError)
    options = _load(options, {})
    doc = frappe.get_doc("POS Profile", pos_profile)
    for key, field in (("enabled", "lr_addons"), ("open_on_tap", "lr_addons_open_on_tap"), ("free_on_receipt", "lr_addons_free_on_receipt")):
        if key in options and doc.meta.has_field(field):
            doc.set(field, 1 if cint(options[key]) else 0)
    # Only these switches change: ERPNext's own checks of the profile are for
    # the fields its form edits.
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)
    return modifiers.outlet_options(doc)
