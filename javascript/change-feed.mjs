// New and removed Copart lots in the last 24 hours, from the change feed.
//
//   export APIAUTO_KEY=...
//   node change-feed.mjs
//
// The feed of market=us holds both auctions: the prefix of car_id tells them apart. Each event
// returned costs one record, including events of the other auction. The change feed
// (/v1/changes) comes with Pro, Max and the demo key.

if (!process.env.APIAUTO_KEY) throw new Error("Set the APIAUTO_KEY environment variable");

const params = new URLSearchParams({
  market: "us",
  since: new Date(Date.now() - 24 * 3600 * 1000).toISOString(),
  limit: "20",
});

const response = await fetch(`https://api.apiauto.space/v1/changes?${params}`, {
  headers: { "X-API-Key": process.env.APIAUTO_KEY },
  redirect: "error", // the key must not follow a redirect to another host
  signal: AbortSignal.timeout(30000),
});
if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);

const { items, next_cursor: nextCursor } = await response.json();
const events = items.filter((event) => event.car_id.startsWith("copart:"));
console.log(`${events.length} copart events of ${items.length} on this page`);
for (const event of events) {
  console.log(event.at, event.type, event.car_id, event.new_price ?? "");
}
if (nextCursor) console.log("next page: pass cursor =", nextCursor);
