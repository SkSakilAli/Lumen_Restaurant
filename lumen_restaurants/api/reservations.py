# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Reservations: the till's book, and the public page's letterbox.

Staff reservations are Confirmed the moment they are written, because a person
took them. The public page writes Requested ones, and they wait in a tray on
the reservations screen until somebody confirms or declines: the page promises
the customer a call back, never a table. Guests never read anything.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_time, getdate, now_datetime, nowdate

from frappe.rate_limiter import rate_limit

from lumen_restaurants.api import restaurant

RES = "POS Table Reservation"


WEEKDAYS = ["closed_mon", "closed_tue", "closed_wed", "closed_thu", "closed_fri", "closed_sat", "closed_sun"]
LIVE = ("Requested", "Confirmed", "Seated")


def _page(pos_profile, published_only=True):
    """The designed page for an outlet, or None when there is no bookable one."""
    if not pos_profile or not frappe.db.exists("POS Booking Page", pos_profile):
        return None
    doc = frappe.get_cached_doc("POS Booking Page", pos_profile)
    if published_only and not doc.published:
        return None
    if not restaurant.enabled(pos_profile):
        return None
    return doc


def _closed_on(page, date):
    return bool(page.get(WEEKDAYS[getdate(date).weekday()]))


def _slot_load(pos_profile, date):
    """Guests already booked per time slot on a day, only the bookings that
    still hold a table."""
    rows = frappe.db.sql(
        """select time_format(reservation_time, '%%H:%%i') as slot, sum(guests) as guests
           from `tabPOS Table Reservation`
           where pos_profile = %s and reservation_date = %s and status in %s
           group by slot""",
        (pos_profile, getdate(date), LIVE),
        as_dict=True,
    )
    return {row.slot: cint(row.guests) for row in rows}


# ---------------------------------------------------------------------------
# The till's book
# ---------------------------------------------------------------------------

@frappe.whitelist()
def day(pos_profile: str, date: str | None = None):
    """One day of the book, plus the tray of online requests (any day)."""
    restaurant._assert_outlet(pos_profile)
    date = getdate(date) if date else getdate(nowdate())
    rows = frappe.get_all(
        RES,
        filters={"pos_profile": pos_profile, "reservation_date": date},
        fields=[
            "name", "customer_name", "phone", "reservation_time", "guests",
            "table", "status", "source", "note", "seated_order", "answers", "estimated_total",
        ],
        order_by="reservation_time asc",
        limit_page_length=0,
    )
    _attach_extras(rows)
    tables = {
        t.name: (f"{t.area} {t.table_no}".strip() if t.area else t.table_no)
        for t in frappe.get_all(
            "POS Restaurant Table",
            filters={"pos_profile": pos_profile},
            fields=["name", "table_no", "area"],
        )
    }
    for row in rows:
        row["table_label"] = tables.get(row.table)
        row["reservation_time"] = restaurant._hhmm(row.reservation_time)
    requested = frappe.get_all(
        RES,
        filters={"pos_profile": pos_profile, "status": "Requested"},
        fields=[
            "name", "customer_name", "phone", "reservation_date",
            "reservation_time", "guests", "note", "answers", "estimated_total",
        ],
        order_by="reservation_date asc, reservation_time asc",
        limit_page_length=50,
    )
    _attach_extras(requested)
    for row in requested:
        row["reservation_time"] = restaurant._hhmm(row.reservation_time)
    return {"date": str(date), "rows": rows, "requested": requested, "now": now_datetime()}


def _attach_extras(rows):
    """Parse the answers and fetch the packages for a list of bookings, in one
    query for all of them."""
    names = [row.name for row in rows]
    packages = {}
    if names:
        for item in frappe.get_all(
            "POS Table Reservation Item",
            filters={"parent": ("in", names)},
            fields=["parent", "item_code", "item_name", "qty", "rate", "amount"],
            order_by="idx asc",
            limit_page_length=0,
        ):
            packages.setdefault(item.parent, []).append(item)
    for row in rows:
        try:
            row["answers"] = json.loads(row.get("answers") or "[]")
        except ValueError:
            row["answers"] = []
        row["items"] = packages.get(row.name, [])


@frappe.whitelist()
def requested_count(pos_profile: str):
    """The badge on the rail: online requests waiting for a person."""
    restaurant._assert_outlet(pos_profile)
    return frappe.db.count(RES, {"pos_profile": pos_profile, "status": "Requested"})


@frappe.whitelist()
def save_reservation(payload: dict | list | str):
    """Create or edit one, from the till. Staff entries are Confirmed at birth:
    a person just took them."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    pos_profile = payload.get("pos_profile")
    restaurant._assert_outlet(pos_profile)
    if payload.get("name"):
        doc = frappe.get_doc(RES, payload["name"])
        if doc.pos_profile != pos_profile:
            frappe.throw(_("That reservation belongs to another outlet"))
    else:
        doc = frappe.new_doc(RES)
        doc.pos_profile = pos_profile
        doc.source = "Till"
        doc.status = "Confirmed"
    doc.customer_name = payload.get("customer_name")
    doc.phone = payload.get("phone")
    doc.reservation_date = getdate(payload.get("reservation_date") or nowdate())
    doc.reservation_time = str(payload.get("reservation_time") or "19:00")
    doc.guests = cint(payload.get("guests")) or 2
    doc.table = payload.get("table") or None
    doc.note = (payload.get("note") or "").strip() or None
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def set_reservation_status(name: str, status: str):
    """Confirm a request, seat an arrival, record a no-show, or cancel.

    Seating with a table attached opens the table order there and then, so the
    host presses one button and the till is already on it."""
    if status not in ("Confirmed", "Seated", "No show", "Cancelled"):
        frappe.throw(_("Unknown status {0}").format(status))
    doc = frappe.get_doc(RES, name)
    doc.check_permission("write")
    restaurant._assert_outlet(doc.pos_profile)
    opened = None
    if status == "Seated" and doc.table and not frappe.db.exists(
        "POS Restaurant Order", {"table": doc.table, "status": "Open"}
    ):
        opened = restaurant.open_order(
            doc.pos_profile,
            table=doc.table,
            order_type="Dine in",
            guests=doc.guests or 0,
            note=_("Reservation {0}").format(doc.customer_name),
        )
        doc.seated_order = opened["name"]
        if doc.items:
            # The buffet or the set menu they booked is already on the table
            # when they sit down; the till reprices it at payment as always.
            restaurant.save_order(
                opened["name"],
                cart={
                    "lines": [
                        {
                            "item_code": row.item_code,
                            "item_name": row.item_name,
                            "qty": flt(row.qty),
                            "price": flt(row.rate),
                        }
                        for row in doc.items
                    ],
                    "note": None,
                },
            )
            opened = restaurant.get_order(opened["name"])
    doc.status = status
    doc.save(ignore_permissions=True)
    return {"status": doc.status, "order": opened}


# ---------------------------------------------------------------------------
# The public page's letterbox
# ---------------------------------------------------------------------------

def _outlet_bookable(pos_profile):
    return _page(pos_profile) is not None


def _clean_answers(page, answers):
    """Every extra field the owner added, checked against its own definition.
    Unknown keys are dropped, required ones must be there, a list answer must
    be one of the list. Stored with the label of the day, so renaming a field
    later never garbles an old booking."""
    if isinstance(answers, str):
        answers = json.loads(answers or "{}")
    answers = answers or {}
    out = []
    for field in page.fields or []:
        raw = answers.get(field.key)
        value = "" if raw is None else str(raw).strip()
        if field.fieldtype == "Check":
            value = "1" if raw in (1, "1", True, "true", "on") else ""
        if field.fieldtype == "Number" and value:
            try:
                value = str(float(value)).rstrip("0").rstrip(".")
            except ValueError:
                frappe.throw(_("{0} has to be a number").format(field.label))
        if field.fieldtype == "Select" and value:
            allowed = [line.split("|")[0].strip() for line in (field.options or "").splitlines() if line.strip()]
            if value not in allowed:
                frappe.throw(_("Pick one of the choices for {0}").format(field.label))
        if field.fieldtype == "Date" and value:
            value = str(getdate(value))
        if field.required and not value:
            frappe.throw(_("{0} is required").format(field.label))
        if value:
            out.append({"key": field.key, "label": field.label, "value": value[:500]})
    return out


def _clean_items(page, items, people):
    """The packages picked on the page, priced from the outlet price list.
    A per guest package follows the party size, a required one is always in."""
    if isinstance(items, str):
        items = json.loads(items or "[]")
    wanted = {}
    for row in items or []:
        code = (row or {}).get("item_code")
        if code:
            wanted[code] = cint(row.get("qty"))
    profile = frappe.get_cached_doc("POS Profile", page.pos_profile)
    from lumen_restaurants.api.booking_page import _price

    out = []
    for item in page.items or []:
        qty = wanted.get(item.item_code, 0)
        if item.pricing == "Per guest" and (qty or item.required):
            qty = people
        elif item.required and qty < 1:
            qty = 1
        if qty <= 0:
            continue
        if item.pricing != "Per guest" and qty > cint(item.max_qty or 10):
            frappe.throw(_("At most {0} of {1}").format(cint(item.max_qty or 10), item.title or item.item_code))
        rate = _price(profile, item.item_code)
        out.append(
            {
                "item_code": item.item_code,
                "item_name": item.title or frappe.db.get_value("Item", item.item_code, "item_name"),
                "qty": qty,
                "rate": rate,
                "amount": flt(qty * rate, 2),
            }
        )
    return out


# The public booking page asks it: counts of a day's full slots, never a name.
@frappe.whitelist(allow_guest=True)  # nosemgrep
def availability(pos_profile: str | None = None, date: str | None = None, guests: int | str | bool | None = None):
    """Which slots on a day can still take this party. Counts only, never a
    name: the page greys out a full slot instead of letting a guest find out
    at the door."""
    page = _page(pos_profile)
    if not page:
        frappe.throw(_("Online booking is not available for this branch"))
    if not date:
        frappe.throw(_("Pick a day"))
    if _closed_on(page, date):
        return {"closed": True, "full": []}
    capacity = cint(page.slot_capacity)
    if not capacity:
        return {"closed": False, "full": []}
    people = max(cint(guests) or 1, 1)
    load = _slot_load(pos_profile, date)
    full = [slot for slot, taken in load.items() if taken + people > capacity]
    return {"closed": False, "full": sorted(full)}


# The public booking page posts it: one Requested booking, a honeypot against
# bots, every field checked against the page, the daily limits per phone and
# per address below, and at most 60 tries an hour from one address (Frappe's own
# rate limiter): far above any guest, it stops a script hammering the page.
@frappe.whitelist(allow_guest=True)  # nosemgrep
@rate_limit(limit=60, seconds=60 * 60)
def book_online(pos_profile: str | None = None, customer_name: str | None = None, phone: str | None = None, reservation_date: str | None = None,
                reservation_time: str | None = None, guests: int | str | bool | None = None, note: str | None = None, website: str | None = None,
                answers: dict | list | str | None = None, items: dict | list | str | None = None):
    """The public form posts here. Writes ONE booking against the page as its
    owner designed it, and reads nothing back but a reference.

    `website` is the honeypot: humans never see the field, bots fill it."""
    if (website or "").strip():
        return {"ok": True, "ref": "RSV", "status": "Requested"}  # a bot leaves empty handed
    page = _page(pos_profile)
    if not page:
        frappe.throw(_("Online booking is not available for this branch"))

    customer_name = (customer_name or "").strip()[:80]
    phone = "".join(ch for ch in (phone or "") if ch.isdigit() or ch == "+")[:16]
    if len(customer_name) < 2:
        frappe.throw(_("Write your name"))
    if len(phone) < 9:
        frappe.throw(_("Write a phone number we can reach you on"))

    date = getdate(reservation_date)
    today = getdate(nowdate())
    days = cint(page.days_ahead) or 14
    if date < today or date > add_days(today, days):
        frappe.throw(_("Pick a day within the next {0} days").format(days))
    if _closed_on(page, date):
        frappe.throw(_("We are closed that day, pick another"))
    try:
        moment = get_time(str(reservation_time))
    except Exception:
        frappe.throw(_("Pick a time"))
    opens, closes = get_time(str(page.open_time)), get_time(str(page.close_time))
    if not (opens <= moment <= closes):
        frappe.throw(_("We take bookings between {0} and {1}").format(restaurant._hhmm(page.open_time), restaurant._hhmm(page.close_time)))
    # Only the times the page offers: one off the grid would sit in a slot of
    # its own and get round the capacity of the real one next to it.
    step = max(cint(page.slot_minutes) or 30, 10)
    if ((moment.hour * 60 + moment.minute) - (opens.hour * 60 + opens.minute)) % step:
        frappe.throw(_("Pick one of the times on the page"))
    now = now_datetime()
    if date == now.date() and moment <= now.time():
        frappe.throw(_("That time has passed, pick a later one"))
    people = cint(guests) or 2
    if people < cint(page.min_guests or 1):
        frappe.throw(_("The smallest party we book is {0}").format(cint(page.min_guests)))
    if people > cint(page.max_guests or 12):
        frappe.throw(_("For more than {0} guests, call the branch").format(cint(page.max_guests)))
    slot = moment.strftime("%H:%M")
    capacity = cint(page.slot_capacity)
    if capacity and _slot_load(pos_profile, date).get(slot, 0) + people > capacity:
        frappe.throw(_("That time is full, pick another"))

    clean_answers = _clean_answers(page, answers)
    clean_items = _clean_items(page, items, people)

    # A letterbox, not a firehose: a phone or an address that keeps stuffing it
    # today is politely told to call instead.
    ip = getattr(frappe.local, "request_ip", None) or ""
    flooded = frappe.db.count(
        RES,
        {
            "source": "Online",
            "creation": (">=", str(today)),
            "phone": phone,
        },
    ) >= 5
    if not flooded and ip:
        flooded = frappe.db.count(
            RES, {"source": "Online", "creation": (">=", str(today)), "created_ip": ip}
        ) >= 15
    if flooded:
        frappe.throw(_("Too many requests today. Call the branch and we will book you in"))

    status = "Confirmed" if page.auto_confirm else "Requested"
    doc = frappe.get_doc(
        {
            "doctype": RES,
            "pos_profile": pos_profile,
            "customer_name": customer_name,
            "phone": phone,
            "reservation_date": date,
            "reservation_time": str(reservation_time),
            "guests": people,
            "note": (note or "").strip()[:300] or None,
            "status": status,
            "source": "Online",
            "created_ip": ip[:45] or None,
            "answers": json.dumps(clean_answers, ensure_ascii=False) if clean_answers else None,
            "items": clean_items,
            "estimated_total": flt(sum(row["amount"] for row in clean_items), 2),
        }
    )
    doc.insert(ignore_permissions=True)
    # A guest request must survive its own response. The marker stays bare:
    # semgrep reads any words after its colon as rule ids and suppresses nothing.
    frappe.db.commit()  # nosemgrep
    return {"ok": True, "ref": doc.name.split("-")[-1], "status": status}
