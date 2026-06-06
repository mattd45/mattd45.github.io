# Risks & Things to Decide Before Building

Not legal/tax advice — but these are the issues that materially affect whether
the platform is worth building and how. Worth a quick sanity check (and possibly
an accountant) before spending real money or time.

## 1. Perkbox & employee discounts — treat as a "maybe," not a foundation
- Perkbox and most employer benefit schemes provide discounts for the
  **employee's personal use**. Systematically buying to resell is very likely a
  breach of those terms, and potentially of your employment terms too.
- Codes can be single-use, account-linked, or void the order if abused; the
  retailer can cancel orders and the scheme can revoke access.
- **Recommendation:** design the platform so Perkbox is *one optional discount
  lever*, not the core edge. If the model only works *because* of Perkbox, the
  model is fragile and the activity is questionable. Make sure deals stand up on
  public sales + codes + cashback alone.

## 2. This is taxable trading income (UK)
- Buying with intent to resell at a profit is **trading**, not casual selling of
  unwanted items. Profit is taxable.
- There's a **£1,000 trading allowance**; above that you generally need to
  register as a sole trader and file a Self Assessment.
- CeX payouts and cashback both count toward income/profit.
- Keep clean records from day one (the Phase 3 tracking helps). Consider an
  accountant once volume is non-trivial.

## 3. CeX-side limits (the sell side has friction)
- **Price decay:** CeX's buy price drops as their stock of an item rises — a price
  you see today may be lower by the time you sell, and falls further if you bring
  multiples.
- **Volume / ID:** stores require photo ID, log your details, and may cap how
  many of the same item or how much value they'll take per person/day. They can
  decline items.
- **Condition & testing:** items are tested; "new/boxed" vs "unboxed" grading
  changes the price, and they can re-grade in person.
- **Not a guaranteed buyer:** "we are buying" can switch off per item.
- Net effect: model CeX prices as *indicative*, build in a margin buffer, and
  don't assume you can dump unlimited quantity.

## 4. Retailer terms & anti-reselling measures
- Many retailers' T&Cs prohibit buying for resale and impose **per-customer
  quantity limits**; they cancel orders, ban accounts, and limit stacking of
  codes/cashback.
- Stacking discount codes + cashback + employee discount sometimes voids one or
  more of them — verify per retailer rather than assuming they add up.

## 5. Data-source / ToS risk
- **CeX/WeBuy API:** confirm acceptable-use before depending on it; rate-limit and
  cache regardless.
- **Scraping retailers:** often against ToS and brittle. Prefer official/affiliate
  feeds (Amazon PA-API, eBay API, Awin/Rakuten). Isolate any scraping so it can be
  swapped or removed.

## 6. Operational / financial reality
- **Cashback is deferred and not guaranteed** (can be rejected, paid weeks later).
- **Voucher ≠ cash** — a chunk of CeX margin is store credit; only count it if
  you'll spend it.
- **Cashflow:** you front the money and wait to recoup via sale + cashback.
- **Time cost:** sourcing, buying, testing, packaging/posting or travelling to a
  store — the per-deal labour can eat thin margins. Set a minimum-£ threshold.

## Bottom line
The build is straightforward; the *viability* hinges on §1–§4. Phase 1 is
deliberately cheap precisely so you can test whether real, repeatable,
cash-positive opportunities exist **without leaning on Perkbox** before investing
further.
