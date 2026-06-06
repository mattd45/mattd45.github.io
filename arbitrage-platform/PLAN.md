# Retail Arbitrage Platform — Plan

> Assumed context: UK-based, single operator (you) to start, CeX as the primary
> sell-side. Adjust if any of that is wrong.

---

## 1. The core idea

CeX (WeBuy) will tell you, publicly and for free, exactly how much they'll pay
for thousands of specific products — phones, consoles, games, GPUs, headphones,
tablets, etc. They quote two numbers per item:

- **Cash price** — what they pay you in money.
- **Voucher price** — store credit, typically ~25–30% higher than cash.

So for any item we can compute:

```
profit = CeX_price  −  net_cost_to_acquire
```

`net_cost_to_acquire` is where all the levers come in: the retailer's price after
sales/clearance, minus discount codes, minus cashback, minus Perkbox/employee
discount, plus shipping if any. The platform's whole job is to keep both sides of
that equation up to date across many products and flag the rows where the gap is
positive (and big enough to be worth the effort and risk).

**Important framing:** the realistic edge here is *not* "CeX pays more than RRP."
It's "a temporary discount/code/cashback stack pushes the buy cost below CeX's
standing trade-in price for a short window." The opportunities are transient, so
the platform is really a *monitoring and alerting* system, not a static price list.

> ⚠️ Before writing real code, read [`RISKS.md`](./RISKS.md). Several of the
> levers (Perkbox especially) and the resale activity itself have terms-of-service
> and tax implications that change what's worth building.

---

## 2. What the platform actually does

1. **Ingest sell-side prices** from CeX (cash + voucher + whether they're currently
   buying / stock-capped).
2. **Ingest buy-side prices** from one or more retailers, including current
   sale/clearance prices.
3. **Match** a CeX product to the same retailer product (by barcode/EAN, model
   number, then fuzzy name match).
4. **Apply discount layers** to the buy-side: live discount codes, cashback %,
   Perkbox/employee discount, gift-card discounts.
5. **Compute net margin** per item and per "deal stack."
6. **Rank & alert** — surface positive-margin opportunities, sorted by
   £ profit, % ROI, and confidence; push notifications for new ones.
7. **Track** what you actually bought/sold so you learn real (not theoretical)
   margins and CeX's price decay.

---

## 3. Architecture (high level)

```
                 ┌─────────────────────────────────────────────┐
                 │                  Schedulers                  │
                 │   (cron / queue — refresh prices on cadence) │
                 └─────────────────────────────────────────────┘
                        │              │               │
            ┌───────────▼───┐  ┌───────▼───────┐  ┌────▼──────────┐
            │ CeX connector │  │ Retailer      │  │ Discounts /   │
            │ (sell-side)   │  │ connectors    │  │ cashback /    │
            │               │  │ (buy-side)    │  │ Perkbox feed  │
            └───────┬───────┘  └───────┬───────┘  └────┬──────────┘
                    │                  │               │
                    ▼                  ▼               ▼
            ┌──────────────────────────────────────────────────┐
            │                  Normaliser                       │
            │  - canonical product (EAN/model)                  │
            │  - currency, condition, units                     │
            └───────────────────────┬──────────────────────────┘
                                    ▼
            ┌──────────────────────────────────────────────────┐
            │                Matching engine                    │
            │  barcode → model → fuzzy name; confidence score   │
            └───────────────────────┬──────────────────────────┘
                                    ▼
            ┌──────────────────────────────────────────────────┐
            │                 Profit engine                     │
            │  net cost stack vs CeX cash/voucher → margin      │
            └───────────────────────┬──────────────────────────┘
                                    ▼
            ┌─────────────────┐   ┌──────────────────────────────┐
            │   Data store    │──▶│  API + Dashboard + Alerts     │
            │ (Postgres)      │   │  (web UI, push/email/Telegram)│
            └─────────────────┘   └──────────────────────────────┘
```

Keep connectors as independent, swappable plugins behind a common interface
(`fetch() -> list[PriceRecord]`). Adding a retailer should never touch the
profit engine.

---

## 4. Data sources

### Sell-side — CeX / WeBuy
- CeX exposes a JSON API used by its own site/app (the `webuy.io` endpoints):
  search boxes, box detail, prices, "we are buying" flags, store stock. This is
  the cleanest data source in the whole system — **start here.**
- Capture per item: `boxId`, name, category, **cash price**, **voucher price**,
  sell price (for reference/margin context), and whether buying is currently
  enabled/limited.
- **Validate the API terms** before relying on it (see RISKS). Have a polite
  rate-limited fetch + caching layer regardless.

### Buy-side — retailers
Pick a small number to start. Two integration styles:
- **Official / affiliate product feeds** (cleanest, ToS-friendly): Amazon Product
  Advertising API, eBay API, affiliate networks (Awin, Rakuten) that expose
  product feeds for retailers like Currys, Argos, AO, etc. Preferred where
  available.
- **Scraping** (last resort): brittle, and many retailers' ToS forbid it. If used,
  isolate it, respect robots.txt/rate limits, and treat it as best-effort.

Start with **1–2 retailers** whose categories overlap heavily with CeX
(electronics, gaming, phones) and who run frequent sales/clearance.

### Discount / cashback / Perkbox layer
- **Discount codes:** maintain a small curated table to start (manual entry is
  fine for MVP); later integrate a voucher-code source.
- **Cashback:** TopCashback / Quidco publish rates per retailer; model as a
  simple `% back` per retailer (often delayed payout — flag it as deferred cash).
- **Perkbox / employee discounts:** model as a per-retailer discount % that only
  applies to your account. **See RISKS — likely restricted to personal use.**

---

## 5. The matching problem (the hard bit)

CeX names items their own way ("Apple iPhone 13 128GB Midnight, Unlocked A");
retailers name them differently. Matching strategy, in priority order:

1. **Barcode / EAN / GTIN** — gold standard when both sides expose it.
2. **Brand + model number** (normalised — strip case, punctuation).
3. **Fuzzy name match** with a confidence score; anything below a threshold goes
   to a **manual review queue** rather than auto-trading.
4. **Condition mapping** — CeX grades (A/B/C) and buys *used/working*; retail is
   *new*. New-bought items map to CeX grade A pricing, but **verify CeX's
   "boxed/new" vs "unboxed" distinction per category** — it materially changes the
   price.

Never auto-flag a deal off a low-confidence match — a wrong match produces
fake profit and real losses.

---

## 6. Profit engine

See [`DATA-MODEL.md`](./DATA-MODEL.md) for the full formula and fields. Summary:

```
net_cost      = retail_price
                − sale_reduction
                − discount_code_value
                − (retail_price × cashback_pct)        # deferred
                − (retail_price × perkbox_pct)
                + shipping
                + payment/giftcard_cost_adjustment

cash_margin   = cex_cash_price    − net_cost
vch_margin    = cex_voucher_price − net_cost           # only "real" if you'll spend the voucher
roi_pct       = cash_margin / net_cost
```

Rules the engine must enforce:
- **Voucher margin is not cash.** Show it separately; don't rank a voucher-only
  deal as if it were money unless you have a use for CeX credit.
- **Cashback is deferred and not guaranteed** — flag it; optionally show
  margin both with and without it.
- **Confidence gate** — suppress deals built on low-confidence matches or stale
  prices (price older than N hours).
- **Minimum thresholds** — configurable floor on £ profit and % ROI so the feed
  isn't noise.

---

## 7. MVP → roadmap

### Phase 0 — Decisions (no code)
Answer the open questions (§9) and the RISKS items. This gates everything.

### Phase 1 — Read-only price spotter (the MVP)
- CeX connector only + **one** retailer (via official/affiliate feed if possible).
- Barcode/model matching with manual review queue.
- Profit engine with manually-entered discount codes + a single Perkbox % field.
- Simple web dashboard: sortable table of opportunities, filters, margin columns.
- Goal: prove that real, positive-margin opportunities actually appear, and how
  often. **This phase is mostly about validating the thesis cheaply.**

### Phase 2 — Alerting + more sources
- Add 2–3 more retailers and a cashback model.
- Push alerts (Telegram/email/web push) for new opportunities above threshold.
- Discount-code feed integration.

### Phase 3 — Tracking & learning
- Log actual buys/sells; compare realised vs predicted margin.
- Model CeX **price decay** (their buy price drops as their stock rises) and
  per-item trade-in caps.
- Basic P&L / tax-export report.

### Phase 4 (optional) — Scale
- More categories, smarter matching (embeddings for fuzzy match), portfolio view,
  multi-user.

Resist building Phase 2+ until Phase 1 shows the opportunities are real and
frequent enough to be worth it.

---

## 8. Tech stack (proposal)

| Concern | Choice | Why |
|---|---|---|
| Language | **Python** | Best ecosystem for scraping/data/matching; fast to prototype |
| Scheduler | cron / APScheduler → later a queue (Celery/RQ) | Simple first |
| Store | **Postgres** | Relational fits products/prices/deals; good enough at scale |
| Matching | rapidfuzz (fuzzy) + barcode lookup | Cheap, effective |
| API/back end | FastAPI | Lightweight, typed |
| Front end | Start with a server-rendered table or a small React/Next app | MVP needs little |
| Alerts | Telegram bot (easiest) + email | Low friction |
| Hosting | Single small VPS or a cheap container host; this repo (GitHub Pages) can host a **read-only static dashboard** later | — |

GitHub Pages can't run the back end (it's static hosting), so the engine runs
elsewhere; Pages could host a static read-only view that reads a published JSON
snapshot if you ever want a public-facing page.

---

## 9. Open questions for Matt

These change the design — worth answering before Phase 1:

1. **Geography & scale:** UK only? Just you, or multiple people trading?
2. **CeX logistics:** Post items to CeX (WeBuy postal) or walk into stores? Postal
   is automatable/scalable; stores cap volume and need travel. Are you aware of
   their per-person trade-in / ID limits?
3. **Capital & cadence:** Rough budget per cycle, and how much time per week? This
   sets how many opportunities/sources are worth chasing.
4. **Cash vs voucher:** Do you have any use for CeX store credit, or is this
   cash-only (which roughly halves the qualifying opportunities)?
5. **Retailer priority:** Which retailers do you already shop / have accounts &
   cashback with? Start there.
6. **Perkbox reality check:** Are you OK proceeding given Perkbox/your employer's
   terms almost certainly intend those discounts for *personal* use, not resale?
   (See RISKS — I'd treat Perkbox as a "maybe," not a foundation.)
7. **Tax:** Are you set up (or willing to register) as a sole trader / declare this
   to HMRC? It's taxable trading income from £1 of profit beyond the £1,000
   trading allowance.

Answer these and I'll turn Phase 1 into a concrete build task list.
