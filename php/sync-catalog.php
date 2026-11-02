<?php
// Keep a catalog of Copart lots in MySQL/PostgreSQL in sync: import once, then poll the change
// feed hourly. Run it from cron: `0 * * * * php sync-catalog.php`. PHP 7.4+ with curl.
//
// market=us and its feed hold Copart and IAAI together, so lots are kept by `source` and events by
// the "copart:" prefix of car_id. The SQL is left as comments: plug in your own database layer.
// MAX_RECORDS caps the first import: the quota also pays for lots of the other auction.

if (PHP_SAPI !== "cli") {
    exit("Run this example from the command line. Listing data is untrusted: escape it before showing it in HTML.\n");
}

const API = "https://api.apiauto.space/v1";
const SOURCE = "copart";
const SORT = "first_seen"; // on 2 November 2026 this order put the most Copart lots first; it is no contract
const STATE_FILE = __DIR__ . "/since.txt";
const MAX_RECORDS = 200;

function apiauto_get(string $path, array $params = []): array
{
    $key = getenv("APIAUTO_KEY");
    if (!$key) {
        throw new RuntimeException("Set the APIAUTO_KEY environment variable");
    }
    for ($attempt = 1; ; $attempt++) {
        $ch = curl_init(API . $path . ($params ? "?" . http_build_query($params) : ""));
        curl_setopt_array($ch, [
            CURLOPT_HTTPHEADER => ["X-API-Key: " . $key],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER => true,
            CURLOPT_TIMEOUT => 60,
        ]);
        $response = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $body = substr($response, $headerSize);

        if (($status === 429 || $status === 503) && $attempt < 5) {
            // Wait as long as the API asks, at most 60 s; 1 s when it does not give a number.
            preg_match('/^retry-after:\s*(\d+)\s*$/mi', substr($response, 0, $headerSize), $m);
            sleep(min((int)($m[1] ?? 1), 60));
            continue;
        }
        if ($status !== 200) {
            throw new RuntimeException("HTTP $status: $body");
        }
        return json_decode($body, true);
    }
}

function next_cursor(array $page, array &$seen): ?string
{
    // Null at the end, on an empty page or a repeated cursor.
    $cursor = $page["next_cursor"] ?? null;
    if (!$page["items"] || !$cursor || isset($seen[$cursor])) {
        return null;
    }
    $seen[$cursor] = true;
    return $cursor;
}

function save_lot(array $car): void
{
    // INSERT ... ON CONFLICT (id) DO UPDATE: id, title, vin, raw.damage_main, raw.title_doc,
    // raw.sale_date, raw.bid, photos (refresh them when showing the lot: links live about a day).
    echo "save {$car['id']} {$car['title']}\n";
}

if (!file_exists(STATE_FILE)) {
    // The first run: the selection by the cursor.
    $since = gmdate("Y-m-d\TH:i:s\Z");
    $pageSize = 20; // up to 100 on paid plans
    $params = ["market" => "us", "brand" => "Toyota", "sort" => SORT];
    $spent = 0;
    $seen = [];
    do {
        $params["limit"] = min($pageSize, MAX_RECORDS - $spent);
        $page = apiauto_get("/cars", $params);
        $spent += count($page["items"]);
        foreach ($page["items"] as $car) {
            if ($car["source"] === SOURCE) {
                save_lot($car);
            }
        }
        $params["cursor"] = next_cursor($page, $seen);
    } while ($params["cursor"] && $spent < MAX_RECORDS);
} else {
    // Every next run: only what changed since the last one.
    $since = trim(file_get_contents(STATE_FILE));
    $now = gmdate("Y-m-d\TH:i:s\Z");
    $params = ["market" => "us", "since" => $since, "limit" => 20]; // up to 100 on paid plans
    $seen = [];
    do {
        $page = apiauto_get("/changes", $params);
        foreach ($page["items"] as $event) {
            if (strpos($event["car_id"], SOURCE . ":") !== 0) {
                continue;
            }
            switch ($event["type"]) {
                case "added":
                    save_lot(apiauto_get("/cars/" . $event["car_id"]));
                    break;
                case "disappeared": // left the catalog; the source does not say why
                    // UPDATE lots SET is_active = false WHERE id = $event["car_id"]
                    echo "gone {$event['car_id']}\n";
                    break;
                default: // price_drop, price_up
                    echo "{$event['type']} {$event['car_id']}: {$event['old_price']} → {$event['new_price']}\n";
            }
        }
        $params["cursor"] = next_cursor($page, $seen);
    } while ($params["cursor"]);
    $since = $now;
}

file_put_contents(STATE_FILE, $since);
