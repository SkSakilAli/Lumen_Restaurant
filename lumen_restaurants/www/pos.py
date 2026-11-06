# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/pos"
        raise frappe.Redirect
    context.csrf_token = frappe.sessions.get_csrf_token()
    from lumen_restaurants import __version__
    context.lumenpos_version = __version__
    frappe_major = int(str(getattr(frappe, "__version__", "13")).split(".", 1)[0])
    context.socketio_site = frappe.local.site if frappe_major >= 15 else ""
    context.socketio_port = int(frappe.conf.get("socketio_port") or (9000 if frappe_major >= 15 else 3000))
    context.socketio_dev = bool(frappe.conf.get("developer_mode"))
    return context
