# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""A group of choices a guest makes about a dish: Heat level, Without, Sauces.

The name is a stable MOD-#### so the group can be renamed without breaking the
orders and tickets that carry its choices. A choice with a price is billed as
its own item (see POS Modifier Option), everything else is an instruction for
the kitchen. A group shows with whole sections (Item Groups, their
sub-sections and any dish added to them later) and with single dishes.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class POSModifierGroup(Document):
    def validate(self):
        self.group_name = (self.group_name or "").strip()
        if not self.group_name:
            frappe.throw(_("Give the group a name"))
        seen = set()
        for row in self.options:
            row.option_name = (row.option_name or "").strip()
            key = row.option_name.casefold()
            if not key:
                frappe.throw(_("Every choice in {0} needs a name").format(self.group_name))
            if key in seen:
                frappe.throw(_("{0} is in {1} twice").format(row.option_name, self.group_name))
            seen.add(key)
        if not self.options:
            frappe.throw(_("Add at least one choice to {0}").format(self.group_name))
        self.max_choices = max(0, cint(self.max_choices)) if cint(self.multiple) else 0
        if not cint(self.multiple):
            defaults = [row for row in self.options if cint(row.is_default)]
            for row in defaults[1:]:
                row.is_default = 0
        self._tidy_links()

    def _tidy_links(self):
        """One row per section and per dish, and no single row for a dish its
        whole section already covers."""
        sections, rows = set(), []
        for row in self.item_groups:
            if row.item_group and row.item_group not in sections:
                sections.add(row.item_group)
                rows.append(row)
        self.set("item_groups", rows)
        covered = covered_groups(sections)
        dishes, rows = set(), []
        for row in self.items:
            if not row.item or row.item in dishes:
                continue
            if frappe.db.get_value("Item", row.item, "item_group") in covered:
                continue
            dishes.add(row.item)
            rows.append(row)
        self.set("items", rows)


def covered_groups(sections):
    """The sections themselves and every sub-section under them (Item Group is
    a tree, as ERPNext keeps it)."""
    out = set()
    for name in sections or ():
        bounds = frappe.db.get_value("Item Group", name, ["lft", "rgt"], as_dict=True)
        if not bounds:
            continue
        out.update(
            frappe.get_all(
                "Item Group",
                filters={"lft": [">=", bounds.lft], "rgt": ["<=", bounds.rgt]},
                pluck="name",
            )
        )
    return out
