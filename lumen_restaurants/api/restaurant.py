# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Tables and open orders, for an outlet run as a restaurant.

A retail till sells a basket and is done with it. A restaurant holds the basket
open while people eat, on a table, shared between every device in the place,
and only turns it into money at the end. That open basket is a POS Restaurant
Order, and this module is everything the floor does with it: open one, keep it
saved as the waiter adds to it, move it to another table, pour two together,
cancel it, and finally hand it to the ordinary sale path to be paid.

Nothing here posts an invoice or moves stock. Paying a table order is a normal
`sales.submit_sale` with `order` in the payload, so promotions, loyalty,
cashback, the Z-report and returns all behave exactly as they do on a retail
sale, and there is only ONE place in this app that creates a sale.

Restaurant mode is per outlet: the POS Profile field `lumenpos_restaurant_mode`
(Desk) decides, so a company can run one branch as a cafe and another as a shop
from the same install.
"""

from __future__ import annotations

import datetime
import json

import frappe
from frappe import _
from frappe.utils import cint, flt, get_fullname, get_time, now_datetime, nowdate, nowtime

from lumen_restaurants.api import permissions

TABLE = "POS Restaurant Table"
ORDER = "POS Restaurant Order"


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def enabled(pos_profile):
    """Is this outlet run as a restaurant?"""
    if not pos_profile:
        return False
    return bool(frappe.db.get_value("POS Profile", pos_profile, "lumenpos_restaurant_mode"))


def _assert_outlet(pos_profile):
    """A till may only touch an outlet its user is assigned to."""
    from lumen_restaurants.api.session import _user_profiles

    if not pos_profile:
        frappe.throw(_("No outlet given"))
    if pos_profile not in _user_profiles() and not permissions.is_manager():
        frappe.throw(
            _("You are not assigned to outlet {0}.").format(pos_profile), frappe.PermissionError
        )


def _assert_enabled(pos_profile):
    if not enabled(pos_profile):
        frappe.throw(
            _("Restaurant mode is off for outlet {0}. Turn it on on the POS Profile.").format(
                pos_profile
            )
        )


def _assert_can(capability):
    if not permissions.allowed(capability):
        frappe.throw(
            _("You are not allowed to do that: {0}").format(_(capability)),
            frappe.PermissionError,
        )


def _open_doc(name, ptype="write"):
    doc = frappe.get_doc(ORDER, name)
    doc.check_permission(ptype)
    _assert_outlet(doc.pos_profile)
    return doc


# ---------------------------------------------------------------------------
# The floor
# ---------------------------------------------------------------------------

def _fullnames(users):
    return {user: get_fullname(user) for user in {u for u in users if u}}


# A booking holds its table on the floor from an hour before its time until
# half an hour after it: the guests are late, or nobody has marked a no-show.
HOLD_BEFORE = 60
HOLD_AFTER = 30


def _has_fields(doctype, *fields):
    """A site updated without a migrate lacks the newest fields: the floor
    still answers, without them."""
    try:
        meta = frappe.get_meta(doctype)
    except frappe.DoesNotExistError:
        return False
    return all(meta.has_field(field) for field in fields)


def _layout(table):
    """A table as the plan draws it. One never placed stands at 0, 0 and the
    screen finds it a place; one with no shape is drawn square, or as a
    rectangle from 6 seats."""
    from lumen_restaurants.floor import SHAPES

    table["shape"] = SHAPES.get(table.get("shape")) or ("rect" if cint(table.get("seats")) >= 6 else "square")
    table["pos_x"] = cint(table.get("pos_x"))
    table["pos_y"] = cint(table.get("pos_y"))
    table["rotation"] = cint(table.get("rotation")) % 360
    table["area"] = (table.get("area") or "").strip()


def _hhmm(value):
    """A Time from the database (a timedelta) as 21:05."""
    return get_time(value).strftime("%H:%M") if value not in (None, "") else ""


def _bookings(pos_profile, now, tables):
    """Today's confirmed bookings: the ones holding a table right now, by table,
    and every one still to come, earliest first."""
    known = {t["name"]: t for t in tables}
    rows = frappe.get_all(
        "POS Table Reservation",
        filters={"pos_profile": pos_profile, "reservation_date": now.date(), "status": "Confirmed"},
        fields=["name", "customer_name", "reservation_time", "guests", "table", "source"],
        order_by="reservation_time asc",
        limit_page_length=0,
    )
    held, upcoming = {}, []
    for row in rows:
        at = datetime.datetime.combine(now.date(), get_time(row.reservation_time))
        minutes = (at - now).total_seconds() / 60.0
        if minutes < -HOLD_AFTER:
            continue
        table = known.get(row.table) or {}
        info = {
            "name": row.name,
            "time": at.strftime("%H:%M"),
            "guests": cint(row.guests),
            "customer_name": row.customer_name,
            "source": row.source,
            "table": row.table if table else None,
            "table_no": table.get("table_no"),
            "area": table.get("area"),
        }
        upcoming.append(info)
        if table and minutes <= HOLD_BEFORE and row.table not in held:
            held[row.table] = info
    return held, upcoming[:12]


def _areas(pos_profile, tables):
    """The outlet's areas in the order of their tabs, each with what is drawn
    on it. An area its tables name that nobody has drawn yet follows, with
    nothing on it (the screen gives it four walls and a door until a manager
    saves the plan)."""
    from lumen_restaurants.floor import KINDS

    records = []
    if frappe.db.table_exists("POS Floor Area"):
        records = frappe.get_all(
            "POS Floor Area",
            filters={"pos_profile": pos_profile},
            fields=["name", "area_name", "photo", "photo_opacity"],
            order_by="sort_order asc, creation asc",
            limit_page_length=0,
        )
    drawn = {}
    if records:
        for row in frappe.get_all(
            "POS Floor Object",
            filters={"parenttype": "POS Floor Area", "parent": ["in", [r.name for r in records]]},
            fields=["parent", "kind", "label", "pos_x", "pos_y", "width", "depth", "rotation"],
            order_by="idx asc",
            limit_page_length=0,
        ):
            drawn.setdefault(row.parent, []).append(
                {
                    "kind": KINDS.get(row.kind, "wall"),
                    "label": row.label or "",
                    "x": cint(row.pos_x),
                    "y": cint(row.pos_y),
                    "w": cint(row.width),
                    "h": cint(row.depth),
                    "rot": cint(row.rotation) % 360,
                }
            )
    out = [
        {
            "name": r.name,
            "area_name": r.area_name,
            "photo": r.photo or None,
            "photo_opacity": cint(r.photo_opacity) or 50,
            "objects": drawn.get(r.name, []),
            "drawn": 1,
        }
        for r in records
    ]
    seen = {r.area_name.strip().casefold() for r in records}
    for table in tables:
        key = (table.get("area") or "").strip().casefold()
        if key not in seen:
            seen.add(key)
            out.append(
                {"name": None, "area_name": (table.get("area") or "").strip(), "photo": None, "photo_opacity": 50, "objects": [], "drawn": 0}
            )
    return out


@frappe.whitelist()
def get_floor(pos_profile: str):
    """Every table of this outlet and what is happening on it, plus the orders
    that are not on a table at all (takeaway, delivery).

    Since 0.1.0-r14 also the floor plan: each table's shape and place, the
    tables out of service (for the plan's edit mode), the areas with their
    walls and doors, the bookings that hold a table now and the ones still to
    come today, and whether this outlet draws the plan and this person may
    change it."""
    _assert_outlet(pos_profile)
    from lumen_restaurants import floor

    layout = ["shape", "pos_x", "pos_y", "rotation"] if _has_fields(TABLE, "shape") else []
    rows = frappe.get_all(
        TABLE,
        filters={"pos_profile": pos_profile},
        fields=["name", "table_no", "area", "seats", "disabled", *layout],
        order_by="area asc, table_no asc",
        limit_page_length=0,
    )
    for row in rows:
        _layout(row)
    tables = [row for row in rows if not cint(row.disabled)]
    order_fields = [
        "name", "table", "table_label", "order_type", "guests", "customer",
        "customer_name", "total", "opened_at", "opened_by", "note", "app_type",
    ]
    if _has_fields(ORDER, "bill_printed_at"):
        order_fields.append("bill_printed_at")
    orders = frappe.get_all(
        ORDER,
        filters={"pos_profile": pos_profile, "status": "Open"},
        fields=order_fields,
        order_by="opened_at asc",
        limit_page_length=0,
    )
    names = _fullnames([o.opened_by for o in orders])
    # One query for every order's line count, not one per order: a busy floor
    # polls this every few seconds from every device in the place.
    counts = {}
    if orders:
        # Plain SQL: Frappe 16 refuses an SQL function written as text in
        # get_all fields, so "count(name)" there killed the floor screen on
        # v16 as soon as one table had an order (LumenPOS inbox, 2026-09-28).
        # NOT "as lines": lines is a reserved word in MariaDB and the whole
        # floor screen dies with a syntax error.
        rows_count = frappe.db.sql(
            """select parent, count(name) as line_count
            from `tabPOS Restaurant Order Item`
            where parent in %(orders)s
            group by parent""",
            {"orders": [o.name for o in orders]},
            as_dict=True,
        )
        counts = {row["parent"]: row["line_count"] for row in rows_count}
    for order in orders:
        order["opened_by_name"] = names.get(order.opened_by) or order.opened_by
        order["lines"] = counts.get(order.name, 0)
    by_table = {o.table: o for o in orders if o.table}
    now = now_datetime()
    held, upcoming = _bookings(pos_profile, now, rows)
    for table in tables:
        table["order"] = by_table.get(table["name"])
        table["booking"] = None if table["order"] else held.get(table["name"])
    plan_on = floor.plan_on(pos_profile)
    return {
        "tables": tables,
        # The plan's edit mode shows them dashed, the floor never.
        "off_tables": [row for row in rows if cint(row.disabled)],
        # Takeaway and delivery sit beside the floor, they have no table.
        "loose": [o for o in orders if not o.table],
        # The clock the elapsed times are measured against is the SERVER's, so
        # a tablet with a wrong clock still shows the right "sitting for".
        "now": now,
        "areas": _areas(pos_profile, rows),
        "upcoming": upcoming,
        "plan": {"on": plan_on, "can_edit": bool(plan_on and permissions.can_edit_floor())},
    }


# ---------------------------------------------------------------------------
# An order
# ---------------------------------------------------------------------------

def _as_dict(doc, with_cart=False):
    data = {
        "name": doc.name,
        "pos_profile": doc.pos_profile,
        "table": doc.table,
        "table_label": doc.table_label,
        "order_type": doc.order_type,
        "guests": cint(doc.guests),
        "customer": doc.customer,
        "customer_name": doc.customer_name,
        "status": doc.status,
        "total": flt(doc.total, 2),
        "note": doc.note,
        "app_type": doc.app_type,
        "order_id": doc.order_id,
        "opened_at": doc.opened_at,
        "opened_by": doc.opened_by,
        "opened_by_name": get_fullname(doc.opened_by) if doc.opened_by else None,
        "lines": len(doc.items or []),
    }
    if with_cart:
        data["cart"] = json.loads(doc.cart or "{}")
    return data


@frappe.whitelist()
def open_order(
    pos_profile: str,
    table: str | None = None,
    order_type: str = "Dine in",
    guests: int | str | bool = 0,
    customer: str | None = None,
    note: str | None = None,
    app_type: str | None = None,
    order_id: str | None = None,
):
    """Start serving. No money moves, so no register session is needed: a
    waiter with a tablet can open a table before the till is even manned."""
    _assert_outlet(pos_profile)
    _assert_enabled(pos_profile)
    _assert_can(permissions.OPEN_TABLE)
    if table:
        # Two waiters can tap the same table at the same moment. Locking the
        # table row first makes the second one wait, then fail the check, so a
        # table can never end up with two open orders.
        frappe.db.get_value(TABLE, table, "name", for_update=True)
        twin = frappe.db.exists(ORDER, {"table": table, "status": "Open"})
        if twin:
            frappe.throw(_("That table already has an open order ({0})").format(twin))
    doc = frappe.get_doc(
        {
            "doctype": ORDER,
            "pos_profile": pos_profile,
            "table": table or None,
            "order_type": order_type or "Dine in",
            "guests": cint(guests),
            "customer": customer or None,
            "note": (note or "").strip() or None,
            "app_type": (app_type or "").strip() or None,
            "order_id": (order_id or "").strip() or None,
            "status": "Open",
            "opened_by": frappe.session.user,
            "opened_at": now_datetime(),
            "cart": json.dumps({"lines": []}),
        }
    ).insert()
    return _as_dict(doc, with_cart=True)


@frappe.whitelist()
def get_order(name: str):
    """Reopen an order on any device, exactly as it was left."""
    return _as_dict(_open_doc(name, "read"), with_cart=True)


@frappe.whitelist()
def list_orders(pos_profile: str, status: str = "Open", limit: int | str | bool = 50):
    _assert_outlet(pos_profile)
    return frappe.get_all(
        ORDER,
        filters={"pos_profile": pos_profile, "status": status},
        fields=[
            "name", "table_label", "order_type", "guests", "customer_name",
            "total", "status", "opened_at", "closed_at",
        ],
        order_by="opened_at desc",
        limit_page_length=cint(limit) or 50,
    )


def _derive_items(doc, cart):
    """The readable view of the cart: what was ordered, at what price.

    Indicative, not accounting. Promotions and the basket discount are resolved
    by the server at payment, so the figure on the floor screen can be a little
    above what the guest finally pays. The invoice is the authority, always."""
    from lumen_restaurants import modifiers

    doc.set("items", [])
    for line in cart.get("lines") or []:
        qty = flt(line.get("qty"))
        rate = flt(line.get("price")) * (1 - flt(line.get("manual_discount_percent")) / 100.0)
        choices = modifiers.clean_choices(line.get("lr_mods"))
        doc.append(
            "items",
            {
                "item_code": line.get("item_code"),
                "item_name": line.get("item_name"),
                "qty": qty,
                "rate": flt(rate, 2),
                "amount": flt(qty * rate, 2),
                "note": ((line.get("note") or "").strip())[:500] or None,
                # The guest's choices, and a paid add-on's dish (modifiers.py).
                "modifiers": json.dumps(choices, ensure_ascii=False) if choices else None,
                "line_id": str(line.get("lr_line") or "")[:40] or None,
                "addon_of": str(line.get("lr_addon_of") or "")[:40] or None,
            },
        )


# ---------------------------------------------------------------------------
# A price typed at the till on a table order (LumenPOS 0.55.0 on the shop
# screen, here since 0.1.0-r11). It is checked when it is TYPED: the outlet
# lets prices be changed (POS Profile, Allow User to Edit Rate) and the person
# may (Edit price / discount). It stays on the order with the name of whoever
# typed it, so the cashier who takes the money needs no right of their own.


def _typed_prices(cart):
    """{item code: (typed price, who typed it)} on an order's cart."""
    out = {}
    for line in (cart or {}).get("lines") or []:
        if line.get("bundle_key") or line.get("price_override") in (None, ""):
            continue
        out[line.get("item_code")] = (flt(line.get("price_override"), 2), line.get("price_override_by"))
    return out


def assert_one_price_per_item(rows):
    """Every line of one item carries the same typed price, or none. A return
    takes an item back at one rate (sales._build_return_doc keeps its first
    line), so two burgers at two prices would be refunded wrong. Bundle lines
    keep their own pricing and are left out."""
    prices = {}
    for row in rows or []:
        if row.get("bundle_key"):
            continue
        value = row.get("price_override")
        value = None if value in (None, "") else flt(value, 2)
        code = row.get("item_code")
        if code in prices and prices[code] != value:
            frappe.throw(
                _("{0} is on this order at two prices. Type one price for all of it.").format(
                    row.get("item_name") or code
                )
            )
        prices[code] = value


def _check_typed_prices(doc, old_cart, new_cart):
    """The typed prices of an order being saved: one per item, a new or
    changed one only from someone who may type prices at this outlet. Each
    carries who typed it. Returns the lines typed now, one per item."""
    lines = new_cart.get("lines") or []
    assert_one_price_per_item(lines)
    before = _typed_prices(old_cart)
    typed_now = {}
    for line in lines:
        if line.get("bundle_key"):
            continue
        if line.get("price_override") in (None, ""):
            line.pop("price_override_by", None)
            continue
        code = line.get("item_code")
        was = before.get(code)
        if was and was[1] and abs(was[0] - flt(line.get("price_override"), 2)) < 0.005:
            line["price_override_by"] = was[1]
            continue
        typed_now.setdefault(code, line)
        line["price_override_by"] = frappe.session.user
    if typed_now:
        profile = frappe.get_cached_doc("POS Profile", doc.pos_profile)
        if not cint(profile.get("allow_rate_change")):
            frappe.throw(
                _("{0} does not let prices be changed at the till. Tick Allow User to Edit Rate on its POS Profile to allow it.").format(
                    profile.name
                ),
                frappe.PermissionError,
            )
        if not permissions.can_edit_price():
            frappe.throw(
                _("You're not allowed to edit prices or apply discounts on a sale."),
                frappe.PermissionError,
            )
    return list(typed_now.values())


def typed_on_order(payload, rows):
    """Were the typed prices of this sale all typed on the table order it pays,
    by someone allowed to (save_order checked them)? Then the cashier taking
    the money needs no right to type prices."""
    name = payload.get("order")
    if not name or not rows:
        return False
    order = frappe.db.get_value(ORDER, name, ["status", "cart", "pos_profile"], as_dict=True)
    if not order or order.status != "Open" or order.pos_profile != payload.get("pos_profile"):
        return False
    typed = _typed_prices(json.loads(order.cart or "{}"))
    for row in rows:
        was = typed.get(row.get("item_code"))
        if not was or not was[1] or abs(was[0] - flt(row.get("price_override"), 2)) >= 0.005:
            return False
    return True


@frappe.whitelist()
def save_order(name: str, cart: dict | list | str | None = None, customer: str | None = None, guests: int | str | bool | None = None, note: str | None = None, order_type: str | None = None):
    """Keep the order up to date as the waiter rings items in.

    The till calls this on every change (debounced), so an order survives a
    dropped tablet, a locked screen or a waiter who walks away."""
    doc = _open_doc(name)
    if doc.status != "Open":
        frappe.throw(_("This order is {0} and cannot be changed").format(_(doc.status)))
    typed_now = []
    if cart is not None:
        if isinstance(cart, str):
            cart = json.loads(cart or "{}")
        typed_now = _check_typed_prices(doc, json.loads(doc.cart or "{}"), cart)
        doc.cart = json.dumps(cart)
        billed = _bill_lines(doc)
        _derive_items(doc, cart)
        # The printed bill no longer says what the table owes: the table stops
        # waiting to pay until the bill is printed again (0.1.0-r14).
        if doc.get("bill_printed_at") and _bill_lines(doc) != billed:
            doc.bill_printed_at = None
    if customer is not None:
        doc.customer = customer or None
        doc.customer_name = (
            frappe.db.get_value("Customer", customer, "customer_name") if customer else None
        )
    if guests is not None:
        doc.guests = cint(guests)
    if note is not None:
        doc.note = (note or "").strip() or None
    if order_type:
        doc.order_type = order_type
    doc.save()
    if typed_now:
        from lumen_restaurants.api import audit

        for line in typed_now:
            audit.log(
                audit.PRICE_EDIT,
                detail=_("{0}: price changed from {1} to {2}").format(
                    line.get("item_code"), flt(line.get("price_before_override"), 2), flt(line.get("price_override"), 2)
                ),
                amount=flt(line.get("price_override")),
                reference_doctype=ORDER,
                reference_name=doc.name,
                pos_profile=doc.pos_profile,
            )
    return _as_dict(doc)


@frappe.whitelist()
def move_order(name: str, table: str | None = None):
    """Move an order to another table, or off the floor entirely (which is what
    a takeaway is)."""
    _assert_can(permissions.MOVE_TABLE)
    doc = _open_doc(name)
    if doc.status != "Open":
        frappe.throw(_("This order is {0}").format(_(doc.status)))
    if table:
        frappe.db.get_value(TABLE, table, "name", for_update=True)
        twin = frappe.db.exists(ORDER, {"table": table, "status": "Open", "name": ("!=", name)})
        if twin:
            frappe.throw(_("That table already has an open order ({0})").format(twin))
    doc.table = table or None
    doc.save()
    return _as_dict(doc)


@frappe.whitelist()
def merge_orders(source: str, target: str):
    """Pour one order into another: two tables joined, or a guest who moved.

    The source keeps its number and its history, marked Merged and pointing at
    where it went, so nothing is ever silently erased."""
    _assert_can(permissions.MOVE_TABLE)
    if source == target:
        frappe.throw(_("Pick two different orders"))
    src = _open_doc(source)
    dst = _open_doc(target)
    if src.pos_profile != dst.pos_profile:
        frappe.throw(_("Those orders belong to different outlets"))
    if src.status != "Open" or dst.status != "Open":
        frappe.throw(_("Both orders have to be open"))
    src_cart = json.loads(src.cart or "{}")
    dst_cart = json.loads(dst.cart or "{}")
    dst_cart["lines"] = (dst_cart.get("lines") or []) + (src_cart.get("lines") or [])
    dst.cart = json.dumps(dst_cart)
    _derive_items(dst, dst_cart)
    dst.guests = cint(dst.guests) + cint(src.guests)
    # A bill printed for either table no longer covers the two (0.1.0-r14).
    dst.bill_printed_at = None
    dst.save()
    src.status = "Merged"
    src.merged_into = dst.name
    src.closed_at = now_datetime()
    src.set("items", [])
    src.cart = json.dumps({"lines": []})
    src.save()
    return _as_dict(dst)


@frappe.whitelist()
def cancel_order(name: str, reason: str | None = None):
    """Nobody ate: the guests left, or the order was rung up by mistake.

    A cancelled order that had items on it has to say why. That line is the
    only trail there is, since an order never posted anything to cancel."""
    _assert_can(permissions.CANCEL_ORDER)
    doc = _open_doc(name)
    if doc.status != "Open":
        frappe.throw(_("This order is {0}").format(_(doc.status)))
    if doc.invoices:
        frappe.throw(_("This order has already been billed"))
    reason = (reason or "").strip()
    if doc.items and not reason:
        frappe.throw(_("Give a reason for cancelling an order that has items on it"))
    doc.status = "Cancelled"
    doc.cancel_reason = reason or None
    doc.closed_at = now_datetime()
    doc.save()
    return _as_dict(doc)


# ---------------------------------------------------------------------------
# The bill (0.1.0-r14): what the table owes before it pays, priced exactly as
# the sale will be, and printed with our mark at its foot like every receipt.


def _bill_lines(doc):
    """What a printed bill shows of an order, to tell when it has changed."""
    return [(row.item_code, flt(row.qty), flt(row.rate, 2)) for row in doc.items or []]


def _cart_payload(doc):
    """The sale an order would make, as the till sends it (cart.js
    _basePayload), built from the order's own cart."""
    cart = json.loads(doc.cart or "{}")
    items = []
    for line in cart.get("lines") or []:
        row = {
            "item_code": line.get("item_code"),
            "qty": line.get("qty"),
            "manual_discount_percent": line.get("manual_discount_percent") or 0,
            "price_override": line.get("price_override"),
            "serial_nos": line.get("serial_nos") or [],
            "bundle_key": line.get("bundle_key") or None,
        }
        if line.get("lr_line"):
            row.update({"lr_line": line["lr_line"], "lr_mods": line.get("lr_mods") or [], "lr_note": line.get("note") or ""})
        if line.get("lr_addon_of"):
            row["lr_addon_of"] = line["lr_addon_of"]
        items.append(row)
    return {
        "pos_profile": doc.pos_profile,
        "customer": doc.customer or None,
        "items": items,
        "coupon_codes": cart.get("coupon_codes") or [],
        "sales_person": cart.get("sales_person"),
        "app_type": cart.get("app_type") or doc.app_type,
        "order_id": cart.get("order_id") or doc.order_id,
        "order_discount_percent": cart.get("order_discount_percent") or 0,
        "note": cart.get("note") or None,
        # A price typed on the order was checked when it was typed.
        "order": doc.name,
    }


def _bill(doc):
    """The bill of an open order, in the shape of a receipt (sales.get_receipt)
    so the till prints it the same way. Priced by the sale's own code without
    saving anything, as quote_sale is; when that cannot price it (no customer
    and no walk-in customer on the outlet, say) the order's own figures are
    used and the bill says it is an estimate."""
    from lumen_restaurants import modifiers
    from lumen_restaurants.api import sales
    from lumen_restaurants.api.settings import effective_receipt

    profile = frappe.get_cached_doc("POS Profile", doc.pos_profile)
    company = doc.company or profile.company
    receipt_settings = effective_receipt(doc.pos_profile)
    if not receipt_settings.get("receipt_tax_id"):
        receipt_settings["receipt_tax_id"] = frappe.get_cached_value("Company", company, "tax_id") or ""
    bill = {
        "is_bill": 1,
        "name": doc.name,
        "order": doc.name,
        "pos_profile": doc.pos_profile,
        "table_label": doc.table_label,
        "guests": cint(doc.guests),
        "receipt_settings": receipt_settings,
        "custom_fields": [],
        "company": company,
        "customer": doc.customer,
        "customer_name": doc.customer_name or "",
        "posting_date": nowdate(),
        "posting_time": nowtime(),
        "currency": profile.currency,
        "items": [],
        "taxes": [],
        "payments": [],
        "applied_promotions": [],
        "discount_amount": 0,
        "net_total": 0,
        "grand_total": 0,
        "rounded_total": 0,
        "estimated": 0,
    }
    if not doc.items:
        return bill
    try:
        invoice, _customer = sales._build_sale_invoice(
            profile, _cart_payload(doc), validate_serials=False, check_passcode=False,
            session_name=sales._quote_session(profile.name),
        )
    except Exception:
        # Not this call's error to show: the order's own lines stand in.
        frappe.local.message_log = []
        bill.update(
            {
                "estimated": 1,
                "items": [
                    {"item_code": row.item_code, "item_name": row.item_name, "qty": flt(row.qty), "rate": flt(row.rate), "amount": flt(row.amount)}
                    for row in doc.items
                ],
                "net_total": flt(doc.total, 2),
                "grand_total": flt(doc.total, 2),
                "rounded_total": flt(doc.total, 2),
            }
        )
        return bill
    prec = invoice.precision("grand_total")
    bill.update(
        {
            "currency": invoice.currency,
            "customer_name": invoice.customer_name or bill["customer_name"],
            "sales_person": invoice.sales_team[0].sales_person if invoice.get("sales_team") else None,
            "items": [
                {
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "qty": flt(row.qty),
                    "rate": flt(row.rate),
                    "amount": flt(row.amount),
                    "discount_amount": flt(row.discount_amount),
                    **modifiers.receipt_item(row, doc.pos_profile),
                }
                for row in invoice.items
            ],
            "taxes": [
                {
                    "description": tax.description,
                    "tax_amount": flt(tax.tax_amount, prec),
                    "rate": flt(tax.rate),
                    "included": cint(tax.included_in_print_rate),
                }
                for tax in invoice.taxes or []
                if flt(tax.tax_amount)
            ],
            "applied_promotions": json.loads(sales._get_custom(invoice, ("lumenpos_promotions",)) or "[]"),
            "discount_amount": flt(invoice.discount_amount, prec),
            "net_total": flt(invoice.net_total, prec),
            "grand_total": flt(invoice.grand_total, prec),
            "rounded_total": flt(invoice.rounded_total, prec),
        }
    )
    return bill


@frappe.whitelist()
def get_bill(name: str):
    """What an open order owes, as the guests will pay it. Nothing is saved."""
    return _bill(_open_doc(name, "read"))


@frappe.whitelist()
def print_bill(name: str, printer: int | str | bool = 0):
    """The guests asked for the bill. It is marked on the order, so the floor
    shows the table waiting to pay, and comes back to be printed: by the
    outlet's receipt printer when the till asks and there is one, else by the
    till's browser. Our mark is at its foot either way, as on every receipt."""
    doc = _open_doc(name)
    if doc.status != "Open":
        frappe.throw(_("This order is {0}").format(_(doc.status)))
    if not doc.items:
        frappe.throw(_("Nothing to bill yet: the order has no items"))
    bill = _bill(doc)
    if doc.meta.has_field("bill_printed_at"):
        doc.db_set("bill_printed_at", now_datetime())
    printed, error = False, None
    ip = frappe.db.get_value("POS Profile", doc.pos_profile, "lumenpos_printer_ip") if cint(printer) else None
    if ip:
        from lumen_restaurants.api import printing

        port = frappe.db.get_value("POS Profile", doc.pos_profile, "lumenpos_printer_port") or 9100
        try:
            printing._send(ip, int(port), printing.build_receipt_bytes(bill))
            printed = True
        except Exception as e:
            frappe.local.message_log = []
            error = str(e)
    return {"bill": bill, "printed": printed, "printer_error": error}


def close_order(name, invoice, amount):
    """The order was paid. Called by sales.submit_sale, never by the client.

    The table is free the moment the money is in, which is why this runs on the
    sale itself and not on a later click a cashier could forget."""
    doc = frappe.get_doc(ORDER, name)
    if doc.status != "Open":
        return
    doc.append(
        "invoices",
        {"invoice": invoice, "amount": flt(amount, 2), "billed_at": now_datetime()},
    )
    doc.status = "Closed"
    doc.closed_at = now_datetime()
    doc.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# The tables themselves (Settings)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def list_tables(pos_profile: str):
    _assert_outlet(pos_profile)
    return frappe.get_all(
        TABLE,
        filters={"pos_profile": pos_profile},
        fields=["name", "table_no", "area", "seats", "disabled"],
        order_by="area asc, table_no asc",
        limit_page_length=0,
    )


@frappe.whitelist()
def save_table(pos_profile: str, table_no: str, area: str | None = None, seats: int | str | bool = 4, name: str | None = None, disabled: int | str | bool = 0):
    """Add or edit a table. Governed by the ordinary DocType permissions, so a
    shop can let a supervisor rearrange the floor without making them a manager."""
    _assert_outlet(pos_profile)
    from lumen_restaurants.api.settings import _require

    if name:
        _require(TABLE, "write")
        doc = frappe.get_doc(TABLE, name)
    else:
        _require(TABLE, "create")
        doc = frappe.new_doc(TABLE)
        doc.pos_profile = pos_profile
    doc.table_no = table_no
    doc.area = area
    doc.seats = cint(seats)
    doc.disabled = 1 if cint(disabled) else 0
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def delete_table(name: str):
    from lumen_restaurants.api.settings import _require

    _require(TABLE, "delete")
    doc = frappe.get_doc(TABLE, name)
    _assert_outlet(doc.pos_profile)
    doc.delete()
    return {"deleted": name}
