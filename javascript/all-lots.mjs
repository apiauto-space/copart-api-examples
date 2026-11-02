// Collect Copart lots across pages with the cursor, as an async generator.
//
//   export APIAUTO_KEY=...
//   node all-lots.mjs
//
// The filter runs on your side, so the quota also pays for the lots of the other auction on
// each page: maxRecords is the budget, want is how many Copart lots you need.

if (!process.env.APIAUTO_KEY) throw new Error("Set the APIAUTO_KEY environment variable");

const BASE = "https://api.apiauto.space/v1";
const SOURCE = "copart";
const SORT = "first_seen"; // on 2 November 2026 this order put the most Copart lots first; it is no contract
const PAGE_SIZE = 20; // up to 20 on the demo key, up to 100 on paid plans
let spent = 0;

async function* lots(filters, { want, maxRecords }) {
  const params = new URLSearchParams({ market: "us", sort: SORT, ...filters });
  let found = 0;
  let tries = 0;
  const seen = new Set();
  while (spent < maxRecords) {
    params.set("limit", String(Math.min(PAGE_SIZE, maxRecords - spent)));
    const response = await fetch(`${BASE}/cars?${params}`, {
      headers: { "X-API-Key": process.env.APIAUTO_KEY },
      redirect: "error", // the key must not follow a redirect to another host
      signal: AbortSignal.timeout(30000),
    });
    if ((response.status === 429 || response.status === 503) && ++tries < 5) {
      // Wait as long as the API asks, at most 60 s; 1 s when it does not give a number.
      const value = response.headers.get("Retry-After") ?? "";
      const seconds = /^\d+$/.test(value) ? Math.min(Number(value), 60) : 1;
      await new Promise((resolve) => setTimeout(resolve, seconds * 1000));
      continue;
    }
    if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
    tries = 0;

    const page = await response.json();
    spent += page.items.length;
    for (const car of page.items) {
      if (car.source !== SOURCE) continue;
      yield car;
      if (++found >= want) return;
    }
    if (page.items.length === 0 || !page.next_cursor || seen.has(page.next_cursor)) return;
    seen.add(page.next_cursor);
    params.set("cursor", page.next_cursor);
  }
}

let kept = 0;
for await (const car of lots(
  { brand: "Toyota", model: "RAV4", year_min: "2020" },
  { want: 10, maxRecords: 60 },
)) {
  kept++;
  console.log(car.id, car.title, car.raw.sale_date);
}
console.log(`kept ${kept} ${SOURCE} lots, spent ${spent} records`);
