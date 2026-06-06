# Draft Data Model & Profit Formula

A first sketch of entities for Phase 1. Not final — refine once the CeX connector
is built and we see the real shape of the data.

## Entities

### Product (canonical)
The thing both sides map to.
```
id              uuid
ean             string?          # barcode / GTIN — primary match key
brand           string
model           string
name            string           # human-readable canonical name
category        string           # phone, console, game, gpu, ...
```

### CexListing (sell-side)
```
id              uuid
product_id      fk -> Product
cex_box_id      string           # WeBuy boxId
condition_grade string           # A / B / C (and boxed/unboxed variant)
cash_price      decimal
voucher_price   decimal
sell_price      decimal          # CeX retail, for context
is_buying       bool             # "we are buying" flag
fetched_at      timestamp
```

### RetailListing (buy-side)
```
id              uuid
product_id      fk -> Product
retailer        string           # amazon, currys, argos, ...
url             string
list_price      decimal          # before deal-specific reductions
sale_price      decimal?         # current sale/clearance price if any
in_stock        bool
fetched_at      timestamp
source          enum(feed|affiliate|scrape)
```

### Discount
```
id              uuid
retailer        string
type            enum(code|cashback|perkbox|giftcard)
value_type      enum(percent|fixed)
value           decimal
code            string?
stackable       bool             # can it combine with others? (verify per retailer)
deferred        bool             # true for cashback (paid later, not guaranteed)
personal_only   bool             # true for perkbox/employee — flags ToS risk
valid_until     timestamp?
notes           string?
```

### Opportunity (computed)
```
id              uuid
product_id      fk -> Product
cex_listing_id  fk -> CexListing
retail_listing_id fk -> RetailListing
applied_discount_ids  [fk]
net_cost        decimal
cash_margin     decimal
voucher_margin  decimal
roi_pct         decimal
match_confidence decimal         # 0..1 — gate auto-surfacing on this
flags           [string]         # e.g. ["voucher_only","cashback_deferred","low_confidence"]
computed_at     timestamp
```

### Trade (Phase 3 — actuals)
```
id              uuid
opportunity_id  fk
bought_price    decimal          # what you actually paid
sold_price      decimal          # what CeX actually gave
sold_as         enum(cash|voucher)
cashback_received decimal?
status          enum(bought|sold|cashback_pending|closed)
realised_margin decimal
notes           string
```

## Profit formula

```
sale_reduction  = list_price − sale_price            # if on sale, else 0
code_value      = resolve(code discount)
cashback_value  = sale_price × cashback_pct          # deferred, optional in margin
perkbox_value   = sale_price × perkbox_pct           # personal_only — flag
giftcard_adj    = sale_price × giftcard_discount_pct # if buying via discounted gift cards

net_cost        = sale_price
                  − code_value
                  − perkbox_value
                  − giftcard_adj
                  + shipping
                  − (include_cashback ? cashback_value : 0)

cash_margin     = cex_cash_price    − net_cost
voucher_margin  = cex_voucher_price − net_cost
roi_pct         = cash_margin / net_cost
```

### Surfacing rules
- Only surface if `match_confidence >= threshold` (else → manual review queue).
- Rank primarily by **cash_margin**, then `roi_pct`.
- Show `voucher_margin` separately; never blend it into cash ranking unless the
  user has opted in to "I'll spend CeX credit."
- Apply a configurable **minimum cash_margin** and **minimum roi_pct** floor.
- Suppress listings whose `fetched_at` is older than N hours (stale price).
- Surface flags prominently: `voucher_only`, `cashback_deferred`,
  `personal_only_discount`, `low_confidence`, `cex_not_buying`.
