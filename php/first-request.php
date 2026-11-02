<?php
// Search Copart lots: VIN, damage, title, bid and sale date. PHP 7.4+ with the curl extension.
//
//   export APIAUTO_KEY=...   # the demo key from https://t.me/apiautospace_bot?start=demo
//   php first-request.php
//
// The API has no auction filter: market=us returns Copart and IAAI lots together and every
// record says where it comes from in `source`, so the script keeps Copart lots on its side.

if (PHP_SAPI !== "cli") {
    exit("Run this example from the command line. Listing data is untrusted: escape it before showing it in HTML.\n");
}

const SOURCE = "copart";
const SORT = "first_seen"; // on 2 November 2026 this order put the most Copart lots first; it is no contract

function apiauto_get(string $path, array $params = []): array
{
    $key = getenv("APIAUTO_KEY");
    if (!$key) {
        throw new RuntimeException("Set the APIAUTO_KEY environment variable");
    }
    $url = "https://api.apiauto.space/v1" . $path . ($params ? "?" . http_build_query($params) : "");
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_HTTPHEADER => ["X-API-Key: " . $key],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
    ]);
    $body = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    if ($status !== 200) {
        // Errors are JSON too: {"error": "quota_exhausted", "reset_at": "..."}
        throw new RuntimeException("HTTP $status: $body");
    }
    return json_decode($body, true);
}

$page = apiauto_get("/cars", [
    "market" => "us",     // us = Copart and IAAI
    "brand" => "Toyota",
    "model" => "Camry",
    "year_min" => 2020,
    "sort" => SORT,
    "limit" => 20,        // up to 20 on the demo key, up to 100 on paid plans
]);

foreach ($page["items"] as $car) {
    if ($car["source"] !== SOURCE) {
        continue;
    }
    printf(
        "%-18s %-24s VIN %-18s damage: %-8s title: %-10s bid: %-7s sale: %s\n",
        $car["id"],
        $car["title"],
        $car["vin"] ?? "-",
        $car["raw"]["damage_main"] ?? "-",
        $car["raw"]["title_doc"] ?? "-",
        $car["raw"]["bid"] ?? "-",
        substr($car["raw"]["sale_date"] ?? "-", 0, 16)
    );
}
