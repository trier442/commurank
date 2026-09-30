#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
KST = ZoneInfo("Asia/Seoul")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def first_key(items):
    if not items:
        return ""
    return str(items[0].get("key") or "")


def main():
    sitemap_path = ROOT / "sitemap.xml"
    sitemap = sitemap_path.read_text(encoding="utf-8") if sitemap_path.exists() else ""
    urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
    lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", sitemap)

    latest = read_json(DATA / "latest.json", {})
    archive = read_json(DATA / "archive-index.json", {"periods": {}})
    briefing = read_json(DATA / "briefing-index.json", {"items": []})

    periods = archive.get("periods", {})
    community_urls = [u for u in urls if "/community/" in u]
    briefing_urls = [u for u in urls if "/briefing/20" in u]
    ranking_urls = [u for u in urls if "/ranking/" in u and re.search(r"/(daily|weekly|monthly)/[^/]+/$", u)]
    report_urls = [u for u in urls if "/reports/" in u and re.search(r"/(weekly|monthly)/[^/]+/$", u)]

    status = {
        "generated_at": datetime.now(KST).isoformat(),
        "today_kst": datetime.now(KST).strftime("%Y-%m-%d"),
        "latest_collected_at": latest.get("collected_at"),
        "sitemap": {
            "url_count": len(urls),
            "unique_url_count": len(set(urls)),
            "duplicate_count": len(urls) - len(set(urls)),
            "latest_lastmod": max(lastmods) if lastmods else "",
            "community_pages": len(community_urls),
            "briefing_articles": len(briefing_urls),
            "ranking_archives": len(ranking_urls),
            "trend_reports": len(report_urls),
        },
        "latest_pages": {
            "daily": first_key(periods.get("daily", [])),
            "weekly": first_key(periods.get("weekly", [])),
            "monthly": first_key(periods.get("monthly", [])),
            "briefing": first_key(briefing.get("items", [])),
        },
        "verification": {
            "google_meta": "google-site-verification" in (ROOT / "index.html").read_text(encoding="utf-8"),
            "naver_meta": "naver-site-verification" in (ROOT / "index.html").read_text(encoding="utf-8"),
            "robots_sitemap": "Sitemap: https://commurank.kr/sitemap.xml" in (ROOT / "robots.txt").read_text(encoding="utf-8"),
        },
        "note": "This file checks technical indexing readiness only. Search Console impressions, clicks, CTR and indexed status are external Google data.",
    }

    (DATA / "seo-status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"SEO status updated: {len(urls)} sitemap URLs, {status['sitemap']['duplicate_count']} duplicates")


if __name__ == "__main__":
    main()
