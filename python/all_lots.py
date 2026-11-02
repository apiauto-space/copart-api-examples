"""Collect Copart lots across pages with the cursor, and show what it costs.

The filter runs on your side, so the quota also pays for the lots of the other auction on each
page. max_records is the budget of records, want is how many Copart lots you need.

    pip install httpx
    export APIAUTO_KEY=...
    python all_lots.py Toyota RAV4
"""

import os
import sys
import time
from collections.abc import Iterator

import httpx

SOURCE = "copart"
SORT = "first_seen"  # on 2 November 2026 this order put the most Copart lots first; it is no contract
PAGE_SIZE = 20  # up to 20 on the demo key, up to 100 on paid plans

api = httpx.Client(
    base_url="https://api.apiauto.space/v1",
    headers={"X-API-Key": os.environ["APIAUTO_KEY"]},
    timeout=30,
)
spent = 0


def get_page(params: dict) -> dict:
    """GET with up to 5 tries on 429 (rate limit) and 503, waiting Retry-After, at most 60 s."""
    for attempt in range(5):
        response = api.get("/cars", params=params)
        if response.status_code not in (429, 503) or attempt == 4:
            response.raise_for_status()
            return response.json()
        value = response.headers.get("Retry-After", "")
        time.sleep(min(int(value[:9]), 60) if value.isdecimal() else 1)


def lots(filters: dict, want: int, max_records: int) -> Iterator[dict]:
    global spent
    params = {"market": "us", "sort": SORT, **filters}
    found = 0
    seen: set = set()
    while spent < max_records:
        params["limit"] = min(PAGE_SIZE, max_records - spent)
        page = get_page(params)
        spent += len(page["items"])
        for car in page["items"]:
            if car["source"] == SOURCE:
                yield car
                found += 1
                if found >= want:
                    return
        cursor = page["next_cursor"]
        if not page["items"] or not cursor or cursor in seen:
            return
        seen.add(cursor)
        params["cursor"] = cursor


brand = sys.argv[1] if len(sys.argv) > 1 else "Toyota"
model = sys.argv[2] if len(sys.argv) > 2 else "RAV4"
kept = 0
for car in lots({"brand": brand, "model": model, "year_min": 2020}, want=10, max_records=60):
    kept += 1
    print(car["id"], car["title"], car["raw"].get("sale_date"))
print(f"kept {kept} {SOURCE} lots, spent {spent} records")
