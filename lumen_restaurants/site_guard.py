# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""A site runs LumenPOS or Lumen Restaurants, never both.

Lumen Restaurants carries everything LumenPOS does under the same doctype
names (LumenPOS Settings, POS Register Session and the rest), so whichever of
the two went on a site second would take those doctypes over from the first,
and every sale would run through the hooks of both. Both directions are
refused here, before anything is written. The two apps can still share a
bench: only a site has to choose.

Frappe v14 and later ask the installed apps before another app goes on a site
(before_app_install), which is how LumenPOS is refused on a Lumen Restaurants
site without any change to LumenPOS. Frappe v13 has no such hook, so there
only the first direction is guarded.
"""
import frappe

LUMENPOS = "lumenpos"

# The bench console and Frappe Cloud's install log have no language of their
# own, so each message carries both.
LUMENPOS_ON_SITE = (
    "This site runs LumenPOS. Lumen Restaurants already includes everything in"
    " LumenPOS, so a site runs one of the two. Install Lumen Restaurants on a new"
    " site, or ask Lumen Solutions to move this site to it with its data.\n"
    "هذا الموقع يعمل على LumenPOS. يتضمن Lumen Restaurants كل ما في LumenPOS،"
    " لذلك يعمل الموقع بأحدهما فقط. ثبت Lumen Restaurants على موقع جديد، أو اطلب"
    " من Lumen Solutions نقل هذا الموقع إليه مع بياناته."
)
RESTAURANTS_ON_SITE = (
    "This site runs Lumen Restaurants, which already includes everything in"
    " LumenPOS. A site runs one of the two, so LumenPOS was not installed.\n"
    "هذا الموقع يعمل على Lumen Restaurants، وهو يتضمن كل ما في LumenPOS. يعمل"
    " الموقع بأحدهما فقط، لذلك لم يتم تثبيت LumenPOS."
)


def before_install():
    """Lumen Restaurants is being installed: refuse a site that runs LumenPOS."""
    if LUMENPOS in frappe.get_installed_apps():
        # Both languages in one message: an install has no language of its own.
        frappe.throw(LUMENPOS_ON_SITE, frappe.IncompatibleApp)  # nosemgrep


def before_app_install(app_name):
    """Another app is being installed on a Lumen Restaurants site."""
    if app_name == LUMENPOS:
        frappe.throw(RESTAURANTS_ON_SITE, frappe.IncompatibleApp)  # nosemgrep
