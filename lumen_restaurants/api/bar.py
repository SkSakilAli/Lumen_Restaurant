# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
"""Beverage Inventory & Pour Management (The Bar Module).

Handles cocktail recipes (Beverage BOM), draft beer keg/tap tracking, live pour
depletions, and bar floor spillage/breakage logging.
"""

from __future__ import annotations

import json
import re
import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime, nowdate

RECIPE = "POS Bar Recipe"
RECIPE_ING = "POS Bar Recipe Ingredient"
TAP = "POS Bar Tap"
SPILLAGE = "POS Bar Spillage"
SPILLAGE_ITEM = "POS Bar Spillage Item"


def _ensure_schema():
    """No-op schema check (tables and DocTypes are registered in MySQL)."""
    pass


@frappe.whitelist()
def get_bar_dashboard(pos_profile: str | None = None) -> dict:
    """Return live metrics and taps for the Bar view."""
    try:
        taps = frappe.db.sql("""
            SELECT name, tap_number, station, status, keg_item, item_name, capacity_liters, remaining_liters, unit, last_cleaned, tapped_at
            FROM `tabPOS Bar Tap`
            ORDER BY tap_number ASC
        """, as_dict=True)
    except Exception:
        taps = []

    for t in taps:
        t["unit"] = t.get("unit") or "ml"
        cap = flt(t.get("capacity_liters")) or (1000.0 if t["unit"] == "ml" else 50.0)
        rem = flt(t.get("remaining_liters")) or 0.0
        t["percent"] = round((rem / cap) * 100, 1) if cap > 0 else 0

    # Today's spillage
    try:
        spill_stats = frappe.db.sql("""
            SELECT COUNT(name) as count, COALESCE(SUM(total_cost), 0) as total_cost
            FROM `tabPOS Bar Spillage`
            WHERE DATE(creation) = %s
        """, (nowdate(),), as_dict=True)
        today_spill = spill_stats[0] if spill_stats else {"count": 0, "total_cost": 0.0}
    except Exception:
        today_spill = {"count": 0, "total_cost": 0.0}

    # Count of active recipes
    try:
        rc = frappe.db.sql("SELECT COUNT(*) FROM `tabPOS Bar Recipe` WHERE is_active = 1")
        recipes_count = rc[0][0] if rc else 0
    except Exception:
        recipes_count = 0

    return {
        "taps": taps,
        "recipes_count": recipes_count,
        "spillage_today": {
            "count": cint(today_spill.get("count")),
            "total_cost": flt(today_spill.get("total_cost")),
        },
        "low_taps": [t for t in taps if t["percent"] <= 15 and t["status"] != "Empty"],
    }


@frappe.whitelist()
def list_taps(pos_profile: str | None = None) -> list[dict]:
    """List all draft taps and keg status."""
    try:
        taps = frappe.db.sql("""
            SELECT name, tap_number, station, status, keg_item, item_name, capacity_liters, remaining_liters, unit, last_cleaned, tapped_at
            FROM `tabPOS Bar Tap`
            ORDER BY tap_number ASC
        """, as_dict=True)
    except Exception:
        taps = []

    for t in taps:
        t["unit"] = t.get("unit") or "ml"
        cap = flt(t.get("capacity_liters")) or (1000.0 if t["unit"] == "ml" else 50.0)
        rem = flt(t.get("remaining_liters")) or 0.0
        t["percent"] = round((rem / cap) * 100, 1) if cap > 0 else 0
    return taps


@frappe.whitelist()
def save_tap(payload: dict | str) -> dict:
    """Create or update a draft tap."""
    if isinstance(payload, str):
        payload = json.loads(payload)

    name = payload.get("name")
    tap_number = (payload.get("tap_number") or "").strip()
    if not tap_number:
        frappe.throw(_("Tap Number is required"))

    station = payload.get("station") or "Main Bar"
    keg_item = payload.get("keg_item") or ""
    item_name = payload.get("item_name") or keg_item
    unit = (payload.get("unit") or "ml").strip()
    capacity = flt(payload.get("capacity_liters")) or (1000.0 if unit == "ml" else 50.0)
    status = payload.get("status") or "Active"
    now_str = str(now_datetime())

    if payload.get("action") == "tap_new_keg":
        remaining = capacity
        status = "Active"
        tapped_at = now_str
    else:
        remaining = flt(payload.get("remaining_liters"))
        tapped_at = payload.get("tapped_at") or now_str

    if name:
        frappe.db.sql("""
            UPDATE `tabPOS Bar Tap`
            SET tap_number=%s, station=%s, status=%s, keg_item=%s, item_name=%s,
                capacity_liters=%s, remaining_liters=%s, unit=%s, tapped_at=%s, modified=%s
            WHERE name=%s
        """, (tap_number, station, status, keg_item, item_name, capacity, remaining, unit, tapped_at, now_str, name))
    else:
        new_name = "TAP-" + frappe.generate_hash(length=8).upper()
        frappe.db.sql("""
            INSERT INTO `tabPOS Bar Tap`
            (name, tap_number, station, status, keg_item, item_name, capacity_liters, remaining_liters, unit, tapped_at, creation, modified, modified_by, owner)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Administrator', 'Administrator')
        """, (new_name, tap_number, station, status, keg_item, item_name, capacity, remaining, unit, tapped_at, now_str, now_str))

    frappe.db.commit()
    return {"status": "ok", "tap_number": tap_number}


@frappe.whitelist()
def list_recipes(category: str | None = None, search: str | None = None) -> list[dict]:
    """List drink recipes with ingredients."""
    try:
        query = "SELECT name, item_code, recipe_name, category, glassware, serving_size_ml, cost, prep_instructions FROM `tabPOS Bar Recipe` WHERE is_active = 1"
        params = []
        if category and category != "All":
            query += " AND category = %s"
            params.append(category)
        query += " ORDER BY recipe_name ASC"

        recipes = frappe.db.sql(query, params, as_dict=True)
    except Exception:
        recipes = []

    if search:
        s = search.lower().strip()
        recipes = [r for r in recipes if s in (r.get("recipe_name") or "").lower() or s in (r.get("item_code") or "").lower()]

    for r in recipes:
        try:
            r["ingredients"] = frappe.db.sql("""
                SELECT ingredient_item, ingredient_name, pour_qty, pour_uom, is_primary_spirit, cost
                FROM `tabPOS Bar Recipe Ingredient`
                WHERE parent = %s
                ORDER BY idx ASC
            """, (r["name"],), as_dict=True)
        except Exception:
            r["ingredients"] = []

    return recipes


@frappe.whitelist()
def get_recipe(item_code: str | None = None, recipe_name: str | None = None) -> dict | None:
    """Fetch recipe card by item_code or recipe_name for quick bartender lookup."""
    target = (item_code or recipe_name or "").strip()
    if not target:
        return None
    try:
        recs = frappe.db.sql("""
            SELECT name, item_code, recipe_name, category, glassware, serving_size_ml, cost, prep_instructions
            FROM `tabPOS Bar Recipe`
            WHERE (item_code = %s OR recipe_name = %s) AND is_active = 1
            LIMIT 1
        """, (target, target), as_dict=True)
        if not recs:
            return None
        data = recs[0]
        data["ingredients"] = frappe.db.sql("""
            SELECT ingredient_item, ingredient_name, pour_qty, pour_uom, is_primary_spirit, cost
            FROM `tabPOS Bar Recipe Ingredient`
            WHERE parent = %s
            ORDER BY idx ASC
        """, (data["name"],), as_dict=True)
        return data
    except Exception:
        return None


@frappe.whitelist()
def save_recipe(payload: dict | str) -> dict:
    """Create or update a drink recipe (BOM)."""
    if isinstance(payload, str):
        payload = json.loads(payload)

    item_code = payload.get("item_code") or payload.get("recipe_name")
    if not item_code:
        frappe.throw(_("Beverage Item or Recipe Name is required"))

    recipe_name = payload.get("recipe_name") or item_code
    category = payload.get("category") or "Cocktail"
    glassware = payload.get("glassware") or "Rocks Glass"
    serving_size_ml = flt(payload.get("serving_size_ml"))
    prep = payload.get("prep_instructions") or ""
    now_str = str(now_datetime())

    # Check if exists by name or item_code
    name = payload.get("name")
    existing = None
    if name:
        existing = frappe.db.sql("SELECT name FROM `tabPOS Bar Recipe` WHERE name = %s", (name,))
    if not existing:
        existing = frappe.db.sql("SELECT name FROM `tabPOS Bar Recipe` WHERE item_code = %s", (item_code,))

    if existing:
        name = existing[0][0]
        frappe.db.sql("""
            UPDATE `tabPOS Bar Recipe`
            SET item_code=%s, recipe_name=%s, category=%s, glassware=%s, serving_size_ml=%s, prep_instructions=%s, modified=%s
            WHERE name=%s
        """, (item_code, recipe_name, category, glassware, serving_size_ml, prep, now_str, name))
        frappe.db.sql("DELETE FROM `tabPOS Bar Recipe Ingredient` WHERE parent = %s", (name,))
    else:
        name = "BREC-" + frappe.generate_hash(length=8).upper()
        frappe.db.sql("""
            INSERT INTO `tabPOS Bar Recipe`
            (name, item_code, recipe_name, category, glassware, serving_size_ml, prep_instructions, creation, modified, modified_by, owner)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Administrator', 'Administrator')
        """, (name, item_code, recipe_name, category, glassware, serving_size_ml, prep, now_str, now_str))

    for idx, ing in enumerate(payload.get("ingredients") or []):
        ing_item = ing.get("ingredient_item") or ing.get("ingredient_name") or "Ingredient"
        ing_name = ing.get("ingredient_name") or ing_item
        row_name = "BING-" + frappe.generate_hash(length=8).upper()
        frappe.db.sql("""
            INSERT INTO `tabPOS Bar Recipe Ingredient`
            (name, parent, parentfield, parenttype, idx, ingredient_item, ingredient_name, pour_qty, pour_uom, is_primary_spirit, cost, creation, modified, modified_by, owner)
            VALUES (%s, %s, 'ingredients', 'POS Bar Recipe', %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Administrator', 'Administrator')
        """, (
            row_name, name, idx,
            ing_item, ing_name,
            flt(ing.get("pour_qty")), ing.get("pour_uom") or "ml",
            1 if ing.get("is_primary_spirit") else 0, flt(ing.get("cost")),
            now_str, now_str
        ))

    frappe.db.commit()
    return {"status": "ok", "name": name}


@frappe.whitelist()
def delete_recipe(name: str) -> dict:
    """Delete a drink recipe and ingredients."""
    if not name:
        return {"status": "error"}
    frappe.db.sql("DELETE FROM `tabPOS Bar Recipe Ingredient` WHERE parent = %s", (name,))
    frappe.db.sql("DELETE FROM `tabPOS Bar Recipe` WHERE name = %s", (name,))
    frappe.db.commit()
    return {"status": "ok", "name": name}


@frappe.whitelist()
def get_beverage_items() -> list[dict]:
    """Return items from Item master for recipe selection."""
    try:
        items = frappe.db.sql("""
            SELECT item_code, item_name, item_group, stock_uom
            FROM `tabItem`
            ORDER BY item_name ASC
            LIMIT 250
        """, as_dict=True)
        return items
    except Exception:
        return []


@frappe.whitelist()
def log_spillage(payload: dict | str) -> dict:
    """Log spillage/wastage from the bar screen."""
    if isinstance(payload, str):
        payload = json.loads(payload)

    reason = payload.get("reason") or "Bad Pour / Foam Loss"
    notes = payload.get("notes") or ""
    pos_profile = payload.get("pos_profile")
    warehouse = payload.get("warehouse")
    bartender = frappe.session.user
    now_str = str(now_datetime())

    items = payload.get("items") or []
    if not items:
        frappe.throw(_("At least one item is required to log spillage."))

    spill_name = "BSPIL-" + frappe.generate_hash(length=8).upper()
    total_cost = 0.0

    for idx, row in enumerate(items):
        item_code = row.get("item_code")
        item_name = row.get("item_name") or item_code
        qty = flt(row.get("qty")) or 1.0
        uom = row.get("uom") or "Nos"
        rate = flt(row.get("rate"))
        amount = qty * rate
        total_cost += amount

        row_name = "BSPI-" + frappe.generate_hash(length=8).upper()
        frappe.db.sql("""
            INSERT INTO `tabPOS Bar Spillage Item`
            (name, parent, parentfield, parenttype, idx, item_code, item_name, qty, uom, rate, amount, creation, modified, modified_by, owner)
            VALUES (%s, %s, 'items', 'POS Bar Spillage', %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Administrator', 'Administrator')
        """, (row_name, spill_name, idx, item_code, item_name, qty, uom, rate, amount, now_str, now_str))

    frappe.db.sql("""
        INSERT INTO `tabPOS Bar Spillage`
        (name, pos_profile, warehouse, reason, bartender, total_cost, notes, creation, modified, modified_by, owner)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Administrator', 'Administrator')
    """, (spill_name, pos_profile, warehouse, reason, bartender, total_cost, notes, now_str, now_str))

    frappe.db.commit()
    return {"status": "ok", "name": spill_name}


@frappe.whitelist()
def list_spillages(pos_profile: str | None = None, limit: int = 20) -> list[dict]:
    """Return recent spillage events."""
    try:
        records = frappe.db.sql("""
            SELECT name, creation, reason, bartender, total_cost, stock_entry, notes
            FROM `tabPOS Bar Spillage`
            ORDER BY creation DESC
            LIMIT %s
        """, (cint(limit) or 20,), as_dict=True)
    except Exception:
        records = []

    for r in records:
        try:
            r["items"] = frappe.db.sql("""
                SELECT item_code, item_name, qty, uom, rate, amount
                FROM `tabPOS Bar Spillage Item`
                WHERE parent = %s
            """, (r["name"],), as_dict=True)
        except Exception:
            r["items"] = []

    return records


def get_pour_volume_ml(item_code: str | None, item_name: str | None = None) -> float:
    """Return pour volume in milliliters for an item, checking recipe first, then ml regex, then defaults."""
    # 1. Check Recipe
    if item_code or item_name:
        try:
            res = frappe.db.sql("""
                SELECT serving_size_ml FROM `tabPOS Bar Recipe`
                WHERE (item_code = %s OR recipe_name = %s) AND is_active = 1
                LIMIT 1
            """, (item_code or "", item_name or ""), as_dict=True)
            if res and flt(res[0].get("serving_size_ml")) > 0:
                return flt(res[0]["serving_size_ml"])
        except Exception:
            pass

    # 2. Check ml pattern in item name or item code (e.g., '30 ML Wine', '60ml', '330ml', '750ml')
    combined = f"{item_name or ''} {item_code or ''}"
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:ml|milliliter|milli)\b', combined, re.IGNORECASE)
    if m:
        try:
            ml_val = float(m.group(1))
            if ml_val > 0:
                return ml_val
        except Exception:
            pass

    # 3. Default based on item category or keywords: beer pint = 500ml, wine/spirits = 30ml
    if re.search(r'\b(beer|ale|lager|cider|draught|draft|pint|keg|stout|ipa)\b', combined, re.IGNORECASE):
        return 500.0
    if re.search(r'\b(wine|peg|shot|liquor|whisky|whiskey|vodka|rum|gin|tequila)\b', combined, re.IGNORECASE):
        return 30.0

    # Default fallback: 30ml standard pour
    return 30.0


# Backward compatibility alias
def get_pour_volume_liters(item_code: str | None, item_name: str | None = None) -> float:
    return get_pour_volume_ml(item_code, item_name) / 1000.0


def _uom_to_ml(qty: float, uom: str | None) -> float:
    """Convert ingredient pour quantity to milliliters."""
    u = (uom or "ml").lower().strip()
    qty = flt(qty)
    if u in ("ml", "milliliter", "milliliters"):
        return qty
    if u in ("cl", "centiliter", "centiliters"):
        return qty * 10.0
    if u in ("oz", "fl oz", "ounce", "ounces"):
        return qty * 29.5735
    if u in ("l", "liter", "liters", "litre", "litres"):
        return qty * 1000.0
    if u in ("dash", "dashes"):
        return qty * 1.0
    return qty if qty > 1 else qty * 1000.0


def deplete_bar_items(items: list[dict], source_ref: str | None = None) -> list[dict]:
    """Deduct dispensed beverage volumes from active taps.
    
    Safe & resilient: supports both milliliter (ml - default for liquor) and liter (L) tap lines.
    Called when:
    - Tickets are marked "Handed over" at the bar
    - Direct invoices without tickets are submitted (on_invoice_submit)
    """
    if not items:
        return []

    depletions = []
    try:
        now_str = str(now_datetime())
        for it in items:
            item_code = (it.get("item_code") or "").strip()
            item_name = (it.get("item_name") or item_code or "").strip()
            qty = flt(it.get("qty")) or 1.0
            if qty <= 0 or (not item_code and not item_name):
                continue

            # 1. Check direct tap match (tap is assigned directly to the sold item)
            direct_or = []
            params = []
            if item_code:
                direct_or.append("keg_item = %s")
                params.append(item_code)
                direct_or.append("item_name = %s")
                params.append(item_code)
            if item_name and item_name != item_code:
                direct_or.append("keg_item = %s")
                params.append(item_name)
                direct_or.append("item_name = %s")
                params.append(item_name)

            taps = []
            if direct_or:
                taps = frappe.db.sql(f"""
                    SELECT name, tap_number, capacity_liters, remaining_liters, unit, keg_item, item_name
                    FROM `tabPOS Bar Tap`
                    WHERE status IN ('Active', 'Kicking Soon') AND ({' OR '.join(direct_or)})
                    ORDER BY tap_number ASC
                """, params, as_dict=True)

            if taps:
                pour_ml = get_pour_volume_ml(item_code, item_name)
                for tap in taps:
                    unit = (tap.get("unit") or "ml").strip().lower()
                    if unit in ("l", "liter", "litres"):
                        total_pour = round((pour_ml / 1000.0) * qty, 4)
                    else:
                        total_pour = round(pour_ml * qty, 1)

                    rem = flt(tap.get("remaining_liters"))
                    cap = flt(tap.get("capacity_liters")) or (1000.0 if unit == "ml" else 50.0)
                    new_rem = max(0.0, rem - total_pour)
                    pct = round((new_rem / cap) * 100, 1) if cap > 0 else 0

                    status = "Active"
                    if new_rem <= 0:
                        status = "Empty"
                    elif pct <= 15:
                        status = "Kicking Soon"

                    frappe.db.sql("""
                        UPDATE `tabPOS Bar Tap`
                        SET remaining_liters = %s, status = %s, modified = %s
                        WHERE name = %s
                    """, (new_rem, status, now_str, tap["name"]))

                    depletions.append({
                        "tap": tap["name"],
                        "tap_number": tap["tap_number"],
                        "item_code": item_code,
                        "pour_qty": total_pour,
                        "unit": tap.get("unit") or "ml",
                        "remaining_liters": new_rem,
                        "status": status,
                        "source": source_ref,
                    })

            else:
                # 2. Check recipe ingredients linked to taps (e.g. keg item mapped as ingredient)
                ing_taps = frappe.db.sql("""
                    SELECT t.name, t.tap_number, t.capacity_liters, t.remaining_liters, t.unit, t.status,
                           ing.ingredient_item, ing.pour_qty, ing.pour_uom
                    FROM `tabPOS Bar Tap` t
                    INNER JOIN `tabPOS Bar Recipe Ingredient` ing
                      ON (ing.ingredient_item = t.keg_item OR ing.ingredient_name = t.keg_item)
                    INNER JOIN `tabPOS Bar Recipe` r ON r.name = ing.parent
                    WHERE (r.item_code = %s OR r.recipe_name = %s)
                      AND t.status IN ('Active', 'Kicking Soon')
                """, (item_code or item_name, item_name or item_code), as_dict=True)

                for itap in ing_taps:
                    unit = (itap.get("unit") or "ml").strip().lower()
                    each_ml = _uom_to_ml(itap.get("pour_qty"), itap.get("pour_uom"))
                    if unit in ("l", "liter", "litres"):
                        total_pour = round((each_ml / 1000.0) * qty, 4)
                    else:
                        total_pour = round(each_ml * qty, 1)

                    rem = flt(itap.get("remaining_liters"))
                    cap = flt(itap.get("capacity_liters")) or (1000.0 if unit == "ml" else 50.0)
                    new_rem = max(0.0, rem - total_pour)
                    pct = round((new_rem / cap) * 100, 1) if cap > 0 else 0

                    status = "Active"
                    if new_rem <= 0:
                        status = "Empty"
                    elif pct <= 15:
                        status = "Kicking Soon"

                    frappe.db.sql("""
                        UPDATE `tabPOS Bar Tap`
                        SET remaining_liters = %s, status = %s, modified = %s
                        WHERE name = %s
                    """, (new_rem, status, now_str, itap["name"]))

                    depletions.append({
                        "tap": itap["name"],
                        "tap_number": itap["tap_number"],
                        "item_code": item_code,
                        "ingredient": itap.get("ingredient_item"),
                        "pour_qty": total_pour,
                        "unit": itap.get("unit") or "ml",
                        "remaining_liters": new_rem,
                        "status": status,
                        "source": source_ref,
                    })

        if depletions:
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(title="deplete_bar_items failed", message=str(e))

    return depletions


@frappe.whitelist()
def test_reports():
    """Verify that reports are loaded and can execute query report run."""
    import frappe.desk.query_report
    checks = {}
    reports = [
        "Liquor Stock Movement",
        "Peg-wise Sales Summary",
        "Bar Stock Reconciliation"
    ]
    test_filters = {"from_date": "2026-10-01", "to_date": "2026-11-03"}
    for rep_name in reports:
        try:
            r = frappe.desk.query_report.run(rep_name, filters=test_filters)
            checks[rep_name] = {
                "status": "OK",
                "columns": [c.get("label") for c in r.get("columns", [])],
                "rows_count": len(r.get("result", []))
            }
        except Exception as e:
            checks[rep_name] = {"status": "Error", "error": str(e)}

    return checks


@frappe.whitelist()
def sync_bar_reports():
    """Register and sync bar reports into tabReport."""
    results = {}
    reports = [
        "liquor_stock_movement",
        "peg_wise_sales_summary",
        "bar_stock_reconciliation"
    ]
    for rep in reports:
        try:
            frappe.reload_doc("lumen_restaurants", "report", rep, force=True)
            results[rep] = "Success"
        except Exception as e:
            results[rep] = f"Error: {e}"

    frappe.db.commit()
    frappe.clear_cache()
    return results


def on_invoice_submit(doc, method=None):
    """Event hook: triggered safely on POS Invoice or Sales Invoice submit."""
    try:
        # 1. Skip if this is a restaurant sale (handled by send_to_kitchen or kitchen.after_sale)
        if getattr(doc.flags, "lumenpos_has_order", False) or getattr(doc.flags, "lumenpos_is_takeaway", False):
            return

        # 2. Skip if this invoice already had a bar ticket created
        has_ticket = frappe.db.sql("""
            SELECT name FROM `tabPOS Kitchen Ticket`
            WHERE invoice = %s AND station = 'Bar'
            LIMIT 1
        """, (doc.name,))
        if has_ticket:
            return

        # 3. Skip if this invoice belongs to a table order (already depleted on send_to_kitchen)
        has_order = frappe.db.sql("""
            SELECT parent FROM `tabPOS Restaurant Order Invoice`
            WHERE invoice = %s
            LIMIT 1
        """, (doc.name,))
        if has_order:
            return

        # 4. Direct invoice: deplete any bar items
        deplete_bar_items(doc.items or [], source_ref=doc.name)
    except Exception as e:
        frappe.log_error(title="Bar Pour Depletion Hook Warning", message=str(e))
