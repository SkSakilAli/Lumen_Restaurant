# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Persistent, outlet-scoped notifications for the POS portal."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from lumen_restaurants.api import permissions

DOCTYPE = "POS Notification"
EVENT_NAME = "lumenpos_notification"

EVENTS = (
    ("kitchen_ticket_created", _("Kitchen ticket created"), _("New kitchen order"), "/kitchen"),
    ("bar_ticket_created", _("Bar ticket created"), _("New bar order"), "/bar"),
    ("ticket_preparing", _("Ticket started"), _("Ticket started"), "/kitchen"),
    ("ticket_ready", _("Ticket ready"), _("Order ready"), "/kitchen"),
    ("ticket_done", _("Ticket handed over"), _("Ticket handed over"), "/kitchen"),
    ("table_order_opened", _("Table order opened"), _("Table order opened"), "/tables"),
    ("table_order_moved", _("Table order moved"), _("Table order moved"), "/tables"),
    ("table_order_merged", _("Table orders merged"), _("Table orders merged"), "/tables"),
    ("table_order_cancelled", _("Table order cancelled"), _("Table order cancelled"), "/tables"),
    ("table_order_paid", _("Table order paid"), _("Table order paid"), "/tables"),
    ("reservation_requested", _("Online reservation requested"), _("Reservation requested"), "/reservations"),
    ("reservation_confirmed", _("Reservation confirmed"), _("Reservation confirmed"), "/reservations"),
    ("reservation_updated", _("Reservation updated"), _("Reservation updated"), "/reservations"),
    ("reservation_seated", _("Reservation seated"), _("Reservation seated"), "/reservations"),
    ("reservation_cancelled", _("Reservation cancelled"), _("Reservation cancelled"), "/reservations"),
    ("reservation_no_show", _("Reservation marked no-show"), _("Reservation marked no-show"), "/reservations"),
    ("sale_completed", _("Sale completed"), _("Sale completed"), "/history"),
    ("return_completed", _("Return completed"), _("Return completed"), "/history"),
    ("approval_requested", _("Approval requested"), _("Approval requested"), "/register"),
    ("approval_approved", _("Approval approved"), _("Approval approved"), "/register"),
    ("approval_rejected", _("Approval rejected"), _("Approval rejected"), "/register"),
    ("register_opened", _("Register opened"), _("Register opened"), "/register"),
    ("register_closed", _("Register closed"), _("Register closed"), "/register"),
    ("register_variance", _("Register variance recorded"), _("Register variance recorded"), "/register"),
    ("stock_out", _("Stock reached zero"), _("Stock reached zero"), None),
)
EVENT_BY_KEY = {
    key: {"label": label, "subject": subject, "route": route}
    for key, label, subject, route in EVENTS
}


def _can_view_outlet(user, pos_profile):
    return not pos_profile or permissions.can_use_outlet(pos_profile, user)


def _insert_for_user(
    user,
    event_type,
    subject,
    message,
    route,
    reference_doctype,
    reference_name,
    pos_profile,
):
    if not user or user == "Guest":
        return None

    doc = frappe.get_doc(
        {
            "doctype": DOCTYPE,
            "recipient": user,
            "event_type": event_type,
            "subject": subject,
            "message": message,
            "route": route,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "pos_profile": pos_profile,
        }
    )
    doc.insert(ignore_permissions=True)
    frappe.publish_realtime(
        EVENT_NAME,
        {"name": doc.name},
        user=user,
        after_commit=True,
    )
    return doc.name


def notification_settings(doc):
    """Return saved event-role rows, migrating the two original role fields in memory."""
    rows = [
        {"event_type": row.event_type, "role": row.role}
        for row in (doc.get("notification_rules") or [])
        if row.get("event_type") in EVENT_BY_KEY and row.get("role")
    ]
    configured_events = {row["event_type"] for row in rows}
    for event_type, fieldname in (
        ("kitchen_ticket_created", "kitchen_notification_role"),
        ("bar_ticket_created", "bar_notification_role"),
    ):
        role = doc.get(fieldname)
        if role and event_type not in configured_events:
            rows.append({"event_type": event_type, "role": role})
    return rows


def _configured_roles(event_type):
    settings = frappe.get_cached_doc("LumenPOS Settings")
    return list(
        dict.fromkeys(
            row["role"]
            for row in notification_settings(settings)
            if row["event_type"] == event_type
        )
    )


def notify_roles(
    roles,
    pos_profile,
    event_type,
    subject,
    message,
    route,
    reference_doctype=None,
    reference_name=None,
):
    """Create one inbox item per eligible user holding any configured role."""
    roles = list(dict.fromkeys(role for role in roles if role))
    if not roles or not pos_profile:
        return []

    users = frappe.get_all(
        "Has Role",
        filters={"role": ["in", roles], "parenttype": "User"},
        pluck="parent",
        limit_page_length=0,
    )
    users = list(dict.fromkeys(users))
    if not users:
        return []

    enabled_users = frappe.get_all(
        "User",
        filters={"name": ["in", users], "enabled": 1},
        pluck="name",
        limit_page_length=0,
    )
    names = []
    for user in enabled_users:
        if not _can_view_outlet(user, pos_profile):
            continue
        name = _insert_for_user(
            user,
            event_type,
            subject,
            message,
            route,
            reference_doctype,
            reference_name,
            pos_profile,
        )
        if name:
            names.append(name)
    return names


def notify_role(
    role,
    pos_profile,
    event_type,
    subject,
    message,
    route,
    reference_doctype=None,
    reference_name=None,
):
    """Backward-compatible single-role helper."""
    return notify_roles(
        [role],
        pos_profile,
        event_type,
        subject,
        message,
        route,
        reference_doctype,
        reference_name,
    )


def notification_event_options():
    return [{"value": key, "label": data["label"]} for key, data in EVENT_BY_KEY.items()]


def notify_event(
    event_type,
    pos_profile,
    message="",
    reference_doctype=None,
    reference_name=None,
    route=None,
):
    """Persist and publish a configured event to its role-based audience."""
    event = EVENT_BY_KEY.get(event_type)
    if not event:
        raise ValueError("Unknown POS notification event: " + str(event_type))
    return notify_roles(
        _configured_roles(event_type),
        pos_profile,
        event_type,
        event["subject"],
        message,
        route or event["route"],
        reference_doctype,
        reference_name,
    )


def has_event_recipients(event_type):
    return bool(_configured_roles(event_type))


def notify_user(
    user,
    event_type,
    subject,
    message,
    route,
    reference_doctype=None,
    reference_name=None,
    pos_profile=None,
):
    """Create an inbox item for a specific user after checking outlet access."""
    if not _can_view_outlet(user, pos_profile):
        return None
    return _insert_for_user(
        user,
        event_type,
        subject,
        message,
        route,
        reference_doctype,
        reference_name,
        pos_profile,
    )


def _configured_role(fieldname):
    if not frappe.get_meta("LumenPOS Settings").has_field(fieldname):
        return None
    return frappe.db.get_single_value("LumenPOS Settings", fieldname)


def notify_new_ticket(ticket):
    station = ticket.get("station") or "Kitchen"
    station = "Bar" if station == "Bar" else "Kitchen"
    order = (
        "#" + str(ticket.order_no)
        if ticket.get("order_no")
        else (ticket.get("table_label") or _("Table order"))
    )
    notify_event(
        event_type="bar_ticket_created" if station == "Bar" else "kitchen_ticket_created",
        pos_profile=ticket.pos_profile,
        message=order,
        reference_doctype="POS Kitchen Ticket",
        reference_name=ticket.name,
        route="/bar" if station == "Bar" else "/kitchen",
    )


def notify_ticket_status(ticket, status):
    event_type = {
        "Preparing": "ticket_preparing",
        "Ready": "ticket_ready",
        "Done": "ticket_done",
    }.get(status)
    if not event_type:
        return
    station = "Bar" if ticket.get("station") == "Bar" else "Kitchen"
    order = (
        "#" + str(ticket.order_no)
        if ticket.get("order_no")
        else (ticket.get("table_label") or _("Order"))
    )
    notify_event(
        event_type=event_type,
        pos_profile=ticket.pos_profile,
        message=order,
        route="/bar" if station == "Bar" else "/kitchen",
        reference_doctype="POS Kitchen Ticket",
        reference_name=ticket.name,
    )


@frappe.whitelist()
def list_notifications(limit=50):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Log in to view notifications."), frappe.PermissionError)

    limit = min(max(cint(limit) or 50, 1), 100)
    fields = [
        "name",
        "event_type",
        "subject",
        "message",
        "route",
        "reference_name",
        "pos_profile",
        "read_at",
        "creation",
    ]
    rows = frappe.get_all(
        DOCTYPE,
        filters={"recipient": user},
        fields=fields,
        order_by="creation desc",
        limit_page_length=limit,
    )
    unread = frappe.get_all(
        DOCTYPE,
        filters={"recipient": user, "read_at": ["is", "not set"]},
        fields=["pos_profile"],
        limit_page_length=0,
    )

    allowed = {}

    def visible(row):
        profile = row.get("pos_profile")
        if profile not in allowed:
            allowed[profile] = _can_view_outlet(user, profile)
        return allowed[profile]

    return {
        "items": [row for row in rows if visible(row)],
        "unread_count": sum(1 for row in unread if visible(row)),
    }


@frappe.whitelist()
def mark_read(name: str):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Log in to update notifications."), frappe.PermissionError)

    row = frappe.db.get_value(
        DOCTYPE,
        {"name": name, "recipient": user},
        ["pos_profile", "read_at"],
        as_dict=True,
    )
    if not row or not _can_view_outlet(user, row.pos_profile):
        frappe.throw(_("Notification not found."), frappe.PermissionError)
    if not row.read_at:
        frappe.db.set_value(DOCTYPE, name, "read_at", now_datetime(), update_modified=False)
    return {"name": name, "read_at": row.read_at or now_datetime()}
