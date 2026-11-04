# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Add-ons on dishes: the guest's choices (no pickles, medium heat) and the
paid extras (extra mayo, two riyals).

A POS Modifier Group holds the choices and says which dishes it shows with:
whole sections (Item Groups, their sub-sections and the dishes added to them
later) and single dishes. At the till a choice is one of two things:

- free (no item, or an item with no price at the outlet): an instruction for
  the kitchen, carried on the dish's own line and printed under it.
- paid (its item has a price in the outlet's price list): a line of its own
  right under the dish, priced by the server like any other line, so VAT, the
  reports and the stock (when the item keeps stock) come out right.

The till tags the lines it sends: a dish carries lr_line (its id), lr_mods
(the choices) and lr_note, a paid add-on carries lr_addon_of (its dish's id).
apply_to_invoice turns that into the invoice's own fields. Everything here is
ours, next to LumenPOS's files: sales.py only calls apply_to_invoice.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, escape_html, flt

from lumen_restaurants.lumen_restaurants.doctype.pos_modifier_group.pos_modifier_group import (
    covered_groups,
)

# The group's kitchen look, as the till and the kitchen screen name it.
STYLES = {"Without": "no", "Heat": "heat", "Cooking": "cook"}

# The Item Group the Menu page files the items of paid choices under, and the
# name it is given in each language when it has to be made.
ADDON_GROUPS = ("Add-ons", "الإضافات")

MAX_CHOICES_PER_LINE = 40


def _invoice_item_fields(after):
    return [
        dict(
            fieldname="lr_modifiers",
            label="Add-ons (till)",
            fieldtype="Small Text",
            insert_after=after,
            read_only=1,
            hidden=1,
            print_hide=1,
            description="The guest's choices for this dish and its kitchen note, as the till sent them.",
        ),
        dict(
            fieldname="lr_addon_of",
            label="Add-on of line",
            fieldtype="Int",
            insert_after="lr_modifiers",
            read_only=1,
            hidden=1,
            print_hide=1,
            description="A paid add-on: the line number of the dish it belongs to.",
        ),
    ]


CUSTOM_FIELDS = {
    "POS Profile": [
        dict(
            fieldname="lr_addons",
            label="Add-ons on dishes",
            fieldtype="Check",
            default="1",
            insert_after="lumenpos_restaurant_mode",
            depends_on="lumenpos_restaurant_mode",
            description="The choices a guest makes about a dish (no pickles, medium heat, extra "
            "mayo), set up on the till's Menu page. Off: a line takes a free note only.",
        ),
        dict(
            fieldname="lr_addons_open_on_tap",
            label="Open the add-ons when a dish is tapped",
            fieldtype="Check",
            default="1",
            insert_after="lr_addons",
            depends_on="eval:doc.lumenpos_restaurant_mode && doc.lr_addons",
            description="Off: a tap adds the dish straight away and the cashier taps its line to "
            "choose. A dish with a required group always opens its window.",
        ),
        dict(
            fieldname="lr_addons_free_on_receipt",
            label="Print the free choices on the customer receipt",
            fieldtype="Check",
            default="1",
            insert_after="lr_addons_open_on_tap",
            depends_on="eval:doc.lumenpos_restaurant_mode && doc.lr_addons",
            description="Like no pickles. Paid add-ons always print, with their price.",
        ),
    ],
    "POS Invoice Item": _invoice_item_fields("lumenpos_return_group"),
    "Sales Invoice Item": _invoice_item_fields("lumenpos_return_group"),
}


def ensure_setup():
    """after_install and after_migrate: our fields, next to LumenPOS's. A commit
    first, Frappe refuses the table change after a write in the same
    transaction."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    # Before the table change: MariaDB commits by itself on DDL, and Frappe
    # refuses DDL after a write in the same transaction.
    frappe.db.commit()  # nosemgrep
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)


def _flag(value, default=1):
    return default if value is None else cint(value)


def outlet_options(profile):
    """The outlet's add-on switches. A site that has not migrated yet has no
    such fields, and reads the defaults."""
    if isinstance(profile, str):
        profile = frappe.get_cached_doc("POS Profile", profile)
    restaurant = cint(profile.get("lumenpos_restaurant_mode"))
    return {
        "enabled": bool(restaurant and _flag(profile.get("lr_addons"))),
        "open_on_tap": bool(_flag(profile.get("lr_addons_open_on_tap"))),
        "free_on_receipt": bool(_flag(profile.get("lr_addons_free_on_receipt"))),
    }


def addon_group(create=False):
    """The Item Group of the items made for paid choices, made on first use
    under the root of the tree, in the language of whoever makes it."""
    for name in ADDON_GROUPS:
        if frappe.db.exists("Item Group", name):
            return name
    if not create:
        return None
    from frappe.utils.nestedset import get_root_of

    name = ADDON_GROUPS[1] if (frappe.local.lang or "").startswith("ar") else ADDON_GROUPS[0]
    frappe.get_doc(
        {
            "doctype": "Item Group",
            "item_group_name": name,
            "parent_item_group": get_root_of("Item Group"),
            "is_group": 0,
        }
    ).insert(ignore_permissions=True)
    return name


def option_prices(profile, item_codes):
    """What each paid choice sells for at this outlet: the same price the sale
    posts (lumen_restaurants.price_books)."""
    from lumen_restaurants.price_books import effective_prices

    codes = sorted({c for c in item_codes if c})
    if not codes:
        return {}
    uoms = dict(frappe.get_all("Item", filters={"name": ["in", codes]}, fields=["name", "stock_uom"], as_list=True))
    return effective_prices(profile, codes, None, None, uoms)


def till_data(profile):
    """Everything the till needs to offer the add-ons at this outlet: the
    groups in the order they were made, each with its choices and their prices,
    and which groups show with which dish and which section."""
    if isinstance(profile, str):
        profile = frappe.get_cached_doc("POS Profile", profile)
    out = dict(outlet_options(profile), groups=[], by_item={}, by_section={}, hidden_group=addon_group())
    if not out["enabled"]:
        return out
    groups = frappe.get_all(
        "POS Modifier Group",
        filters={"disabled": 0},
        fields=["name", "group_name", "multiple", "required", "max_choices", "kitchen_style", "print_default"],
        order_by="creation asc",
    )
    if not groups:
        return out
    names = [g.name for g in groups]
    child = {"parent": ["in", names], "parenttype": "POS Modifier Group"}
    options = frappe.get_all(
        "POS Modifier Option",
        filters=child,
        fields=["name", "parent", "option_name", "is_default", "item", "idx"],
        order_by="idx asc",
    )
    prices = option_prices(profile, [o.item for o in options])
    choices = {}
    for o in options:
        choices.setdefault(o.parent, []).append(
            {
                "id": o.name,
                "title": o.option_name,
                "default": cint(o.is_default),
                "item_code": o.item or None,
                "price": flt(prices.get(o.item)) if o.item else 0,
            }
        )
    for g in groups:
        out["groups"].append(
            {
                "name": g.name,
                "title": g.group_name,
                "multiple": cint(g.multiple),
                "required": cint(g.required),
                "max": cint(g.max_choices),
                "style": STYLES.get(g.kitchen_style or "", ""),
                "print_default": cint(g.print_default),
                "options": choices.get(g.name, []),
            }
        )
    order = {name: i for i, name in enumerate(names)}
    for row in frappe.get_all("POS Modifier Item", filters=child, fields=["parent", "item"]):
        out["by_item"].setdefault(row.item, set()).add(row.parent)
    for row in frappe.get_all("POS Modifier Item Group", filters=child, fields=["parent", "item_group"]):
        for section in covered_groups([row.item_group]):
            out["by_section"].setdefault(section, set()).add(row.parent)
    for mapping in (out["by_item"], out["by_section"]):
        for key in list(mapping):
            mapping[key] = sorted(mapping[key], key=order.get)
    return out


def groups_for_item(item_code, item_group=None):
    """The enabled groups a dish shows with, in their order."""
    item_group = item_group or frappe.db.get_value("Item", item_code, "item_group")
    names = set(
        frappe.get_all("POS Modifier Item", filters={"item": item_code, "parenttype": "POS Modifier Group"}, pluck="parent")
    )
    for row in frappe.get_all(
        "POS Modifier Item Group", filters={"parenttype": "POS Modifier Group"}, fields=["parent", "item_group"]
    ):
        if item_group in covered_groups([row.item_group]):
            names.add(row.parent)
    if not names:
        return []
    return frappe.get_all(
        "POS Modifier Group", filters={"name": ["in", list(names)], "disabled": 0}, pluck="name", order_by="creation asc"
    )


# ---------------------------------------------------------------------------
# the sale


def clean_choices(raw):
    """The choices the kitchen and the receipt show for a dish, from what the
    till sent: a title, the group's look, and whether it is a paid add-on. Only
    ever text for people to read, the money is on the add-on lines."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = []
    out = []
    for c in (raw or [])[:MAX_CHOICES_PER_LINE]:
        if not isinstance(c, dict) or not cint(c.get("k", 1)):
            continue
        title = str(c.get("t") or "").strip()[:140]
        if not title:
            continue
        style = c.get("s") if c.get("s") in ("no", "heat", "cook") else ""
        paid = cint(c.get("p")) or (c.get("i") and flt(c.get("pr")) > 0)
        out.append({"t": title, "s": style, "p": 1 if paid else 0})
    return out


def choices_text(choices, paid=True):
    sep = "، " if (frappe.local.lang or "").startswith("ar") else ", "
    return sep.join(c["t"] for c in choices if paid or not c.get("p"))


class _AddonCheck:
    """A paid add-on line must be one of its dish's own choices: an option of a
    group that shows with the dish, billed as that very item."""

    def __init__(self):
        self._groups = {}

    def _group(self, name):
        if name not in self._groups:
            self._groups[name] = (
                frappe.get_cached_doc("POS Modifier Group", name)
                if name and frappe.db.exists("POS Modifier Group", name)
                else None
            )
        return self._groups[name]

    def _shows_with(self, group, item_code):
        if any(row.item == item_code for row in group.items):
            return True
        item_group = frappe.db.get_value("Item", item_code, "item_group")
        return item_group in covered_groups([row.item_group for row in group.item_groups])

    def check(self, dish, addon, dish_name):
        code = addon.get("item_code")
        for c in dish.get("lr_mods") or []:
            if not isinstance(c, dict) or c.get("i") != code:
                continue
            group = self._group(c.get("g"))
            if not group or cint(group.disabled) or not self._shows_with(group, dish.get("item_code")):
                continue
            if any(o.name == c.get("o") and o.item == code for o in group.options):
                return
        frappe.throw(
            _("The add-ons of {0} have changed. Open the dish again and pick them.").format(dish_name)
        )


def apply_to_invoice(invoice, payload_items):
    """Called by the sale (api/sales.py) once the lines are on the invoice, in
    the till's order. Writes each dish's choices and note, ties each paid add-on
    to its dish (its line number), and refuses an add-on that is not one of its
    dish's own choices."""
    rows = invoice.get("items") or []
    if not any(isinstance(p, dict) and (p.get("lr_line") or p.get("lr_addon_of")) for p in payload_items):
        return
    position = {}
    for i, p in enumerate(payload_items):
        if p.get("lr_line"):
            position[str(p["lr_line"])] = i
    checker = _AddonCheck()
    for i, p in enumerate(payload_items[: len(rows)]):
        row = rows[i]
        parent = p.get("lr_addon_of")
        if parent:
            j = position.get(str(parent))
            if j is None or j >= i or payload_items[j].get("lr_addon_of"):
                frappe.throw(_("{0} is an add-on without its dish").format(row.item_name or row.item_code))
            dish_row, dish = rows[j], payload_items[j]
            if abs(flt(p.get("qty")) - flt(dish.get("qty"))) > 1e-9:
                frappe.throw(
                    _("{0} must have the same quantity as {1}").format(row.item_name, dish_row.item_name)
                )
            checker.check(dish, p, dish_row.item_name or dish_row.item_code)
            # No return group on purpose: a return counts items by code, so
            # two burgers, one with extra cheese and one without, would make
            # the plain one impossible to return on its own.
            row.lr_addon_of = cint(dish_row.idx) or j + 1
        elif p.get("lr_line"):
            choices = clean_choices(p.get("lr_mods"))
            note = str(p.get("lr_note") or "").strip()[:400]
            if not (choices or note):
                continue
            row.lr_modifiers = json.dumps({"c": choices, "n": note}, ensure_ascii=False)
            # ERPNext prints the description under the item: the free choices
            # go there too, so its own print formats show them.
            free = choices_text(choices, paid=False)
            if free:
                row.description = "{0}<br>{1}".format(row.description or escape_html(row.item_name or ""), escape_html(free))


def receipt_item(row, pos_profile=None):
    """What the receipt adds to a sold line (api/sales.py get_receipt): the line
    of the dish a paid add-on belongs to, and a dish's free choices when the
    outlet prints them. Nothing for a line that has neither."""
    out = {}
    if cint(row.get("lr_addon_of")):
        out["addon_of"] = cint(row.get("lr_addon_of"))
    if row.get("lr_modifiers"):
        try:
            options = outlet_options(pos_profile) if pos_profile else {"free_on_receipt": True}
        except frappe.DoesNotExistError:
            options = {"free_on_receipt": True}
        if options["free_on_receipt"]:
            free = [c for c in row_data(row)["c"] if not c["p"]]
            if free:
                out["choices"] = free
                out["choices_text"] = choices_text(free)
    return out


def row_data(row):
    """A saved line's choices and note (the inverse of apply_to_invoice)."""
    raw = row.get("lr_modifiers") if hasattr(row, "get") else None
    if not raw:
        return {"c": [], "n": ""}
    try:
        data = json.loads(raw)
    except ValueError:
        return {"c": [], "n": ""}
    return {"c": clean_choices(data.get("c")), "n": str(data.get("n") or "")}
