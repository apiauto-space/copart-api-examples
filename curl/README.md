# Copart API with curl

Copart requests of the [apiauto.space API](https://apiauto.space/en/docs/) from the command line.
Put the key in a variable first; the demo key comes from
[the Telegram bot](https://t.me/apiautospace_bot?start=demo) (one day, 100 requests).

```bash
export APIAUTO_KEY=your-key
API=https://api.apiauto.space/v1
```

On a shared server other users can read a key from the command line in the process list. Send the
header through stdin there (curl 7.55+):

```bash
printf 'X-API-Key: %s\n' "$APIAUTO_KEY" | curl -s -H @- "$API/usage"
```

## Lots: how to keep Copart only

Copart lots live in `market=us` together with IAAI lots. The API has no auction filter: a
`source=copart` parameter in the URL is ignored and changes nothing. Every record has a `source`
field, so keep the lots you need on your side, here with [jq](https://jqlang.org/):

```bash
curl -s "$API/cars?market=us&brand=Toyota&model=Camry&year_min=2020&has_photos=true&sort=first_seen&limit=20" \
  -H "X-API-Key: $APIAUTO_KEY" \
  | jq '.items[] | select(.source == "copart")
        | {id, title, vin, damage: .raw.damage_main, title_doc: .raw.title_doc,
           bid: .raw.bid, sale: .raw.sale_date}'

# The next page: pass next_cursor of the previous answer
curl -s "$API/cars?market=us&brand=Toyota&model=Camry&sort=first_seen&limit=20&cursor=PASTE_NEXT_CURSOR" \
  -H "X-API-Key: $APIAUTO_KEY"
```

The quota counts every lot returned, including lots of the other auction, and `count` in the answer
counts both auctions. The sort matters: a page can hold no Copart lots at all. `sort=first_seen` put
the most Copart lots first on 2 November 2026, which is how the catalog was loaded, not a contract.

Filters: `brand`, `model`, `trim`, `year_min`, `year_max`, `price_min`, `price_max`, `price_usd_min`,
`price_usd_max` (the buy-now price, dollars), `mileage_max` (km), `fuel`, `transmission`, `body_type`,
`has_photos`, `is_active`, `q`. Sort: `-first_seen` (default), `first_seen`, `price`, `-price`, `year`,
`-year`, `mileage`, `-mileage`.

## One lot

A lot id is `copart:` plus the lot number, so this request needs no filter:

```bash
curl -s "$API/cars/copart:70370576" -H "X-API-Key: $APIAUTO_KEY"
```

A lot that left the catalog answers with `is_active: false` for 14 more days, then 404. The id in
this example may be gone by the time you read this: take a fresh one from a search.

## Change feed: new lots, removed lots, price changes

The feed of `market=us` holds both auctions; `car_id` starts with the auction's name:

```bash
curl -s "$API/changes?market=us&since=2026-11-02T00:00:00Z&limit=100" \
  -H "X-API-Key: $APIAUTO_KEY" \
  | jq '.items[] | select(.car_id | startswith("copart:"))'
```

Event types: `added`, `disappeared` (left the catalog; the source does not say why), `price_drop`, `price_up`.

## References (free, no quota)

Makes and models are counted for `market=us` as a whole, not per auction.

```bash
curl -s "$API/references/brands?market=us" -H "X-API-Key: $APIAUTO_KEY"
curl -s "$API/references/models?market=us&brand=Toyota" -H "X-API-Key: $APIAUTO_KEY"
curl -s "$API/references/dictionaries" -H "X-API-Key: $APIAUTO_KEY"   # fuel, damage, title_doc…
curl -s "$API/references/markets" -H "X-API-Key: $APIAUTO_KEY"        # freshness and counts
curl -s "$API/usage" -H "X-API-Key: $APIAUTO_KEY"                     # your quota
```

## Quota headers

```bash
curl -si "$API/cars?market=us&limit=1" -H "X-API-Key: $APIAUTO_KEY" | grep -i '^x-'
```

Each answer carries `X-Quota-Limit`, `X-Quota-Remaining`, `X-Quota-Reset`, `X-RateLimit-Limit` and
`X-Data-Age-Seconds`. Errors are JSON: `{"error": "rate_limited", "retry_after": 1}`; the codes are on
[apiauto.space/en/docs/errors/](https://apiauto.space/en/docs/errors/).
