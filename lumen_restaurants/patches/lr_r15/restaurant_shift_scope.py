# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Lumen Restaurants 0.1.0-r15: a site that never stored "A shift belongs to"
gets the restaurant's choice, "Per outlet" (restaurant_defaults.py). Runs after
LumenPOS's v0_60.keep_shift_scope, which already wrote it where shifts exist."""

from lumen_restaurants import restaurant_defaults


def execute():
    restaurant_defaults.keep_restaurant_default()
