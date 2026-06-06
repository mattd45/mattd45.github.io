# Retail Arbitrage Platform — Planning

A tool that spots price differences between **mainstream retailers** (the buy side)
and **CeX / WeBuy** (the sell side), then surfaces the opportunities where buying
an item — after discounts, sales, voucher codes, cashback and Perkbox perks — and
re-selling it to CeX produces a net profit.

## Docs in this folder

| File | What it covers |
|------|----------------|
| [`PLAN.md`](./PLAN.md) | Full plan: concept, architecture, data sources, profit engine, roadmap, tech stack |
| [`RISKS.md`](./RISKS.md) | Legal / tax / terms-of-service / operational risks to decide on **before** building |
| [`DATA-MODEL.md`](./DATA-MODEL.md) | Draft entities and the profit-calculation formula |

## TL;DR

- **Edge:** CeX publishes its buy (trade-in) prices openly. If `CeX cash price >
  net cost to acquire the item`, that's a candidate opportunity.
- **Levers that create the gap:** retailer sales, clearance, discount codes,
  cashback portals (TopCashback/Quidco), stacked vouchers, and **Perkbox** /
  employee discounts.
- **Biggest unknowns to resolve first** (see `RISKS.md`): whether Perkbox &
  retailer T&Cs permit buying-to-resell, CeX's per-person trade-in limits and
  price decay, and the tax position (this is taxable trading income in the UK).

## Status

Planning only. Nothing built yet. Next step is for Matt to answer the open
questions at the end of `PLAN.md`.
