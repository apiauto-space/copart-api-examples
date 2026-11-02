# Copart API examples

Working curl, Python, JavaScript and PHP examples for reading lots of Copart, a US auction of damaged and used vehicles, as JSON through
[apiauto.space](https://apiauto.space/en/copart-api/), a read-only REST API: VIN, damage, title, bid and sale date.

Copart works with partners through private integrations, such as [claim assignments in Duck Creek](https://www.duckcreek.com/content-exchange/copart_assignment_processing_service_(claims)/), but on 2026-11-02 we found no public, self-serve API for its lots. apiauto.space is an independent service, not a Copart product.

The API is paid from $59 a month for 100,000 cars. A free demo key works for 1 day: 100 requests, up to 20
cars per request, no card. It comes from the Telegram bot
[@apiautospace_bot](https://t.me/apiautospace_bot?start=demo).

```bash
curl -s "https://api.apiauto.space/v1/cars/copart:70370576" -H "X-API-Key: $APIAUTO_KEY"
```

A real answer, shortened, with the VIN masked; the full one is in [copart-lot.json](https://github.com/apiauto-space/copart-api-examples/blob/main/samples/copart-lot.json):

```json
{
  "id": "copart:70370576",
  "source": "copart",
  "title": "2025 Toyota Camry",
  "mileage_km": 41822,
  "vin": "4T1DAACK8SU******",
  "price": {
    "amount": null,
    "currency": "USD"
  },
  "raw": {
    "bid": 275.0,
    "sale_date": "2026-11-03T19:00:00+00:00",
    "damage_main": "rear",
    "title_doc": "salvage"
  }
}
```

Last verified: 2026-11-02, every example below run against the live API.

## Quick start

1. Get the demo key in [the bot](https://t.me/apiautospace_bot?start=demo) and save it:
   `export APIAUTO_KEY=your-key`.
2. Search `market=us` and keep the Copart lots. **The API has no filter by auction:** `source=copart` in the
   URL is ignored, and Copart lots come together with IAAI lots.

```bash
curl -s "https://api.apiauto.space/v1/cars?market=us&brand=Toyota&model=Camry&year_min=2020&sort=first_seen&limit=20" \
  -H "X-API-Key: $APIAUTO_KEY" \
  | jq '.items[] | select(.source == "copart") | {id, title, vin, sale: .raw.sale_date}'
```

Call the API from your server: CORS is off, because a key in browser code is visible to everyone. Every
request is in [curl/README.md](https://github.com/apiauto-space/copart-api-examples/blob/main/curl/README.md).

| Task | Python | JavaScript | PHP |
|---|---|---|---|
| Search and keep Copart lots | [first_request.py](https://github.com/apiauto-space/copart-api-examples/blob/main/python/first_request.py) | [first-request.mjs](https://github.com/apiauto-space/copart-api-examples/blob/main/javascript/first-request.mjs) | [first-request.php](https://github.com/apiauto-space/copart-api-examples/blob/main/php/first-request.php) |
| Walk pages with a budget of records | [all_lots.py](https://github.com/apiauto-space/copart-api-examples/blob/main/python/all_lots.py) | [all-lots.mjs](https://github.com/apiauto-space/copart-api-examples/blob/main/javascript/all-lots.mjs) | |
| New and removed lots | [sync_catalog.py](https://github.com/apiauto-space/copart-api-examples/blob/main/python/sync_catalog.py) | [change-feed.mjs](https://github.com/apiauto-space/copart-api-examples/blob/main/javascript/change-feed.mjs) | [sync-catalog.php](https://github.com/apiauto-space/copart-api-examples/blob/main/php/sync-catalog.php) |
| Export to CSV | [export_csv.py](https://github.com/apiauto-space/copart-api-examples/blob/main/python/export_csv.py) | | |
| Download photos | [download_photos.py](https://github.com/apiauto-space/copart-api-examples/blob/main/python/download_photos.py) | | |

Real answers, shortened, without IAAI lots, with VINs (last 6 characters) and photo signatures masked:
[a page](https://github.com/apiauto-space/copart-api-examples/blob/main/samples/cars-page-us-copart.json), [change feed](https://github.com/apiauto-space/copart-api-examples/blob/main/samples/changes-us-copart.json).

## Fields

| Field | Meaning |
|---|---|
| `id`, `source`, `source_id` | `copart:70370576`, `copart`, the lot number |
| `vin` | the lot's VIN |
| `mileage_km`, `raw.odometer_mi` | kilometres, and miles as given |
| `price`, `price_usd` | the buy-now price or `null` |
| `raw.bid`, `raw.buy_now`, `raw.sale_date` | current bid, buy-now price, sale time in UTC |
| `raw.damage_main`, `raw.damage_second`, `raw.title_doc` | damage and title type, canonical values |
| `photos`, `photo_count` | signed links, valid about a day: keep the id, not the link |

Full schema: [openapi.json](https://api.apiauto.space/openapi.json), [the record](https://apiauto.space/en/docs/record/).

## Units and gotchas

- **Filtering by auction costs quota.** Paid plans count every lot returned, including IAAI lots you drop;
  `count` counts both auctions. In the change feed, keep `car_id` values starting with `copart:`.
- **The sort decides the waste.** Lots come in loading order, so a page can hold no Copart lots at all. A page of 20
  Toyota Camry from 2020 on 2 November 2026 held 0 Copart lots with the default `-first_seen`,
  19 with `first_seen` and 12 with `price`. It is no contract: keep the check on `source`.
- **Miles are converted** to `mileage_km`; some lots carry a placeholder odometer of a few kilometres.
- **A bid is not a price.** `price` is often `null` while `raw.bid` runs. Only lots with sales ahead are listed.
- `listing_url` is `null` for US lots. `location.country` is `US` even for the few yards in Canada.
- **`disappeared` is not "sold":** the source does not say why a lot left. Listing text is untrusted input: escape it
  in HTML and in spreadsheets.

## Data freshness

The refresh target is hourly. That is a target, not a promise: the real age is in the
`X-Data-Age-Seconds` header of every answer and in `GET /v1/references/markets`. When we read it on 2026-11-02, the Copart and IAAI copy was
23 min old, and the API marks it stale after 6 h 0 min.

## Limits

Up to 100 cars per request (20 on the demo). Cursor pagination only. References, usage and photos are free. Over the
rate limit the API answers 429 with `Retry-After`. Details: [limits](https://apiauto.space/en/docs/limits/).

## Pricing

| Plan | Price | Cars a month | Markets | Requests a second | Change feed |
|---|---|---|---|---|---|
| Demo | free, 1 day, no card | 100 requests | all 3 | — | yes |
| Start | $59 a month | 100,000 | 1 | 2 | no |
| Pro | $149 a month | 500,000 | 2 | 5 | yes |
| Max | $299 a month | 2,000,000 | 3 | 10 | yes |

`us` is one market, Copart and IAAI together. Current prices and Enterprise terms: [apiauto.space/en/#pricing](https://apiauto.space/en/#pricing).

## Other languages

| Language | Package | Repository |
|---|---|---|
| Python | `pip install apiauto-space` | [apiauto-python](https://github.com/apiauto-space/apiauto-python) |
| JavaScript / TypeScript | `npm i apiauto` | [apiauto-js](https://github.com/apiauto-space/apiauto-js) |
| PHP | `composer require apiauto/apiauto` | [apiauto-php](https://github.com/apiauto-space/apiauto-php) |
| Go | `go get github.com/apiauto-space/apiauto-go` | [apiauto-go](https://github.com/apiauto-space/apiauto-go) |

## Not affiliated

apiauto.space is not affiliated with or endorsed by Copart. Lot data and photos belong to the auction and the
sellers. The examples are [MIT-licensed](https://github.com/apiauto-space/copart-api-examples/blob/main/LICENSE).
