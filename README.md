# Lumen Restaurants

The restaurant till for ERPNext, built from [LumenPOS](https://github.com/ma7mod7osam/lumenpos).

> **[Full user guide and documentation: docs/user-guide.md](docs/user-guide.md)**

Lumen Restaurants is LumenPOS with the restaurant built in, as an app of its own.
It carries everything LumenPOS does: the shift and the register, payments, the
POS Invoice, receipts, returns and refunds, customers, offers and bundles, price
books, loyalty, gift cards, cashback, approvals, insights, other currencies and
groups of several companies. On top of that it runs what a restaurant needs:

- **Tables and a floor plan.** Tables in areas, orders that stay open while the
  guests eat, move and merge tables, and pay one ordinary sale at the end.
- **A sell screen made for food.** Order type first (dine in, takeaway,
  delivery), big menu tiles, a note on any line ("no onions").
- **Order numbers.** A takeaway gets a short daily number the moment it is
  paid, printed big on the receipt and shown on the kitchen ticket, so the
  counter can call it.
- **The kitchen screen.** Tickets with the notes highlighted and real timing,
  and an optional ESC/POS kitchen printer per outlet.
- **Bookings.** A clear day book, and a **public booking page** per outlet
  (`/book/<outlet>`) the owner designs: colours, backgrounds, fonts, their own
  questions and packages such as a buffet priced per guest.

Each outlet chooses. Tick **Run this outlet as a restaurant** (ERP, POS Profile,
section **Lumen Restaurants**) and that outlet opens the restaurant till. Every
other outlet stays a shop till, so a group with shops and restaurants runs one
system. At a restaurant outlet the shop features a restaurant has no use for are
switched off: holds and deposits, the exchange flow, and the retail sell screen
with its parking, price checker and serial numbers.

## Requirements

- ERPNext v13 to v16.
- Nothing else. Lumen Restaurants does not need LumenPOS installed. A site runs
  Lumen Restaurants or LumenPOS, never both, because they hold the same records.

## Install

On Frappe Cloud, install Lumen Restaurants from the Marketplace. On a bench of
your own:

```bash
bench get-app https://github.com/ma7mod7osam/LumenRestaurants
bench --site <site> install-app lumen_restaurants
```

The front end ships built, so no Node or npm is needed on the bench.

The till is at `/pos`, and it can be installed on a tablet or a phone as its own
app. The public booking pages are at `/book/<outlet>`.

## Updates from LumenPOS

Lumen Restaurants keeps LumenPOS's history, so every LumenPOS release can be
brought in: see [docs/updating-from-lumenpos.md](docs/updating-from-lumenpos.md).

## Licence

GNU Affero General Public License v3.0 only. See `license.txt` and `NOTICE`.
"Lumen Restaurants", "LumenPOS" and their logos are trademarks of Lumen
Solutions, see `TRADEMARKS.md`.
