// Search Copart lots by make, model and year: VIN, damage, title, bid and sale date.
//
//   export APIAUTO_KEY=...   # the demo key from https://t.me/apiautospace_bot?start=demo
//   node first-request.mjs Toyota Camry   # Node 18+, no dependencies
//
// The API has no auction filter: market=us returns Copart and IAAI lots together and every
// record says where it comes from in `source`, so the script keeps Copart lots on its side.

if (!process.env.APIAUTO_KEY) throw new Error("Set the APIAUTO_KEY environment variable");

const SOURCE = "copart";
const SORT = "first_seen"; // on 2 November 2026 this order put the most Copart lots first; it is no contract
const [brand = "Toyota", model = "Camry"] = process.argv.slice(2);
const params = new URLSearchParams({
  market: "us", // us = Copart and IAAI
  brand,
  model,
  year_min: "2020",
  has_photos: "true",
  sort: SORT,
  limit: "20", // up to 20 on the demo key, up to 100 on paid plans
});

const response = await fetch(`https://api.apiauto.space/v1/cars?${params}`, {
  headers: { "X-API-Key": process.env.APIAUTO_KEY },
  redirect: "error", // the key must not follow a redirect to another host
  signal: AbortSignal.timeout(30000),
});
if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);

const { items } = await response.json();
const lots = items.filter((car) => car.source === SOURCE);
console.log(`${lots.length} ${SOURCE} lots of ${items.length} on this page`);
for (const car of lots) {
  const { raw } = car; // auction-only fields
  console.log(
    [
      car.id,
      car.title,
      `VIN ${car.vin ?? "—"}`,
      `damage: ${raw.damage_main ?? "—"}`,
      `title: ${raw.title_doc ?? "—"}`,
      `bid: ${raw.bid ?? "—"}`,
      `sale: ${raw.sale_date?.slice(0, 16) ?? "—"}`,
      `${car.location.city}, ${car.location.region}`,
    ].join(" · "),
  );
}
