# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Our mark and name at the foot of every receipt the till gives out.

He wants them on every receipt, with no way for a customer to take them off
(2026-09-27: "خلي شعارنا واسمنا اللي تحت دائما موجودة ما يقدر العميل يشيلها
ابدا"), so there is no setting for them, on purpose. The built-in receipt
(ReceiptView.vue) and the receipt printer (receipt_images.py) draw them
themselves. This module adds them where the page comes from an outlet's own
Print Format (the POS Profile's): the till's print and the emailed receipt.
ERPNext's own screens, and its desk print of an invoice, stay ERPNext's.
"""
from __future__ import annotations

import base64
from functools import lru_cache

import frappe

# The kit's receipt cut: pure black, 96 dots, printed 12 mm wide.
MARK_FILE = ("public", "images", "png", "receipt-96px-203dpi.png")


@lru_cache(maxsize=1)
def mark_html():
    # Our own packaged picture, a fixed path inside the app.
    with open(frappe.get_app_path("lumen_restaurants", *MARK_FILE), "rb") as f:  # nosemgrep
        png = base64.b64encode(f.read()).decode()
    return (
        '<div class="lumen-restaurants-mark" style="text-align:center;margin:14px 0 4px;'
        'font:10px/1.4 Arial,sans-serif;color:#000;page-break-inside:avoid">'
        f'<img src="data:image/png;base64,{png}" alt="" '
        'style="width:12mm;height:12mm;display:block;margin:0 auto 2px">'
        "Lumen Restaurants</div>"
    )


def owed_html(doc):
    """A sale on account (LumenPOS 0.60.0): what stays owed, on this sale and in
    all, and a line for the customer to sign, as the till's own receipt and the
    receipt printer show them. Nothing for any other sale, or a return."""
    from frappe.utils import escape_html, fmt_money

    from lumen_restaurants import credit_sales

    if doc.get("is_return"):
        return ""
    try:
        facts = credit_sales.receipt_facts(doc)
    except Exception:
        return ""
    if not facts:
        return ""
    rows = [(frappe._("Owed on this sale"), fmt_money(facts.get("owed_on_sale"), currency=doc.currency))]
    if facts.get("owed_total") is not None:
        currency = frappe.get_cached_value("Company", doc.company, "default_currency")
        rows.append((frappe._("Owed in all"), fmt_money(facts["owed_total"], currency=currency)))
    cells = "".join(
        f'<tr><td>{escape_html(label)}</td><td style="text-align:end;white-space:nowrap">{escape_html(value)}</td></tr>'
        for label, value in rows
    )
    return (
        '<div class="lumen-restaurants-owed" style="margin:12px 0 0;font:12px/1.5 Arial,sans-serif;'
        'color:#000;page-break-inside:avoid">'
        f'<table style="width:100%;border-collapse:collapse;font-weight:bold">{cells}</table>'
        '<div style="margin-top:26px;padding-top:4px;border-top:1px solid #000;width:70%">'
        f'{escape_html(frappe._("Customer signature"))}</div></div>'
    )


def with_mark(html, before=""):
    """The page with our mark added just before </body>, or at its end, and
    `before` it (what a sale on account still owes)."""
    html = html or ""
    foot = (before or "") + mark_html()
    at = html.lower().rfind("</body>")
    return html + foot if at < 0 else html[:at] + foot + html[at:]


@frappe.whitelist()
def print_html(invoice: str):
    """A sale in its outlet's own Print Format, our mark at the foot, for the
    till to print (it used to open /printview, where the mark was missing)."""
    from lumen_restaurants.api.sales import _doctype_of

    doctype = _doctype_of(invoice)
    if not doctype:
        frappe.throw(frappe._("Sale {0} not found").format(invoice))
    doc = frappe.get_doc(doctype, invoice)
    doc.check_permission("print")
    print_format = frappe.db.get_value("POS Profile", doc.get("pos_profile"), "print_format")
    return with_mark(
        frappe.get_print(doctype, invoice, print_format=print_format or None, doc=doc, no_letterhead=0),
        before=owed_html(doc),
    )


def attach_with_mark(doctype, name, doc, print_format=None):
    """frappe.attach_print, the same attachment an emailed receipt always had,
    with our mark at the foot."""
    from frappe.utils import scrub_urls

    frappe.local.flags.ignore_print_permissions = True
    try:
        html = with_mark(frappe.get_print(doctype, name, print_format=print_format, doc=doc), before=owed_html(doc))
    finally:
        frappe.local.flags.ignore_print_permissions = False
    return frappe.attach_print(doctype, name, print_format=print_format, doc=doc, html=scrub_urls(html))
