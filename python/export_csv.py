"""Export Copart lots to CSV (opens in Excel and Google Sheets).

    pip install httpx
    export APIAUTO_KEY=...
    python export_csv.py --brand Ford --year-min 2020 --max-records 100 > lots.csv

--max-records is the budget: the quota also pays for lots of the other auction on each page.
"""

import argparse
import csv
import os
import sys
import time

import httpx

SOURCE = "copart"
SORT = "first_seen"  # on 2 November 2026 this order put the most Copart lots first; it is no contract

parser = argparse.ArgumentParser()
parser.add_argument("--brand")
parser.add_argument("--model")
parser.add_argument("--year-min", type=int)
parser.add_argument("--max-records", type=int, default=100, help="stop after reading this many lots")
parser.add_argument("--limit", type=int, default=20, help="lots per page: 20 on the demo, up to 100")
args = parser.parse_args()

api = httpx.Client(
    base_url="https://api.apiauto.space/v1",
    headers={"X-API-Key": os.environ["APIAUTO_KEY"]},
    timeout=60,
)
params = {"market": "us", "sort": SORT, "brand": args.brand, "model": args.model, "year_min": args.year_min}
params = {key: value for key, value in params.items() if value is not None}

columns = [
    "id", "title", "vin", "brand", "model", "year", "mileage_km", "fuel", "transmission", "engine_cc",
    "body_type", "color", "region", "city", "lot_number", "damage_main", "damage_second", "title_doc",
    "bid", "buy_now", "sale_date", "location_branch", "keys_available", "photo_count",
]
raw_columns = (
    "lot_number", "damage_main", "damage_second", "title_doc", "bid", "buy_now", "sale_date",
    "location_branch", "keys_available",
)


def get_page(query: dict) -> dict:
    """GET with up to 5 tries on 429 (rate limit) and 503, waiting Retry-After, at most 60 s."""
    for attempt in range(5):
        response = api.get("/cars", params=query)
        if response.status_code not in (429, 503) or attempt == 4:
            response.raise_for_status()
            return response.json()
        value = response.headers.get("Retry-After", "")
        time.sleep(min(int(value[:9]), 60) if value.isdecimal() else 1)


def safe_cell(value):
    """Listing text comes from strangers: a leading ' stops Excel running it as a formula."""
    if isinstance(value, str) and (value[:1] in ("\t", "\r") or value.lstrip()[:1] in ("=", "+", "-", "@")):
        return "'" + value
    return value


def safe_row(row: dict) -> dict:
    return {name: safe_cell(value) for name, value in row.items()}


writer = csv.DictWriter(sys.stdout, fieldnames=columns, extrasaction="ignore")
writer.writeheader()

seen: set = set()
spent = written = 0
while spent < args.max_records:
    params["limit"] = min(args.limit, args.max_records - spent)
    page = get_page(params)
    spent += len(page["items"])
    for car in page["items"]:
        if car["source"] != SOURCE:
            continue
        writer.writerow(safe_row({
            **car,
            "region": car["location"]["region"],
            "city": car["location"]["city"],
            **{name: car["raw"].get(name) for name in raw_columns},
        }))
        written += 1
    cursor = page["next_cursor"]
    if not page["items"] or not cursor or cursor in seen:
        break
    seen.add(cursor)
    params["cursor"] = cursor

print(f"exported {written} {SOURCE} lots, spent {spent} records", file=sys.stderr)
