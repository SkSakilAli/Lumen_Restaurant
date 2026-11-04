// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only
//
// Lumen Restaurants: the help for staff (LumenPOS 0.58.0, help/content.js) at a
// restaurant too. LumenPOS's screens, topics, tours and news come as LumenPOS
// writes them (help/content.js, merged as it is), and this file lays the
// restaurant's on top. The till reads the help from here (stores/help.js,
// HelpPanel.vue, HelpCard.vue):
//  - the help of the restaurant screens (the tables, the kitchen, bookings, the
//    booking page, the Menu page), and at a restaurant outlet the order
//    screen's help in place of the shop sell screen's;
//  - the "sell" tour walks the restaurant order screen at a restaurant outlet
//    (RestaurantSellView carries the same data-tour markers, and order-type and
//    kitchen-send of its own), the shop's steps stay for a shop outlet;
//  - what is new, on OUR release numbers (0.1.0-rN, where the N counts):
//    LumenPOS's news is dated by the release of ours that brought it, ours is
//    added, and a LumenPOS entry that says something else here is replaced.
// Every text is an English key for t(); the Arabic is in messages-restaurant.js.

import * as lp from './content.js'

const restaurant = (s) => Boolean(s.restaurantMode)
const shop = (s) => !s.restaurantMode
const salespeople = (s) => s.salesPersons.length > 0 && s.settings.salesperson_mode !== 'Off'
// A condition joined to an entry's own (topics, tour steps, tours, news).
const also = (cond, entry) => ({ ...entry, when: (s) => cond(s) && (!entry.when || entry.when(s)) })

export const SCREENS = {
  ...lp.SCREENS,
  '/tables': 'Tables',
  '/kitchen': 'Kitchen',
  '/reservations': 'Bookings',
  '/booking-designer': 'Booking page',
  '/menu': 'Menu',
}

const ORDER_SCREEN = [
  {
    title: 'Take an order',
    tour: 'sell',
    steps: [
      ['Pick how the guest eats: {dine}, {takeaway} or {delivery}.', { dine: 'Dine in', takeaway: 'Takeaway', delivery: 'Delivery' }],
      ['{dine} opens the tables: tap a table and its order opens here.', { dine: 'Dine in' }],
      'A takeaway or a delivery is paid first, and the kitchen gets it with its order number.',
    ],
  },
  {
    title: 'Add dishes',
    steps: [
      "Type part of a dish's name in the search box, or tap a section to see its dishes.",
      ['Tap a dish to add it. A dish marked {mods} opens its window first: pick the choices, then add it.', { mods: 'Has add-ons' }],
      'The same dish with the same choices adds to its line.',
    ],
  },
  {
    title: 'The lines of the order',
    steps: [
      'Change the quantity with the minus and plus buttons.',
      ['{addons} changes the choices of a dish. {note} adds a note for the kitchen.', { addons: 'Add-ons', note: 'Note' }],
      'Once the kitchen has a dish, its choices stay as they are: change the quantity, or add it again with other choices.',
    ],
  },
  {
    title: 'Pay on account',
    when: (s) => Boolean(s.settings.credit_sales_enabled) && Boolean(s.permissions.sell_on_account),
    steps: [
      'Pick the customer on the order first: a sale on account needs a named customer, never the walk-in.',
      ['At the payment screen, take what the guest pays now, then use {put} for the rest.', { put: 'On account' }],
      'A table order is paid on account the same way, from the order screen or from its panel on the Tables screen.',
      'The receipt shows what is still owed, with a line for the customer to sign.',
    ],
  },
  {
    title: 'A price for a dish',
    when: (s) => Boolean(s.permissions.can_change_price),
    steps: [
      ['{price} on a line types a new price for that dish. Leave it empty for the menu price.', { price: 'Price' }],
      'The price holds for every line of that dish on the order, so a return gives back what was paid.',
      'On a table order it stays with the name of whoever typed it.',
    ],
  },
  {
    title: 'Send to the kitchen',
    steps: [
      'On a table order, the kitchen button sends the dishes added since the last send. Each send is a new ticket.',
      'A takeaway or a delivery goes to the kitchen by itself when it is paid.',
    ],
  },
  {
    title: 'The customer and the salesperson',
    steps: [
      'Tap the customer row to find or add a customer. Without one, the sale goes to the walk-in customer.',
      'Pick who served the order under it, where your restaurant uses salespeople. It may make it required in Settings.',
    ],
  },
  {
    title: 'Pay',
    steps: [
      ['{pay} opens the payment screen: pick how the guest pays, split it if needed, and the change is worked out for you.', { pay: 'Pay' }],
      'A takeaway gets its order number on the receipt and on the kitchen ticket.',
      'A table order closes when it is paid, and the table is free again.',
    ],
  },
]

const RESTAURANT_SCREENS = [
  {
    route: '/tables',
    title: 'The floor',
    steps: [
      ['Each area is a tab, its tables drawn where they stand. {plan} and {list} switch the view, and a phone opens on the list.', { plan: 'Plan', list: 'List' }],
      'The colour of a table says what is happening there: free, occupied in blue, waiting to pay in amber, booked in violet.',
      'The badge on a table is how long its guests have been sitting, or the time of its booking.',
      'Tap a free table to start its order: the number of guests and a note, then the order screen opens.',
      ['Tap a table with an order to see it priced as the guests will pay it, then {open} to go on with it.', { open: 'Open the order' }],
      'Orders that are not at a table show under the plan.',
    ],
  },
  {
    route: '/tables',
    title: 'The bill and the payment',
    steps: [
      ['{print} prints what the table owes, with our mark at its foot. It is not a tax invoice: the receipt of the payment is.', { print: 'Print the bill' }],
      'The table turns amber, waiting to pay. A dish added after it turns the table back until the bill is printed again.',
      ['{pay} opens the payment window over the plan. The receipt follows, and the table is free again.', { pay: 'Pay' }],
      ['A booked table offers {seated} when its guests arrive: the booking is marked and their order opens.', { seated: 'Seated' }],
    ],
  },
  {
    route: '/tables',
    title: 'Move, merge or cancel',
    steps: [
      ['{move} or {merge} in the panel of a table with an order, then tap the table it goes to on the plan.', { move: 'Move', merge: 'Merge' }],
      ['{off} in the bar above the plan takes the order off the floor.', { off: 'Off the floor (takeaway counter)' }],
      'Merging moves every line onto the other order, and this one is marked merged.',
      'An order that was never paid can be cancelled, with a reason when it has dishes on it.',
      'Who may do each is set in Settings, General, Approvals and access.',
    ],
  },
  {
    route: '/tables',
    title: 'Edit the floor plan',
    steps: [
      ['{edit} opens the edit mode, for the people allowed to edit the floor plan.', { edit: 'Edit the plan' }],
      'Drag a table or an item to move it. Tap it to change its number, shape, seats, rotation or area, or to take it out of service.',
      ['{table} and {item} add tables, walls, doors, windows, plants and the places guests look for.', { table: 'Add a table', item: 'Add an item' }],
      ['{photo} puts a photo of your real floor under the plan, and {area} adds a tab.', { photo: 'Plan photo', area: 'New area' }],
      ['Nothing changes for anyone else until {save}.', { save: 'Save the plan' }],
    ],
  },
  {
    route: '/kitchen',
    title: 'The kitchen screen',
    steps: [
      'Every ticket waiting, with its dishes, their choices and the notes.',
      ['{start} when work begins, {ready} when it is done, {handed} when it has left.', { start: 'Start preparing', ready: 'Ready', handed: 'Handed over' }],
      'The clock on a ticket turns amber, then red, as it waits.',
      ['{print} prints the slip on the kitchen printer, where there is one.', { print: 'Print the kitchen slip' }],
    ],
  },
  {
    route: '/kitchen',
    title: 'Choices on a dish',
    steps: [
      'Red is without, amber is heat, violet is doneness, blue is a paid extra.',
      'A ready takeaway shows its number on the order screen, to call the guest.',
    ],
  },
  {
    route: '/reservations',
    title: 'Bookings',
    steps: [
      ['{today}, {tomorrow} or any date: the bookings of that day.', { today: 'Today', tomorrow: 'Tomorrow' }],
      ['{new} takes a booking by phone: the name, the mobile, the time, the guests and a note.', { new: 'New reservation' }],
      ['A booking made on your booking page waits for you to {confirm} or {decline} it.', { confirm: 'Confirm', decline: 'Decline' }],
      ['When the guests come, {arrived}. When they do not, {noshow}.', { arrived: 'Arrived', noshow: 'No show' }],
    ],
  },
  {
    route: '/booking-designer',
    title: 'Your booking page',
    steps: [
      'The page your guests book from: its colours, background and font, your own questions, and packages like a buffet.',
      'Share its link on social media or on your website. Its bookings come to the Bookings screen.',
    ],
  },
  {
    route: '/menu',
    title: 'Dishes',
    steps: [
      ['{new} adds a dish with its name, price and section. Tap a dish to change it.', { new: 'New dish' }],
      'Tick several dishes to tie an add-on group to them all, untie it, or take them off sale.',
      'A dish off sale is off at every outlet.',
    ],
  },
  {
    route: '/menu',
    title: 'Add-on groups',
    steps: [
      ['{new} makes a group: one choice (heat level) or several (sauces), required or not.', { new: 'New group' }],
      'A choice at 0 is a note for the kitchen. A choice with a price is billed on its own line under the dish.',
      'A new group asks which dishes it shows with as soon as it is saved: a whole section, which also covers the dishes added to it later, or single dishes.',
    ],
  },
]

export const TOPICS = [
  // the order screen at a restaurant outlet, the shop sell screen's elsewhere
  ...ORDER_SCREEN.map((topic) => also(restaurant, { ...topic, route: '/' })),
  ...lp.TOPICS.map((topic) => (topic.route === '/' ? also(shop, topic) : topic)),
  ...RESTAURANT_SCREENS,
]

const RESTAURANT_SELL_STEPS = [
  { target: 'order-type', title: 'How the guest eats', text: 'Dine in opens the tables. A takeaway or a delivery is paid first and gets an order number.', optional: true },
  { target: 'sell-search', title: 'Find a dish', text: 'Type part of its name.' },
  { target: 'sell-groups', title: 'Sections', text: 'Show one section of the menu at a time.' },
  { target: 'sell-products', title: 'Add it', text: 'Tap a dish to add it. A dish with add-ons opens its window first.', optional: true },
  { target: 'cart-customer', title: 'The customer', text: 'Optional. Without one, the sale goes to the walk-in customer.' },
  { target: 'cart-salesperson', title: 'Who served it', text: 'Pick the salesperson. Your restaurant may make it required.', optional: true },
  { target: 'cart-lines', title: 'The order', text: 'On each line: the quantity, the add-ons and a note for the kitchen.' },
  { target: 'kitchen-send', title: 'Send to the kitchen', text: 'On a table order, sends what was added since the last send.', optional: true },
  { target: 'cart-totals', title: 'The total', text: 'With the tax it includes.' },
  { target: 'cart-pay', title: 'Pay', text: 'Opens the payment screen. A takeaway gets its order number when it is paid.' },
]

const sellTour = lp.TOURS.sell
export const TOURS = {
  ...lp.TOURS,
  sell: {
    ...sellTour,
    steps: [
      // "open the shift first" serves both; the shop's other steps only a shop
      ...sellTour.steps.map((step) => (step.target === 'register-pill' ? step : also(shop, step))),
      ...RESTAURANT_SELL_STEPS.map((step) => also(restaurant, step)),
    ],
  },
  // the restaurant order screen has no currency switch
  currency: also(shop, lp.TOURS.currency),
}

// What is new. Our release numbers count their N: "0.1.0-r13" is newer than
// "0.1.0-r12" (stores/help.js compareVersions reads them the same way).
const parts = (v) => String(v || '').replace(/-r(\d+)$/, '.$1').split('.').map((n) => parseInt(n, 10) || 0)
function newer(a, b) {
  const x = parts(a)
  const y = parts(b)
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    const d = (x[i] || 0) - (y[i] || 0)
    if (d) return d
  }
  return 0
}

// The release of ours that brought a LumenPOS release (docs/user-guide.md,
// Lumen Restaurants releases). Add a line with every merge of LumenPOS.
function ourRelease(lumenpos) {
  const v = parts(lumenpos)
  const at = (minor, patch = 0) => v[1] > minor || (v[1] === minor && (v[2] || 0) >= patch)
  if (v[0] !== 0) return '0.1.0-r1'
  if (at(61, 2)) return '0.1.0-r18'
  if (at(61)) return '0.1.0-r17'
  if (at(58, 1)) return '0.1.0-r15'
  if (at(57)) return '0.1.0-r13'
  if (at(56, 1)) return '0.1.0-r12'
  if (at(54, 1)) return '0.1.0-r10'
  if (at(51, 1)) return '0.1.0-r8'
  return '0.1.0-r1'
}

// LumenPOS's news that reads differently here, by its title.
const REPLACED = new Set([
  // 0.58.0: in this app the switch was turned back ON by every Save (ours below)
  'Refunds to store credit',
])
const SHOP_ONLY = new Set([
  // the shop's line in the cart: the restaurant's own entry is below
  'A new price at the till',
  // the shop sell tour: the restaurant's own entry is below
  'The salesperson on every sale',
])

const OURS = [
  { version: '0.1.0-r14', title: 'The floor plan', text: 'The Tables screen draws each area with its tables where they stand. Tap a table for its order, its bill and its payment.', route: '/tables', when: restaurant },
  { version: '0.1.0-r14', title: 'Draw your floor', text: 'Edit the plan on the Tables screen moves, adds and turns tables, and draws the walls, doors and the rest of your place.', route: '/tables', when: (s) => restaurant(s) && Boolean(s.permissions.can_edit_floor) },
  { version: '0.1.0-r13', title: 'Help on the restaurant screens', text: 'Tap ? on the order screen, the tables, the kitchen, bookings and the Menu page for their help, and take the tour of an order.', tour: 'sell', when: (s) => restaurant(s) && Boolean(s.help.in_till) },
  { version: '0.1.0-r13', title: 'Who served the order', text: 'Pick the salesperson under the customer on the order screen. Your restaurant may make it required in Settings.', when: (s) => restaurant(s) && salespeople(s) },
  { version: '0.1.0-r12', title: 'Refunds to store credit', text: 'Saving the General settings used to turn Allow refunding to Store Credit back on. If your restaurant gives money back only, check it is off in Settings, General, Returns and refunds.', route: '/settings', when: (s) => Boolean(s.permissions.settings) },
  { version: '0.1.0-r11', title: 'Order numbers after midnight', text: 'A shift that runs past midnight keeps its takeaway numbers until it closes. The next day starts again at 1.', when: restaurant },
  { version: '0.1.0-r11', title: 'A price for a dish', text: 'Where your restaurant allows it, Price on a line of the order types a new price for that dish.', when: (s) => restaurant(s) && Boolean(s.permissions.can_change_price) },
  { version: '0.1.0-r9', title: 'Add-ons on dishes', text: 'No pickles, extra cheese, medium heat: a dish with add-ons opens its window when you tap it. Paid ones are billed under the dish, and the kitchen sees them all.', when: restaurant },
  { version: '0.1.0-r9', title: 'The Menu page', text: 'Dishes, prices, sections and add-on groups in one place, for the people allowed to edit the menu.', route: '/menu', when: (s) => restaurant(s) && Boolean(s.permissions.can_edit_menu) },
]

export const WHATS_NEW = [
  ...OURS,
  ...lp.WHATS_NEW
    .filter((entry) => !REPLACED.has(entry.title))
    .map((entry) => {
      const dated = { ...entry, version: ourRelease(entry.version) }
      return SHOP_ONLY.has(entry.title) ? also(shop, dated) : dated
    }),
].sort((a, b) => newer(b.version, a.version))
