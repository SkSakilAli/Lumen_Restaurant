# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
import frappe


def boot(bootinfo):
    """Runs on every Desk boot, ensuring custom fields and schema are up to date."""
    try:
        from lumen_restaurants.api.kitchen import _ensure_schema
        _ensure_schema()
    except Exception:
        pass
