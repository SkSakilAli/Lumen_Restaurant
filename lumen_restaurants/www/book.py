# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""The public booking page, /book/<outlet>.

The link a restaurant puts on its social media, so it has to look like the
restaurant, not like us: every word, colour, font, background, question and
package on it comes from the outlet's POS Booking Page, designed in the till.
This file only hands that design to the page, which draws itself from it.

Guests see a page only while it is published. ?preview=1 shows the saved (or
the designer's live) design to a signed-in user who may read booking pages,
published or not, and a preview never submits anything.
"""

import json

import frappe
from frappe.utils import now_datetime

no_cache = 1


def get_context(context):
    from lumen_restaurants.api import booking_page, reservations

    outlet = frappe.form_dict.get("outlet") or ""
    # A preview shows the page as it is being designed, to whoever may read it.
    preview = frappe.form_dict.get("preview") in ("1", "true") and frappe.session.user != "Guest"
    if preview:
        preview = frappe.has_permission("POS Booking Page", "read")
    page = None
    if outlet and frappe.db.exists("POS Profile", outlet):
        page = booking_page.load(outlet) if preview else reservations._page(outlet)

    data = booking_page.serialize(page) if page else {}
    context.available = bool(page)
    context.preview = 1 if preview else 0
    context.outlet = outlet
    context.title = (data.get("title") or data.get("company") or "Booking") if page else "Booking"
    # Embedded in a <script>: a "</" in any text the owner typed must not be
    # able to close the tag.
    context.page_json = json.dumps(data, default=str, ensure_ascii=False).replace("</", "<\\/")
    # The branch's clock, not the phone's: the page works out its days and
    # times from it, so a visitor in another time zone or a phone set wrong
    # still sees only what the branch can take.
    context.site_now = now_datetime().strftime("%Y-%m-%dT%H:%M:%S")
    try:
        context.csrf_token = frappe.sessions.get_csrf_token()
    except Exception:
        # Rendered outside a request (a test, a pre-render): no session object
        # to take a token from, and nothing will be posted from this render.
        context.csrf_token = ""
    return context
