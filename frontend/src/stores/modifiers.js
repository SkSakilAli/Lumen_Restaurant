// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only
// "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
// Lumen Restaurants: the add-ons a restaurant outlet offers on its dishes (no
// pickles, medium heat, extra mayo), read once per outlet from
// lumen_restaurants.api.menu.get_modifiers and again after the Menu page
// changes them. Restaurant mode needs a connection, so there is no offline copy.
import { defineStore } from 'pinia'
import { call } from '../api'
import { useSessionStore } from './session'

export const useModifierStore = defineStore('modifiers', {
  state: () => ({
    profile: null,
    enabled: false,
    openOnTap: true,
    freeOnReceipt: true,
    groups: {},
    order: [],
    byItem: {},
    bySection: {},
    hiddenGroup: null,
    loading: false,
  }),

  getters: {
    // The groups a dish shows with, in the order they were made: its own and
    // its section's (the server already spread a section over its children).
    groupsFor(state) {
      return (item) => {
        if (!state.enabled || !item) return []
        const names = new Set([
          ...(state.byItem[item.item_code] || []),
          ...(state.bySection[item.item_group] || []),
        ])
        return state.order.filter((name) => names.has(name)).map((name) => state.groups[name])
      }
    },
    // The items of paid choices live in a section of their own, kept off the menu.
    isAddonItem(state) {
      return (item) => Boolean(state.hiddenGroup && item && item.item_group === state.hiddenGroup)
    },
  },

  actions: {
    async load(force = false) {
      const session = useSessionStore()
      if (!session.restaurantMode || !session.posProfile || session.offline) {
        this.enabled = false
        return
      }
      if (!force && this.profile === session.posProfile) return
      this.loading = true
      try {
        const data = await call('lumen_restaurants.api.menu.get_modifiers', {
          pos_profile: session.posProfile,
        })
        this.profile = session.posProfile
        this.enabled = Boolean(data.enabled)
        this.openOnTap = data.open_on_tap !== false
        this.freeOnReceipt = data.free_on_receipt !== false
        this.groups = Object.fromEntries((data.groups || []).map((g) => [g.name, g]))
        this.order = (data.groups || []).map((g) => g.name)
        this.byItem = data.by_item || {}
        this.bySection = data.by_section || {}
        this.hiddenGroup = data.hidden_group || null
      } catch {
        // Without them the till still sells: a dish takes a free note only.
        this.enabled = false
      } finally {
        this.loading = false
      }
    },
  },
})
