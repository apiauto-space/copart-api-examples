"""Download the photos of one Copart lot.

Photo links in a record are signed and live about a day, so keep the lot id and ask for
a fresh record when you need the photos again. Photo requests do not spend quota.

    pip install httpx
    export APIAUTO_KEY=...
    python download_photos.py copart:70370576 --max 3
"""

import argparse
import os
import re
from pathlib import Path

import httpx

# The API's /img, and the Copart photo host it may redirect to. A link goes nowhere else.
PHOTO_HOSTS = ("api.apiauto.space", ".copart.com")
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/avif": "avif"}
MAX_PHOTO_BYTES = 15 * 1024 * 1024
MAX_REDIRECTS = 3

parser = argparse.ArgumentParser()
parser.add_argument("car_id", help="like copart:70370576")
parser.add_argument("--max", type=int, help="stop after this many photos")
args = parser.parse_args()
if not re.fullmatch(r"copart:[0-9A-Za-z]+", args.car_id):  # it becomes a folder name below
    parser.error("car_id must look like copart:70370576")


def check_link(url: httpx.URL) -> None:
    """Links come from the API and from redirects: refuse anything but https to a known host."""
    known = any(url.host == host or (host[0] == "." and url.host.endswith(host)) for host in PHOTO_HOSTS)
    if url.scheme != "https" or not known or url.userinfo or url.port not in (None, 443):
        raise SystemExit(f"refused a photo link to {url.host or 'an unknown host'}")


def save_photo(http: httpx.Client, link: str, stem: Path) -> Path:
    """Follow redirects by hand, checking each one, and read the photo with a size limit."""
    url = httpx.URL(link)
    for _ in range(MAX_REDIRECTS + 1):
        check_link(url)
        with http.stream("GET", url) as response:
            if response.is_redirect:
                url = url.join(response.headers["Location"])
                continue
            response.raise_for_status()
            extension = IMAGE_TYPES.get(response.headers.get("Content-Type", "").split(";")[0].strip().lower())
            if extension is None:
                raise SystemExit("the answer is not a photo")
            path = stem.with_suffix("." + extension)
            size = 0
            with path.open("wb") as file:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_PHOTO_BYTES:
                        file.close()
                        path.unlink()
                        raise SystemExit("the photo is larger than 15 MiB")
                    file.write(chunk)
            return path
    raise SystemExit("too many redirects")


api = httpx.Client(
    base_url="https://api.apiauto.space/v1",
    headers={"X-API-Key": os.environ["APIAUTO_KEY"]},
    timeout=30,
)
car = api.get(f"/cars/{args.car_id}").raise_for_status().json()

folder = Path(args.car_id.replace(":", "-"))
folder.mkdir(exist_ok=True)
# A separate client without the key: the link is signed.
with httpx.Client(timeout=60) as http:
    photos = car["photos"][: args.max]
    for number, link in enumerate(photos, start=1):
        path = save_photo(http, link, folder / f"{number:02}")
        print(f"{path.as_posix()}  {path.stat().st_size // 1024} KB")

print(f"{car['title']}: {len(photos)} of {car['photo_count']} photos")
