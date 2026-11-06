# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""The kitchen and bar side of the counter.

A ticket is what the kitchen or bar sees: the short daily number (or the table), the
items with the guest's notes, and how long it has been waiting. It moves
through New, Preparing, Ready, Done, and each step stamps its time, so the
screen can colour a ticket that is taking too long and the shop can see the
real average.

Tickets are born in two ways. A paid takeaway or delivery sale makes tickets the
moment the money is in (sales.submit_sale calls after_sale here, in the same
transaction: no payment, no ticket, no number burned). A table sends tickets every
time the waiter presses "send order", routing food to the kitchen and beverages to the bar.
"""

from __future__ import annotations

import json
import re

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, nowdate

from lumen_restaurants.api import restaurant

TICKET = "POS Kitchen Ticket"

# The whole flow, so a wrong jump (Done back to New) is refused loudly.
FLOW = {
    "New": {"Preparing", "Ready", "Cancelled", "Done"},
    "Preparing": {"Ready", "Cancelled", "New", "Done"},
    "Ready": {"Done", "Preparing"},
    "Done": set(),
    "Cancelled": set(),
}

BAR_REGEX = re.compile(
    r'\b('
    r'bar|bars|beverage|beverages|drink|drinks|drinking|cocktail|cocktails|'
    r'beer|beers|wine|wines|liquor|spirits|alcohol|alcoholic|'
    r'mocktail|mocktails|soft\s*drink|soft\s*drinks|cold\s*drink|cold\s*drinks|'
    r'juice|juices|coffee|coffees|tea|teas|shake|shakes|milkshake|milkshakes|'
    r'smoothie|smoothies|water|waters|soda|sodas|gin|rum|vodka|whisky|whiskey|tequila|champagne'
    r')\b',
    re.IGNORECASE
)


def is_bar_name(name: str | None) -> bool:
    if not name:
        return False
    return bool(BAR_REGEX.search(str(name)))


def _ensure_schema():
    """Ensure custom columns and DocType Custom Fields exist without requiring manual migration."""
    try:
        from lumen_restaurants.install import make_custom_fields
        make_custom_fields()
        frappe.clear_cache(doctype="Item Group")
        frappe.clear_cache(doctype="Item")
        frappe.clear_cache(doctype="POS Profile")
        frappe.clear_cache(doctype=TICKET)
    except Exception:
        pass

    try:
        if not frappe.db.has_column(TICKET, "station"):
            frappe.db.sql("ALTER TABLE `tabPOS Kitchen Ticket` ADD COLUMN `station` varchar(140) DEFAULT 'Kitchen'")
        frappe.db.sql("UPDATE `tabPOS Kitchen Ticket` SET `station` = 'Kitchen' WHERE `station` IS NULL OR `station` = ''")
        if not frappe.db.has_column(TICKET, "is_depleted"):
            frappe.db.sql("ALTER TABLE `tabPOS Kitchen Ticket` ADD COLUMN `is_depleted` int(1) NOT NULL DEFAULT 0")
        frappe.db.commit()
    except Exception:
        pass
    try:
        if not frappe.db.has_column("POS Kitchen Ticket Item", "item_code"):
            frappe.db.sql("ALTER TABLE `tabPOS Kitchen Ticket Item` ADD COLUMN `item_code` varchar(140) DEFAULT NULL")
            frappe.db.commit()
    except Exception:
        pass
    try:
        if not frappe.db.has_column("Item Group", "lumenpos_station"):
            frappe.db.sql("ALTER TABLE `tabItem Group` ADD COLUMN `lumenpos_station` varchar(140) DEFAULT NULL")
            frappe.db.commit()
    except Exception:
        pass
    try:
        if not frappe.db.has_column("Item", "lumenpos_station"):
            frappe.db.sql("ALTER TABLE `tabItem` ADD COLUMN `lumenpos_station` varchar(140) DEFAULT NULL")
            frappe.db.commit()
    except Exception:
        pass

    try:
        if not frappe.db.has_column("Contact", "is_billing_contact"):
            frappe.db.sql("ALTER TABLE `tabContact` ADD COLUMN `is_billing_contact` int(1) NOT NULL DEFAULT 0")
            frappe.db.commit()
    except Exception:
        pass
    try:
        if not frappe.db.has_column("Address", "is_your_company_address"):
            frappe.db.sql("ALTER TABLE `tabAddress` ADD COLUMN `is_your_company_address` int(1) NOT NULL DEFAULT 0")
            frappe.db.commit()
    except Exception:
        pass

    # Clear legacy 'Kitchen' default from items so they don't block category or keyword routing
    try:
        frappe.db.sql("UPDATE `tabItem` SET `lumenpos_station` = NULL WHERE `lumenpos_station` = 'Kitchen'")
        frappe.db.commit()
    except Exception:
        pass

    # Auto-tag any existing Bar/Beverage Item Groups to 'Bar' if not already explicitly set
    try:
        for kw in ("bar", "beverage", "drink", "cocktail", "beer", "wine", "liquor", "juice", "coffee", "tea", "shake", "smoothie", "soda", "water"):
            frappe.db.sql("UPDATE `tabItem Group` SET `lumenpos_station` = 'Bar' WHERE lower(name) LIKE %s", f"%{kw}%")
            frappe.db.sql("UPDATE `tabItem` SET `lumenpos_station` = 'Bar' WHERE lower(item_name) LIKE %s OR lower(name) LIKE %s", (f"%{kw}%", f"%{kw}%"))
        frappe.db.commit()
    except Exception:
        pass


def get_item_station(item_code: str | None = None, item_group: str | None = None, item_name: str | None = None) -> str:
    """Determine whether an item goes to the Kitchen or the Bar.
    1. Checks Item.lumenpos_station if explicitly set to 'Bar'.
    2. Checks Item Group.lumenpos_station (or ancestor tree) if set to 'Bar'.
    3. Checks Item Group (or ancestor) name against bar/beverage keywords.
    4. Checks Item name or item_code against bar/beverage keywords.
    5. Checks Item.lumenpos_station if explicitly set to 'Kitchen'.
    6. Defaults to 'Kitchen'.
    """
    _ensure_schema()
    if not item_code and not item_group and not item_name:
        return "Kitchen"

    # 1. Item-level explicit Bar override
    if item_code:
        try:
            if frappe.db.has_column("Item", "lumenpos_station"):
                item_station = frappe.db.get_value("Item", item_code, "lumenpos_station")
                if item_station == "Bar":
                    return "Bar"
        except Exception:
            pass

    # 1b. Registered in Bar Recipe or Bar Tap Line
    if item_code or item_name:
        try:
            is_bar_entity = frappe.db.sql("""
                SELECT 1 FROM `tabPOS Bar Recipe` WHERE (item_code = %s OR recipe_name = %s) AND is_active = 1
                UNION
                SELECT 1 FROM `tabPOS Bar Tap` WHERE (keg_item = %s OR item_name = %s)
                LIMIT 1
            """, (item_code or "", item_name or "", item_code or "", item_name or ""))
            if is_bar_entity:
                return "Bar"
        except Exception:
            pass

    # Find item_group and item_name if not provided
    if not item_group and item_code:
        try:
            item_group = frappe.db.get_value("Item", item_code, "item_group")
        except Exception:
            item_group = None

    if not item_name and item_code:
        try:
            item_name = frappe.db.get_value("Item", item_code, "item_name")
        except Exception:
            item_name = None

    if item_group:
        try:
            # 2. Check if this specific Item Group is marked Bar
            if frappe.db.has_column("Item Group", "lumenpos_station"):
                group_station = frappe.db.get_value("Item Group", item_group, "lumenpos_station")
                if group_station == "Bar":
                    return "Bar"

            # 3. Check ancestor groups in the tree
            node = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
            if node:
                ancestor_bar = frappe.get_all(
                    "Item Group",
                    filters={"lft": ["<", node.lft], "rgt": [">", node.rgt], "lumenpos_station": "Bar"},
                    limit=1,
                )
                if ancestor_bar:
                    return "Bar"

            # 4. Keyword check on category name and ancestor category names
            if is_bar_name(item_group):
                return "Bar"

            if node:
                ancestors = frappe.get_all(
                    "Item Group",
                    filters={"lft": ["<", node.lft], "rgt": [">", node.rgt]},
                    pluck="name",
                )
                for anc in ancestors:
                    if is_bar_name(anc):
                        return "Bar"
        except Exception:
            pass

    # 5. Keyword check on item_name or item_code
    if is_bar_name(item_name) or is_bar_name(item_code):
        return "Bar"

    # 6. Item-level explicit Kitchen override
    if item_code:
        try:
            if frappe.db.has_column("Item", "lumenpos_station"):
                item_station = frappe.db.get_value("Item", item_code, "lumenpos_station")
                if item_station == "Kitchen":
                    return "Kitchen"
        except Exception:
            pass

    return "Kitchen"


def _clean_items(items):
    from lumen_restaurants import modifiers

    rows = []
    for row in items or []:
        qty = flt(row.get("qty"))
        name = (row.get("item_name") or "").strip()
        if not name or qty <= 0:
            continue
        choices = modifiers.clean_choices(row.get("modifiers"))
        rows.append(
            {
                "item_name": name,
                "qty": qty,
                "note": (row.get("note") or "").strip()[:400] or None,
                "item_code": row.get("item_code"),
                # The guest's choices, shown under the dish (modifiers.py).
                "modifiers": json.dumps(choices, ensure_ascii=False) if choices else None,
            }
        )
    return rows


def _choices(raw):
    """A ticket line's choices, as the screen and the slip show them."""
    from lumen_restaurants import modifiers

    return modifiers.clean_choices(raw) if raw else []


def _make_ticket(profile_name, order_type, items, order_no=None, table_label=None,
                 source_order=None, invoice=None, note=None, station="Kitchen"):
    _ensure_schema()
    rows = _clean_items(items)
    if not rows:
        return None
    station = "Bar" if station == "Bar" else "Kitchen"
    naming_series = "BOT-.YYYY.-" if station == "Bar" else "KOT-.YYYY.-"
    ticket_dict = {
        "doctype": TICKET,
        "naming_series": naming_series,
        "pos_profile": profile_name,
        "station": station,
        "order_type": order_type or "Takeaway",
        "order_no": str(order_no) if order_no else None,
        "table_label": table_label,
        "source_order": source_order,
        "invoice": invoice,
        "status": "New",
        "note": (note or "").strip() or None,
        "items": rows,
    }
    doc = frappe.get_doc(ticket_dict)
    doc.insert(ignore_permissions=True)
    frappe.db.sql("UPDATE `tabPOS Kitchen Ticket` SET `station` = %s WHERE `name` = %s", (station, doc.name))
    doc.station = station
    from lumen_restaurants.api.notifications import notify_new_ticket
    notify_new_ticket(doc)
    frappe.db.commit()
    return doc


def _working_day(invoice):
    """The day the shift this sale is posted on opened."""
    from lumen_restaurants.api import sales

    session = sales._get_custom(invoice, ("lumenpos_session",))
    opened = session and frappe.db.get_value("POS Register Session", session, "opened_at")
    return getdate(opened) if opened else None


def after_sale(invoice, profile, meta):
    """A restaurant sale just posted: hand out the day's number and open the
    kitchen and bar tickets, inside the sale's own transaction."""
    from lumen_restaurants import modifiers
    from lumen_restaurants.lumen_restaurants.doctype.pos_daily_counter.pos_daily_counter import next_order_no

    order_type = meta.get("order_type") or "Takeaway"
    notes = {}
    for line in meta.get("notes") or []:
        if line.get("item_code") and (line.get("note") or "").strip():
            notes[line["item_code"]] = line["note"].strip()

    order_no = next_order_no(profile.name, day=_working_day(invoice))
    items = []
    for row in invoice.items:
        if row.get("lr_addon_of"):
            continue
        data = modifiers.row_data(row)
        items.append(
            {
                "item_name": row.item_name,
                "qty": row.qty,
                "item_code": row.item_code,
                "item_group": row.get("item_group"),
                "note": data["n"] if row.get("lr_modifiers") else notes.get(row.item_code),
                "modifiers": data["c"],
            }
        )

    kitchen_items = []
    bar_items = []
    for it in items:
        st = get_item_station(
            item_code=it.get("item_code"),
            item_group=it.get("item_group"),
            item_name=it.get("item_name")
        )
        if st == "Bar":
            bar_items.append(it)
        else:
            kitchen_items.append(it)

    kt = _make_ticket(
        profile.name, order_type, kitchen_items, order_no=order_no, invoice=invoice.name, station="Kitchen"
    ) if kitchen_items else None

    bt = _make_ticket(
        profile.name, order_type, bar_items, order_no=order_no, invoice=invoice.name, station="Bar"
    ) if bar_items else None

    from lumen_restaurants.api import sales

    sales._set_custom(invoice, ("lumenpos_order_no",), str(order_no))
    frappe.db.set_value(
        invoice.doctype, invoice.name, "lumenpos_order_no", str(order_no),
        update_modified=False,
    )

    if kt:
        try:
            from lumen_restaurants.api import printing
            printing.auto_print_kitchen(kt)
        except Exception:
            frappe.log_error(title="LumenPOS kitchen print failed")

    if bt:
        try:
            from lumen_restaurants.api import printing
            printing.auto_print_bar(bt)
        except Exception:
            frappe.log_error(title="LumenPOS bar print failed")

    frappe.db.commit()

    primary_ticket = kt.name if kt else (bt.name if bt else None)
    return {
        "order_no": order_no,
        "ticket": primary_ticket,
        "kitchen_ticket": kt.name if kt else None,
        "bar_ticket": bt.name if bt else None,
    }


@frappe.whitelist()
def send_to_kitchen(order: str, items: dict | list | str, note: str | None = None):
    """A table sends what was just added: the waiter's "Send Order"."""
    if isinstance(items, str):
        items = json.loads(items or "[]")
    doc = frappe.get_doc("POS Restaurant Order", order)
    doc.check_permission("write")
    restaurant._assert_outlet(doc.pos_profile)
    if doc.status != "Open":
        frappe.throw(_("This order is {0}").format(_(doc.status)))

    kitchen_items = []
    bar_items = []
    for item in items:
        st = get_item_station(
            item_code=item.get("item_code"),
            item_group=item.get("item_group"),
            item_name=item.get("item_name")
        )
        if st == "Bar":
            bar_items.append(item)
        else:
            kitchen_items.append(item)

    created_tickets = []
    kt = None
    bt = None

    if kitchen_items:
        kt = _make_ticket(
            doc.pos_profile,
            doc.order_type or "Dine in",
            kitchen_items,
            table_label=doc.table_label or _("Takeaway"),
            source_order=doc.name,
            note=note,
            station="Kitchen",
        )
        if kt:
            created_tickets.append(kt)
            try:
                from lumen_restaurants.api import printing
                printing.auto_print_kitchen(kt)
            except Exception:
                frappe.log_error(title="LumenPOS kitchen print failed")

    if bar_items:
        bt = _make_ticket(
            doc.pos_profile,
            doc.order_type or "Dine in",
            bar_items,
            table_label=doc.table_label or _("Takeaway"),
            source_order=doc.name,
            note=note,
            station="Bar",
        )
        if bt:
            created_tickets.append(bt)
            try:
                from lumen_restaurants.api import printing
                printing.auto_print_bar(bt)
            except Exception:
                frappe.log_error(title="LumenPOS bar print failed")

    if not created_tickets:
        frappe.throw(_("Nothing new to send: everything on this order has already been sent"))

    frappe.db.commit()

    return {
        "ticket": created_tickets[0].name,
        "tickets": [t.name for t in created_tickets],
        "items": sum(len(t.items) for t in created_tickets),
        "kitchen_items": len(kitchen_items),
        "bar_items": len(bar_items),
    }


@frappe.whitelist()
def send_order(order: str, items: dict | list | str, note: str | None = None):
    """Alias for send_to_kitchen, reflecting unified kitchen and bar dispatch."""
    return send_to_kitchen(order=order, items=items, note=note)


@frappe.whitelist()
def board(pos_profile: str, station: str = "Kitchen"):
    """Everything the kitchen or bar screen shows, one request every few seconds."""
    restaurant._assert_outlet(pos_profile)
    _ensure_schema()
    station = "Bar" if station == "Bar" else "Kitchen"

    if station == "Bar":
        tickets = frappe.db.sql("""
            select name, order_type, order_no, table_label, status, station, created_at, started_at, ready_at, note
            from `tabPOS Kitchen Ticket`
            where pos_profile = %s and status in ('New', 'Preparing', 'Ready')
              and (station = 'Bar' or name like %s)
            order by created_at asc
        """, (pos_profile, "BOT-%"), as_dict=True)
    else:
        tickets = frappe.db.sql("""
            select name, order_type, order_no, table_label, status, station, created_at, started_at, ready_at, note
            from `tabPOS Kitchen Ticket`
            where pos_profile = %s and status in ('New', 'Preparing', 'Ready')
              and ((station = 'Kitchen' or station is null or station = '') and name not like %s)
            order by created_at asc
        """, (pos_profile, "BOT-%"), as_dict=True)

    items = {}
    if tickets:
        rows = frappe.get_all(
            "POS Kitchen Ticket Item",
            filters={"parent": ("in", [t.name for t in tickets])},
            fields=["parent", "item_name", "qty", "note", "modifiers"],
            order_by="idx asc",
            limit_page_length=0,
        )
        for row in rows:
            items.setdefault(row.parent, []).append(
                {
                    "item_name": row.item_name,
                    "qty": flt(row.qty),
                    "note": row.note,
                    "modifiers": _choices(row.modifiers),
                }
            )
    for ticket in tickets:
        ticket["items"] = items.get(ticket.name, [])
        ticket["station"] = station

    avg_seconds = 0
    try:
        if station == "Bar":
            avg = frappe.db.sql("""
                select avg(timestampdiff(second, created_at, ready_at))
                from `tabPOS Kitchen Ticket`
                where pos_profile = %s and (station = 'Bar' or name like %s)
                  and ready_at is not null and date(created_at) = %s
            """, (pos_profile, "BOT-%", nowdate()))
        else:
            avg = frappe.db.sql("""
                select avg(timestampdiff(second, created_at, ready_at))
                from `tabPOS Kitchen Ticket`
                where pos_profile = %s and ((station = 'Kitchen' or station is null or station = '') and name not like %s)
                  and ready_at is not null and date(created_at) = %s
            """, (pos_profile, "BOT-%", nowdate()))
        avg_seconds = cint(avg[0][0]) if avg and avg[0] and avg[0][0] else 0
    except Exception:
        avg_seconds = 0

    return {"tickets": tickets, "now": now_datetime(), "avg_seconds": avg_seconds, "station": station}


@frappe.whitelist()
def set_ticket_status(name: str, status: str):
    """Advance a ticket. The kitchen or bar taps, the times write themselves."""
    doc = frappe.get_doc(TICKET, name)
    doc.check_permission("write")
    restaurant._assert_outlet(doc.pos_profile)
    if status not in FLOW:
        frappe.throw(_("Unknown status {0}").format(status))
    if status == doc.status:
        return {"status": doc.status}
    if status not in FLOW.get(doc.status, set()):
        frappe.throw(_("A ticket cannot go from {0} to {1}").format(_(doc.status), _(status)))

    stamp = {
        "Preparing": "started_at",
        "Ready": "ready_at",
        "Done": "delivered_at",
    }.get(status)

    now = now_datetime()
    updates = {"status": status}
    if stamp and not doc.get(stamp):
        updates[stamp] = now

    # Handover trigger: When a bar ticket is marked Done, deplete dispenser volume!
    if status == "Done" and doc.status != "Done":
        station = doc.get("station") or ("Bar" if doc.name.startswith("BOT-") else "Kitchen")
        is_depleted = cint(frappe.db.get_value(TICKET, name, "is_depleted"))
        if station == "Bar" and not is_depleted:
            try:
                ticket_items = frappe.get_all(
                    "POS Kitchen Ticket Item",
                    filters={"parent": name},
                    fields=["item_code", "item_name", "qty"],
                )
                from lumen_restaurants.api import bar
                bar.deplete_bar_items(ticket_items, source_ref=name)
                updates["is_depleted"] = 1
            except Exception as e:
                frappe.log_error(title="Bar Pour Depletion On Handover Failed", message=str(e))

    for k, v in updates.items():
        frappe.db.set_value(TICKET, name, k, v, update_modified=False)
    frappe.db.set_value(TICKET, name, "modified", now, update_modified=False)
    if status in {"Preparing", "Ready", "Done"} and doc.status != status:
        from lumen_restaurants.api.notifications import notify_ticket_status

        notify_ticket_status(doc, status)
    frappe.db.commit()
    return {"status": status}


@frappe.whitelist()
def ready_calls(pos_profile: str):
    """What the cashier should be calling out: tickets sitting on Ready."""
    restaurant._assert_outlet(pos_profile)
    tickets = frappe.db.sql("""
        select name, order_no, table_label, order_type, station, ready_at
        from `tabPOS Kitchen Ticket`
        where pos_profile = %s and status = 'Ready'
        order by ready_at asc
        limit 20
    """, (pos_profile,), as_dict=True)
    for t in tickets:
        if not t.get("station") or t["station"] != "Bar":
            if t.get("name", "").startswith("BOT-"):
                t["station"] = "Bar"
            else:
                t["station"] = "Kitchen"
    return tickets


@frappe.whitelist()
def sync_custom_fields():
    """Manually invoke custom field creation and cache clearing."""
    from lumen_restaurants.install import make_custom_fields
    make_custom_fields()
    frappe.clear_cache(doctype="Item Group")
    frappe.clear_cache(doctype="Item")
    frappe.clear_cache(doctype="POS Profile")
    frappe.clear_cache(doctype=TICKET)
    return {"status": "ok", "message": "Custom fields synchronized successfully"}


@frappe.whitelist()
def get_station_categories():
    """Returns all Item Groups and their assigned preparation station (Kitchen or Bar)."""
    _ensure_schema()
    groups = frappe.get_all(
        "Item Group",
        fields=["name", "parent_item_group", "is_group"],
        order_by="name asc",
        limit_page_length=0,
    )
    has_field = frappe.db.has_column("Item Group", "lumenpos_station")
    for g in groups:
        st = None
        if has_field:
            st = frappe.db.get_value("Item Group", g.name, "lumenpos_station")
        if not st or st not in ("Kitchen", "Bar"):
            st = "Bar" if is_bar_name(g.name) or is_bar_name(g.parent_item_group) else "Kitchen"
        g["station"] = st
    return groups


@frappe.whitelist()
def set_category_station(item_group: str, station: str):
    """Assigns an Item Group to Kitchen or Bar, cascading to all sub-categories."""
    _ensure_schema()
    if station not in ("Kitchen", "Bar"):
        station = "Kitchen"
    from lumen_restaurants.api.catalog import item_group_and_below
    subgroups = item_group_and_below(item_group) or [item_group]
    for g in subgroups:
        frappe.db.set_value("Item Group", g, "lumenpos_station", station)
    frappe.db.commit()
    frappe.clear_cache(doctype="Item Group")
    return {"item_group": item_group, "station": station, "subgroups": subgroups}
