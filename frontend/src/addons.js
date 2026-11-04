// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only
// "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
// Lumen Restaurants: a dish and its add-ons on the cart.
//
// At a restaurant outlet every dish is a line of its own, tagged lr_line, with
// its choices (lr_mods) and its kitchen note. Each PAID choice is a line of its
// own right after its dish (lr_addon_of = the dish's lr_line), an item like any
// other, so the cart's totals, VAT and promotions and the server's pricing stay
// exactly what they are for any line. A free choice is only words: the kitchen
// and the receipt read them from the dish's line. The server checks every paid
// line against its dish's choices (lumen_restaurants/modifiers.py).

export function newLineId() {
  return 'L' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)
}

// The sheet's picks ({group: [option id]}) as the dish's choices, in the order
// of the groups and of their options. `k` says whether the kitchen hears it: a
// default nobody needs to hear ("Regular" heat) stays quiet unless the group
// asks to show its default (a size, a dough).
export function choicesFrom(groups, picks) {
  const out = []
  for (const g of groups) {
    const ids = picks[g.name] || []
    for (const o of g.options) {
      if (!ids.includes(o.id)) continue
      const paid = Boolean(o.item_code && o.price > 0)
      out.push({
        g: g.name,
        o: o.id,
        t: o.title,
        s: g.style || '',
        i: paid ? o.item_code : null,
        pr: paid ? o.price : 0,
        k: o.default && !g.print_default && !paid ? 0 : 1,
      })
    }
  }
  return out
}

export function picksFrom(line) {
  const picks = {}
  for (const c of line.lr_mods || []) (picks[c.g] = picks[c.g] || []).push(c.o)
  return picks
}

export function defaultPicks(groups) {
  const picks = {}
  for (const g of groups) {
    const ids = g.options.filter((o) => o.default).map((o) => o.id)
    picks[g.name] = g.multiple ? ids : ids.slice(0, 1)
  }
  return picks
}

export function missingGroups(groups, picks) {
  return groups.filter((g) => g.required && !(picks[g.name] || []).length)
}

// What a dish costs with its paid choices, for the sheet's button.
export function unitPrice(item, groups, picks) {
  let total = Number(item.price) || 0
  for (const c of choicesFrom(groups, picks)) total += c.pr || 0
  return total
}

// The words under a dish on the order: the choices the kitchen hears, without
// the paid ones (those are lines of their own, with their price).
export function freeChoices(line) {
  return (line.lr_mods || []).filter((c) => c.k !== 0 && !c.i).map((c) => c.t)
}

export function addonsOf(cart, lineId) {
  return cart.lines.filter((l) => l.lr_addon_of === lineId)
}

function signature(code, mods, note) {
  return JSON.stringify([code, (mods || []).map((c) => `${c.g}:${c.o}`).sort(), (note || '').trim()])
}

function dishLine(item) {
  return {
    item_code: item.item_code,
    item_name: item.item_name,
    item_group: item.item_group,
    brand: item.brand,
    tags: item.tags || [],
    barcode: item.barcode || null,
    warranty_days: item.warranty_days || 0,
    has_serial_no: 0,
    serial_nos: [],
    price: item.price || 0,
    standard_price: item.standard_price ?? item.price ?? 0,
    manual_discount_percent: 0,
  }
}

function addonLine(choice, qty, dishId, group) {
  return {
    item_code: choice.i,
    item_name: choice.t,
    item_group: group || null,
    brand: null,
    tags: [],
    barcode: null,
    has_serial_no: 0,
    serial_nos: [],
    qty,
    price: choice.pr,
    standard_price: choice.pr,
    manual_discount_percent: 0,
    lr_addon_of: dishId,
  }
}

function placeAddons(cart, dish, hiddenGroup) {
  const at = cart.lines.indexOf(dish)
  const addons = (dish.lr_mods || [])
    .filter((c) => c.i)
    .map((c) => addonLine(c, dish.qty, dish.lr_line, hiddenGroup))
  cart.lines.splice(at + 1, 0, ...addons)
}

// Add a dish with its choices. The very same dish with the very same choices
// and note adds to the line already there.
export function addDish(cart, item, groups, picks, qty = 1, note = '', hiddenGroup = null) {
  const mods = choicesFrom(groups, picks)
  const sig = signature(item.item_code, mods, note)
  const twin = cart.lines.find(
    (l) => l.lr_line && !l.bundle_key && signature(l.item_code, l.lr_mods, l.note) === sig
  )
  if (twin) {
    setDishQty(cart, twin.lr_line, twin.qty + qty)
    return twin.lr_line
  }
  const typed = typedPriceOf(cart, item.item_code)
  const dish = { ...dishLine(item), qty, note: (note || '').trim(), lr_line: newLineId(), lr_mods: mods }
  cart.lines.push(dish)
  // One price per item on the order (setItemPrice).
  if (typed != null) cart.setLinePrice(cart.lines.length - 1, typed)
  placeAddons(cart, dish, hiddenGroup)
  if (cart.appType || cart.customer) cart.reprice()
  return dish.lr_line
}

// Change a dish's choices, quantity or note: its paid lines are made again
// right after it.
export function updateDish(cart, lineId, groups, picks, qty, note, hiddenGroup = null) {
  const dish = cart.lines.find((l) => l.lr_line === lineId)
  if (!dish) return
  cart.lines = cart.lines.filter((l) => l.lr_addon_of !== lineId)
  dish.lr_mods = choicesFrom(groups, picks)
  dish.qty = Math.max(1, Number(qty) || 1)
  dish.note = (note || '').trim()
  placeAddons(cart, dish, hiddenGroup)
  if (cart.appType || cart.customer) cart.reprice()
}

export function setDishQty(cart, lineId, qty) {
  qty = Number(qty)
  if (!qty || qty <= 0) return removeDish(cart, lineId)
  for (const l of cart.lines) {
    if (l.lr_line === lineId || l.lr_addon_of === lineId) l.qty = qty
  }
}

export function removeDish(cart, lineId) {
  cart.lines = cart.lines.filter((l) => l.lr_line !== lineId && l.lr_addon_of !== lineId)
}

// A price typed at the till, where the outlet allows it and the person may
// (the server checks both again when the order is saved and at the sale):
// one price per item on the order, on every line of it, because a return
// takes an item back at one rate, the rate of its first line on the sale.
export function typedPriceOf(cart, itemCode) {
  const line = cart.lines.find((l) => l.item_code === itemCode && !l.bundle_key && l.price_override != null)
  return line ? line.price_override : null
}

// Type (or clear, with an empty value) the price of an item on every line of it.
export function setItemPrice(cart, itemCode, value) {
  cart.lines.forEach((line, i) => {
    if (line.item_code === itemCode && !line.bundle_key) cart.setLinePrice(i, value)
  })
}

// What a dish costs on the order: its own price and its paid lines.
export function dishTotal(cart, line) {
  return (
    line.price * line.qty +
    addonsOf(cart, line.lr_line).reduce((sum, a) => sum + a.price * a.qty, 0)
  )
}
