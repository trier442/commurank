#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://commurank.kr"
KEY = "d41c9f6a7b2e4d13a8c57f0b9e6a31cd"
ENDPOINT = "https://searchadvisor.naver.com/indexnow"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def latest_archive_urls() -> list[str]:
    index = read_json(DATA / "archive-index.json", {"periods": {}})
    briefing_index = read_json(DATA / "briefing-index.json", {"items": []})
    urls = [
        f"{BASE}/",
        f"{BASE}/issues/",
        f"{BASE}/briefing/",
        f"{BASE}/briefing/archive/",
        f"{BASE}/ranking/",
        f"{BASE}/ranking/daily/",
        f"{BASE}/ranking/weekly/",
        f"{BASE}/ranking/monthly/",
        f"{BASE}/status/",
    ]

    for slug in ["dcinside", "fmkorea", "theqoo", "ruliweb", "clien", "inven", "ppomppu"]:
        urls.append(f"{BASE}/community/{slug}/")

    briefing_items = briefing_index.get("items", [])
    if briefing_items:
        key = briefing_items[0].get("key")
        if key:
            urls.append(f"{BASE}/briefing/{key}/")

    for period in ["daily", "weekly", "monthly"]:
        items = index.get("periods", {}).get(period, [])
        if items:
            key = items[0].get("key")
            if key:
                urls.append(f"{BASE}/ranking/{period}/{key}/")

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(urls))


def main() -> None:
    urls = latest_archive_urls()
    payload = {
        "host": "commurank.kr",
        "key": KEY,
        "keyLocation": f"{BASE}/{KEY}.txt",
        "urlList": urls,
    }

    try:
        response = requests.post(
            ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=20,
        )
        print(f"IndexNow status: {response.status_code}")
        if response.text:
            print(response.text[:1000])
        # Do not break the collector if Naver is temporarily unavailable.
        if response.status_code not in (200, 202):
            print("IndexNow notification was not accepted this time; the next scheduled run will retry.")
    except Exception as exc:
        print(f"IndexNow notification failed: {exc}")


if __name__ == "__main__":
    main()
