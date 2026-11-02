"""Search Copart lots by make, model and year: VIN, damage, title, bid and sale date.

The API has no auction filter. market=us returns Copart and IAAI lots together and every record
says where it comes from in `source`, so this script keeps Copart lots on its side.

    pip install httpx
    export APIAUTO_KEY=...        # the demo key from https://t.me/apiautospace_bot?start=demo
    python first_request.py
"""

import os

import httpx

SOURCE = "copart"
SORT = "first_seen"  # on 2 November 2026 this order put the most Copart lots first; it is no contract

api = httpx.Client(
    base_url="https://api.apiauto.space/v1",
    headers={"X-API-Key": os.environ["APIAUTO_KEY"]},
    timeout=30,
)

response = api.get(
    "/cars",
    params={
        "market": "us",        # us = Copart and IAAI
        "brand": "Toyota",
        "model": "Camry",
        "year_min": 2020,
        "has_photos": True,
        "sort": SORT,
        "limit": 20,           # up to 20 on the demo key, up to 100 on paid plans
    },
)
response.raise_for_status()
page = response.json()

lots = [car for car in page["items"] if car["source"] == SOURCE]
print(f"{len(lots)} {SOURCE} lots of {len(page['items'])} on this page")
for car in lots:
    raw = car["raw"]  # auction-only fields
    print(
        f"{car['id']:<18} {car['title']:<24} VIN {car['vin'] or '-':<18} "
        f"damage: {raw.get('damage_main') or '-':<8} title: {raw.get('title_doc') or '-':<10} "
        f"bid: {raw.get('bid') or '-':<7} sale: {(raw.get('sale_date') or '-')[:16]}"
    )

# Every answer says how much quota is left and how old the market copy is.
print("records left:", response.headers.get("X-Quota-Remaining"))
print("data age, s:", response.headers.get("X-Data-Age-Seconds"))
