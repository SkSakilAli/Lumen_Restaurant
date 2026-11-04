# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
app_name = "lumen_restaurants"
app_title = "Lumen Restaurants"
app_publisher = "Lumen Solutions"
app_description = "The restaurant till for ERPNext, on the full LumenPOS point of sale: tables and a floor plan, a kitchen screen, order numbers, bookings and a public booking page"
app_email = "hello@lumen-solutions.co"
app_license = "AGPL-3.0-only"

required_apps = ["erpnext"]

# Frappe's apps screen (/apps, Frappe 15 and 16) and the Frappe 16 desk list an
# app only when it declares itself here. Shown to whoever may open the till.
# The Frappe 16 desk tile and sidebar are the files in desktop_icon/ and
# workspace_sidebar/, which Frappe 16 imports on every migrate.
# Lumen Restaurants: our own tile, logo and files (the owner, 2026-10-17), made
# from LumenPOS's by scripts/desk_files_from_lumenpos.mjs.
add_to_apps_screen = [
    {
        "name": app_name,
        "logo": "/assets/lumen_restaurants/pos/pwa-192.png",
        "title": app_title,
        "route": "/pos",
        "has_permission": "lumen_restaurants.api.session.can_open_till",
    }
]

# Lumen Restaurants: a site runs LumenPOS or Lumen Restaurants, never both
# (they share doctype names). Both directions are refused before anything is
# written, see site_guard.py.
extend_bootinfo = "lumen_restaurants.boot.boot"
before_install = "lumen_restaurants.site_guard.before_install"
before_app_install = "lumen_restaurants.site_guard.before_app_install"

after_install = [
    "lumen_restaurants.install.after_install",
    # Lumen Restaurants: the add-on fields (modifiers.py) and the floor plan's
    # switch (floor.py).
    "lumen_restaurants.modifiers.ensure_setup",
    "lumen_restaurants.floor.ensure_setup",
    # A restaurant site starts with one shift per outlet (restaurant_defaults.py).
    "lumen_restaurants.restaurant_defaults.after_install",
]
# Runs on every app update (Frappe Cloud deploy), keeps the LumenPOS roles and
# custom fields in place on existing sites without shell access.
after_migrate = [
    "lumen_restaurants.install.ensure_setup",
    "lumen_restaurants.modifiers.ensure_setup",
    "lumen_restaurants.floor.ensure_setup",
]

# Self-healer: re-drive any register shift stuck in "Closing" (a consolidation
# that timed out or failed) toward "Closed", serialized so it never collides
# with a live close. This is the backstop that guarantees no shift is ever left
# half-closed for the next cashier to stumble into.
scheduler_events = {
    "cron": {
        "*/10 * * * *": [
            "lumen_restaurants.api.register.reconcile_stuck_closings",
        ],
        # Forgotten-shift alert. Hourly is enough, it emails once per shift
        # (de-duped by the session's overdue_notified flag) and never closes a
        # till, so it can't race anything.
        "0 * * * *": [
            "lumen_restaurants.api.register.notify_overdue_sessions",
        ],
        # Cashback, once a day and in this order: write off what expired, then
        # book the days that have ended to the accounts (one summary Journal
        # Entry per company, day and outlet cost center). One job so the two
        # steps can never run out of order.
        "30 0 * * *": [
            "lumen_restaurants.cashback.nightly",
        ],
        # Customer balances spent across companies of a group: yesterday's
        # lines booked as Inter Company Journal Entry pairs (one per day, pair
        # of companies and kind of balance).
        "45 0 * * *": [
            "lumen_restaurants.inter_company.nightly",
        ],
        # Other currencies set to Automatic: the day's published rate, less the
        # shop's margin, saved as ERPNext Currency Exchange.
        "15 0 * * *": [
            "lumen_restaurants.currency.daily_rates",
        ],
    },
}

# Demo builder only (lumen_restaurants/demo_data.py). Dates the documents of a demo
# history through Frappe's own hook instead of patching the framework at
# runtime. It returns at once unless a demo run has set
# frappe.flags.lumenpos_demo_stamp, so a real sale is never touched.
doc_events = {
    "POS Invoice": {
        "before_insert": "lumen_restaurants.demo_data.apply_demo_stamp",
        # ERPNext 16 leaves loyalty points owing on a POS Invoice (see there).
        "before_submit": "lumen_restaurants.erpnext_compat.settle_points_outstanding",
        "on_submit": "lumen_restaurants.api.bar.on_invoice_submit",
    },
    "Sales Invoice": {
        "before_insert": "lumen_restaurants.demo_data.apply_demo_stamp",
        "on_submit": "lumen_restaurants.api.bar.on_invoice_submit",
    },
    "Stock Entry": {"before_insert": "lumen_restaurants.demo_data.apply_demo_stamp"},
    "POS Opening Entry": {"before_insert": "lumen_restaurants.demo_data.apply_demo_stamp"},
    "POS Closing Entry": {"before_insert": "lumen_restaurants.demo_data.apply_demo_stamp"},
    "Payment Entry": {"before_insert": "lumen_restaurants.demo_data.apply_demo_stamp"},
}

# The till's service worker has to come from the site ROOT to be allowed to
# control /pos, and Frappe never serves a .js file from an app's www folder.
# This renderer answers /sw.js and nothing else (see lumen_restaurants/service_worker.py).
# v13 has no page_renderer hook, so the till there stays online-only.
page_renderer = ["lumen_restaurants.service_worker.ServiceWorkerPage"]

# The POS single-page app is served at /pos (see lumen_restaurants/www/pos.py).
# All sub-paths resolve to the same page; the frontend uses a hash router.
website_route_rules = [
    {"from_route": "/pos/<path:app_path>", "to_route": "pos"},
    # The public booking page: /book/<outlet> is the link a restaurant puts on
    # its social media. Guests only ever see it for outlets that opted in.
    {"from_route": "/book/<outlet>", "to_route": "book"},
]
