# Bringing a LumenPOS update into Lumen Restaurants

Lumen Restaurants is LumenPOS with the restaurant built in, as an app of its own.
Its history is LumenPOS's history, so every LumenPOS release is merged in like
any other branch. Do it for each LumenPOS release, and before each Lumen
Restaurants release.

## What stays LumenPOS-named on purpose

Only the app's identity and its module are Lumen Restaurants: the Python
package `lumen_restaurants`, the app name and title, the module *Lumen
Restaurants* (folder `lumen_restaurants/lumen_restaurants/`, and the `module`
of every doctype), the dotted paths (imports, hooks, patches, the server methods
the screens call) and the asset URLs (`/assets/lumen_restaurants/...`). The
module needs a name of its own because Frappe maps module names to apps across
the whole bench: two apps with one module name cannot share a bench, and Frappe
Cloud puts many apps on one bench. The internal record names stay LumenPOS's:
the doctypes (such as *LumenPOS Settings*), the custom fields (`lumenpos_*`),
the roles (*LumenPOS Manager*, *LumenPOS Cashier*), the *LumenPOS* workspace and
the browser's offline store. That keeps each merge small, and a site that moves
from LumenPOS keeps its data.

Because the record names are shared, a site runs one of the two apps.
`lumen_restaurants/site_guard.py` refuses either app on a site that runs the
other, before anything is written.

## Start from the inbox

LumenPOS's maintainers write every batch of LumenPOS work, and every problem
they find that Lumen Restaurants must fix, to `inbox-from-lumenpos/` in the
project folder (next to this repository, not part of it). Read its `INDEX.md`
first: each
open entry names the LumenPOS commits, new fields, the files that will
conflict and the **MUST FIX** items in our own code. Merge as below, fix those
items, test, then fill in the entry's last column (our commit and the date).

## The steps

1. **Fetch LumenPOS.** `git fetch lumenpos`. The `lumenpos` remote points at the
   LumenPOS repository, and pushing to it is disabled on purpose.
2. **Merge.** `git merge lumenpos/main`. Git follows the folder renames
   (`lumenpos/` to `lumen_restaurants/`, and the module folder
   `lumenpos/lumenpos/` to `lumen_restaurants/lumen_restaurants/`) by itself in
   almost every case.
3. **Give the new code the Lumen Restaurants identity.**
   `node scripts/rename_from_lumenpos.mjs`. It moves anything that still landed
   under an old folder, and renames the dotted paths, the module name, the asset
   URLs and the app name. Running it twice changes nothing.
4. **Resolve the conflicts.**
   - Keep ours, then carry over any real change by hand: `README.md`, `NOTICE`,
     `TRADEMARKS.md`, `frontend/public/manifest.json`, the icons in
     `frontend/public/` (`favicon.svg`, `favicon-*.png`, `pwa-*.png`,
     `app-icon-180.png`, all from the logo kit), `lumen_restaurants/public/images/`
     (the logo kit itself), and the version in `lumen_restaurants/__init__.py`.
   - Delete again if a merge brings them back: `scripts/make_icons.mjs` and
     `frontend/public/icon-192.png` / `icon-512.png` (LumenPOS's icons), and
     `docs/website-guide.md` (the text of LumenPOS's page on its website, which
     names LumenPOS's repository, so `git rm` it when a merge changes it).
   - Keep both sides: `lumen_restaurants/hooks.py` (the title, the description
     and the two `site_guard` hooks), `lumen_restaurants/api/sales.py` (the
     emailed receipt attaches with our mark, `attach_with_mark`),
     `frontend/src/components/ReceiptModal.vue` (an outlet's own Print Format
     prints through `receipt_print.print_html`, our mark at the foot), `lumen_restaurants/api/session.py` (the
     restaurant switches at the end of `get_bootstrap`), `lumen_restaurants/install.py` (the section
     labels), `lumen_restaurants/www/pos.html` (the title and the icon links) and
     `book.html` (the title, the favicon and the footer mark),
     `frontend/public/sw.js` (the icon names it keeps offline),
     `lumen_restaurants/api/printing.py` (the two `receipt_images` lines:
     the restaurant's logo on top, our mark at the foot),
     `frontend/src/components/ReceiptView.vue` (our mark at the foot),
     `frontend/src/components/NavRail.vue` (the logo), `App.vue` (the product
     name, the router view keyed by the outlet, the table order put down on an
     outlet switch, the restaurant screens sent back to the till at a shop
     outlet), `components/OpenRegisterOverlay.vue` (the same table order rule),
     and `SettingsView.vue` and `messages.js` (the product name).
   - Keep both, the add-ons on dishes (0.1.0-r9): `api/sales.py` (the call to
     `modifiers.apply_to_invoice` before the service charge, and
     `modifiers.receipt_item` in `get_receipt`), `api/catalog.py` (the add-ons
     section kept off the grid), `api/session.py` (`can_edit_menu`, and the
     add-ons section kept off the section list), `api/permissions.py`
     (`EDIT_MENU`, closed by default), `api/printing.py` (add-on lines on the
     receipt, choices on the kitchen slip), `hooks.py` (`after_install` and
     `after_migrate` are lists with `modifiers.ensure_setup`), the capability
     Select of `pos_capability_rule.json` (Edit the menu), `stores/cart.js`
     (`addItem` never merges into a dish or its add-on, `_basePayload` sends
     the `lr_*` keys, `sendToKitchen` skips add-on lines and sends the
     choices), `components/ReceiptView.vue` (add-on rows, the free choices),
     `NavRail.vue` (the Menu item), `main.js` (the /menu route), `App.vue`
     (/menu is restaurant-only), `SettingsView.vue` (`AddonSettings` in the
     Restaurant section, the restaurant's actions in `capabilityOptions`),
     `messages.js` (the import and spread of `messages-restaurant.js`) and
     `translations/ar.csv` (the add-ons' server messages).
   - Keep both, found merging LumenPOS 0.54.1 to 0.56.0 (0.1.0-r10):
     `api/catalog.py` `get_items` (LumenPOS's `item_groups_under` filter, and
     our add-ons section kept off only when no group filter applies),
     `api/session.py` (LumenPOS's root rule and `item_group_members`, next to
     our add-ons section kept off the section list), `api/sales.py`
     `submit_sale` (our `restaurant_meta` first, then LumenPOS's
     `receipt = _sale_answer(invoice.name)`, then our `order_no` and
     `kitchen_ticket` on it), and `stores/cart.js` (LumenPOS's `_saleKey` next
     to our `order` and `serviceType`, `clear()` resets both, the payload's
     `idempotency_key` right after our `order:` line, `_keepQueuedSale` after
     our `leaveOrder`).
   - Keep both, a price typed on the restaurant screen (0.1.0-r11):
     `api/sales.py` `_price_overrides` (after the outlet switch check, our
     `restaurant.assert_one_price_per_item` at a restaurant outlet and
     `restaurant.typed_on_order` next to `permissions.can_edit_price()`).
     LumenPOS's `stores/cart.js` `setLinePrice` is what our screen calls.
   - Keep both, LumenPOS 0.57.0 and 0.58.0 (0.1.0-r13): `stores/help.js` (it
     imports TOPICS, TOURS and WHATS_NEW from our `help/restaurant.js`, and
     `compareVersions` counts our "-rN"), `HelpPanel.vue` and `HelpCard.vue`
     (SCREENS and TOURS from `help/restaurant.js`, "Lumen Restaurants" in
     front of the version and in the title), `api/system_check.py` (`_named`
     around the texts naming LumenPOS, the error log searched under
     `/lumen_restaurants/`), `SettingsView.vue` (the System check's version
     line), `permissions.py` and `pos_capability_rule.json` (our four
     restaurant capabilities next to LumenPOS's, CLOSED_BY_DEFAULT with
     Edit the menu), `stores/cart.js` (`orderSnapshot` and `openOrder` carry
     the table's salesperson). Ours, never conflicting:
     `help/restaurant.js`, `components/SalespersonRow.vue`, the data-tour
     markers of `RestaurantSellView.vue`. **With every LumenPOS merge:** add
     its release to `ourRelease()` in `help/restaurant.js` (LumenPOS's news is
     dated by the release of ours that brought it), read its new WHATS_NEW and
     TOPICS for anything that says something else at a restaurant (REPLACED
     and SHOP_ONLY there), and give our own new whitelisted functions type
     hints behind `from __future__ import annotations`.
   - Keep both, the floor plan (0.1.0-r14): `api/permissions.py` and
     `pos_capability_rule.json` (`EDIT_FLOOR`, "Edit the floor plan",
     closed by default), `api/session.py` (`can_edit_floor`), `hooks.py`
     (`floor.ensure_setup` in both lists), `api/printing.py` (the bill's
     BILL and "Not a tax invoice" lines), `components/ReceiptView.vue` (the
     bill's stamp, table and note), `SettingsView.vue` (`FloorSettings` in
     the Restaurant section, "Edit the floor plan" in `capabilityOptions`),
     `messages.js` (`restaurantEn` spread into the English dictionary) and
     `translations/ar.csv` (the plan's and the bill's server messages). Ours,
     never conflicting: `floor.py`, `api/floor.py`, the doctypes
     `pos_floor_area` and `pos_floor_object`, `frontend/src/floor/`,
     `views/TablesView.vue` (all ours since the restaurant left LumenPOS),
     `components/FloorSettings.vue` and `components/restaurant-settings.css`.
   - Keep both, LumenPOS 0.58.1 to 0.60.1 (0.1.0-r15): `SettingsView.vue`
     (our Restaurant card, closed by its own `</div>`, then LumenPOS's Sales on
     account card; the `restaurant` and `credit` sections both after
     `holds`; our tables functions and LumenPOS's reason helpers; our
     `.add-row` and `.table-row` styles with LumenPOS's new ones; our
     `named()` around three texts that name LumenPOS as the product),
     `pos_capability_rule.json` and `permissions.py` (LumenPOS's three of
     sales on account, then our five, all in CLOSED_BY_DEFAULT but LumenPOS's
     open ones), the dictionary line of `messages.js` (`restaurantEn` and
     `restaurantAddonsAr` spread in front), `translations/ar.csv` (both
     sides' rows, sorted). `patches.txt` did not follow the rename this time:
     LumenPOS's new line came as `lumenpos/patches.txt`, copied into ours by
     hand. Ours, never conflicting: `restaurant_defaults.py` and the patch
     `patches/lr_r15/restaurant_shift_scope.py` (a restaurant site starts on
     one shift per outlet, LumenPOS's own default and code untouched),
     `receipt_print.owed_html` (what a sale on account owes, on an outlet's
     own Print Format and the emailed receipt). LumenPOS's `ReceiptModal.vue`
     asks `printing.allow_reprint` before every print path, ours included.
   - Keep both, LumenPOS 0.61.0 and 0.61.1 (0.1.0-r17): `pos_capability_rule.json`
     (LumenPOS's list, "Cash in" and "Cash out" in place of "Cash in / out",
     then our five restaurant actions), `permissions.py` (our restaurant rights
     up to `can_edit_floor`, then LumenPOS's `_cash_allowed`, `can_cash_in`,
     `can_cash_out` and the new `can_move_cash`), the dictionary line of
     `messages.js` (LumenPOS's `cashOut` and `owesHolds` blocks with our two
     spreads in front), `translations/ar.csv` (both sides' rows, sorted), and
     plain import lines taken from LumenPOS in `register.py`, `settings.py`,
     `session.py` and `stores/session.js` (the rename script fixes them).
     LumenPOS's patch line came as `lumenpos/patches.txt` again: copied into
     ours by hand. No restaurant path moves cash, so the two new rights need
     nothing of ours. Do not `git stash` our own edits in the middle of a merge:
     the stash keeps the merge's whole index, and popping it after the merge
     commit conflicts with itself (copy the files aside instead).
   - LumenPOS 0.61.2 and 0.61.3 (0.1.0-r18): `messages.js` (LumenPOS's
     `anyCurrency` block, our spreads in front), the version line, the guide's
     header. `hooks.py` came as `lumenpos/hooks.py` again (modify/delete):
     LumenPOS's `add_to_apps_screen` block is in ours by hand, with our logo
     (`/assets/lumen_restaurants/pos/pwa-192.png`) and
     `lumen_restaurants.api.session.can_open_till`, then `git rm` the stray
     file. **The Frappe 16 desk files** (`desktop_icon/`, `workspace_sidebar/`,
     `<module>/sidebar/`, `dock/`) arrive under `lumenpos/` naming LumenPOS:
     `node scripts/desk_files_from_lumenpos.mjs` writes ours (app, module and
     title Lumen Restaurants, our logo on our tile, our Restaurant section after
     the outlets, and a HIDDEN tile named after our workspace "LumenPOS", or
     Frappe makes a second tile of ours by itself in grid mode) and removes
     theirs wherever git put them, `--check` says whether they are in step. Run it after every
     merge that touches LumenPOS's copies. Our dock must never set `mount_on`
     (Frappe drops the apps tile of an app that mounts on another), the script
     refuses one. The owner chose our own tile on the apps screen (2026-10-17).
   - **LumenPOS's quality gate on our copy** (`ERPNext POS/quality/gate.mjs`,
     read only): it expects LumenPOS's folders, so point it at a folder of
     junctions (`lumenpos` to our `lumen_restaurants`, plus `frontend`,
     `docs`, `scripts`) with `--repo <that folder> --bench <none>`. Its
     "patches and hooks" rule then fails on our dotted names, and "languages"
     cannot load `messages-restaurant.js`: both are the gate, not us. Every
     other rule applies as it is.
   - `SettingsView.vue` `load()` (0.1.0-r12): our line reading
     `allow_store_credit_refund` (LumenPOS 0.56.2 and 0.58.0 leave it out, so
     every Save turned refunds to store credit back on). When LumenPOS adds the
     same line, keep one of the two. Their quality gate's "settings round trip"
     rule finds any such key.
   - `api/menu.py` (ours) follows LumenPOS's item group rules: `_listed` reads
     the outlet's list as `catalog.item_groups_under` does, and the dishes skip
     `catalog.internal_item_codes()`. When LumenPOS changes either helper, look
     at the Menu page again (`menu_tree_check.py` in the project folder's
     `reference/bench-scripts/`).
   - `docs/user-guide.md`: keep our header and the *Lumen Restaurants releases*
     table, take LumenPOS's new sections and rows.
   - A doctype file LumenPOS changed: take its change. Should a conflict land on
     the `"module"` line, the rename script sets it back to Lumen Restaurants.
   - Most conflicts are LumenPOS's new text against our renamed copy of its old
     text: take theirs, the rename script (step 3, run it again) puts our names
     back. Look for our own lines inside a block before taking theirs.
   - LumenPOS's built till files land under `lumen_restaurants/public/pos/`
     (`pos.js`, `pos.css`, `chunk-*.js`): delete them, step 5 builds our own.
   - The restaurant's own files (its screens, doctypes and APIs) and
     `site_guard.py`, `receipt_images.py`, `receipt_print.py` and
     `modifiers.py` do not exist in LumenPOS, so they never conflict. Nor do the
     add-ons' own: `api/menu.py`, the `pos_modifier_*` doctypes, and in the
     frontend `addons.js`, `stores/modifiers.js`, `messages-restaurant.js`,
     `components/ModifierSheet.vue`, `components/AddonSettings.vue` and
     `views/MenuView.vue`. Our own patches, when there are any,
     go in `patches/lr_*` folders, apart from LumenPOS's `patches/v0_*`.
5. **Rebuild the till.** `cd frontend && npm ci && npx vite build`, and commit the
   build in `lumen_restaurants/public/pos`. The build is what the sites run.
6. **Check.**
   - `python3 scripts/check_endpoints.py`: every call from the screens resolves
     to a whitelisted server method.
   - `node scripts/rename_from_lumenpos.mjs --check` reports 0 files, and
     `node scripts/desk_files_from_lumenpos.mjs --check` "desk files in step".
   - The Python compiles (`python3 -m compileall -q lumen_restaurants`).
   - `check_endpoints.py` also catches a `@frappe.whitelist()` that slid onto
     the wrong function in a merge ("DECORATOR THEFT"). It found one in
     LumenPOS 0.55.0 itself (`api/layaway.py`: `_assert_hold_prices` took the
     decorator of `create_layaway`, so a hold could not be started from the
     till): put it back on the endpoint and tell LumenPOS's maintainers.
7. **Test, then release.** Install on a throwaway site on the benches first,
   then the test sites. LumenPOS's own suites that come in the inbox's
   `tools/` folder run on our sites as they are, with the project folder's
   `reference/bench-scripts/`: `lp_fixtures.py` makes their shop outlet
   ("LumenPOS Smoke", LP-PLAIN) once per site, and `lp_suite.sh <bench> <site>
   <suite.py>` renames their imports to ours and runs them (a suite a note
   names but did not copy is taken from LumenPOS's `/opt/benchtest/`, read
   only). Bump the version (`x.y.z-rN` for previews) and add the
   changelog row in `docs/user-guide.md` in the same commit as the code.
