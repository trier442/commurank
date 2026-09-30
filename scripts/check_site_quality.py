#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
# Quality gate version: 8

errors: list[str] = []
warnings: list[str] = []


def text(path: str) -> str:
    p = ROOT / path
    if not p.exists():
        errors.append(f"Missing required file: {path}")
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def require(path: str, *needles: str) -> None:
    body = text(path)
    for needle in needles:
        if needle not in body:
            errors.append(f"{path}: missing {needle!r}")


def check_indexable(path: str, min_chars: int = 900) -> None:
    body = text(path)
    if not body:
        return
    if 'name="robots" content="index,follow"' not in body:
        errors.append(f"{path}: expected index,follow")
    if '<link rel="canonical"' not in body:
        errors.append(f"{path}: canonical missing")
    if '<meta name="description"' not in body:
        errors.append(f"{path}: meta description missing")
    visible = re.sub(r"<[^>]+>", " ", body)
    visible = re.sub(r"\s+", " ", visible).strip()
    if len(visible) < min_chars:
        warnings.append(f"{path}: content is relatively thin ({len(visible)} chars)")


def check_noindex(path: str) -> None:
    body = text(path)
    if body and 'content="noindex' not in body:
        errors.append(f"{path}: utility page should be noindex")


for page in [
    "index.html",
    "about/index.html",
    "methodology/index.html",
    "editorial/index.html",
    "policy/index.html",
    "privacy/index.html",
    "site-map/index.html",
    "briefing/index.html",
    "briefing/archive/index.html",
    "ranking/index.html",
    "reports/weekly/index.html",
    "reports/monthly/index.html",
]:
    check_indexable(page)

for page in [
    "search/index.html",
    "post/index.html",
    "issue/index.html",
    "my/index.html",
    "admin/index.html",
]:
    check_noindex(page)

require("policy/index.html", "저작권", "원문")
require("privacy/index.html", "개인정보", "방문자 분석")
require("editorial/index.html", "자동화", "사실 판정", "원문")

unfinished_markers = ["Lorem ipsum", "TODO:", "FIXME:", "별도 온라인 접수 폼은 준비 중"]
for page in ["about/index.html", "policy/index.html", "privacy/index.html", "editorial/index.html"]:
    body = text(page)
    for marker in unfinished_markers:
        if marker in body:
            errors.append(f"{page}: unfinished marker found: {marker}")

brief_index = json.loads(text("data/briefing-index.json") or '{"items":[]}')
if brief_index.get("items"):
    key = brief_index["items"][0].get("key")
    if key and not (ROOT / "briefing" / key / "index.html").exists():
        errors.append(f"Latest briefing page missing: /briefing/{key}/")

archive_index = json.loads(text("data/archive-index.json") or '{"periods":{}}')
for period in ("weekly", "monthly"):
    items = archive_index.get("periods", {}).get(period, [])
    if not items:
        continue
    key = items[0].get("key")
    report = ROOT / "reports" / period / str(key) / "index.html"
    if key and not report.exists():
        errors.append(f"Latest {period} report missing: {report.relative_to(ROOT)}")

sitemap = text("sitemap.xml")
for path in [
    "/about/", "/methodology/", "/editorial/", "/policy/", "/privacy/",
    "/site-map/", "/briefing/archive/", "/reports/weekly/", "/reports/monthly/",
]:
    loc = f"https://commurank.kr{path}"
    if loc not in sitemap:
        errors.append(f"sitemap.xml: missing {loc}")

robots = text("robots.txt")
for path in ["/admin/", "/my/", "/search/", "/post/", "/issue/"]:
    if f"Disallow: {path}" not in robots:
        warnings.append(f"robots.txt: utility path not disallowed: {path}")

analytics_public_pages = [
    "index.html",
    "briefing/index.html",
    "issues/index.html",
    "search/index.html",
    "post/index.html",
    "issue/index.html",
    "my/index.html",
    "status/index.html",
    "community/dcinside/index.html",
    "community/fmkorea/index.html",
    "community/theqoo/index.html",
    "community/ruliweb/index.html",
    "community/clien/index.html",
    "community/inven/index.html",
    "community/ppomppu/index.html",
]
for page in analytics_public_pages:
    body = text(page)
    if "analytics.js" not in body:
        errors.append(f"{page}: analytics.js loader missing")

# SEO internal-link checks
home = text("index.html")
for needle in [
    "커뮤니티 인기글 순위·오늘 인터넷 이슈",
    "/ranking/daily/",
    "/reports/weekly/",
    "/reports/monthly/",
    "/briefing/archive/",
]:
    if needle not in home:
        errors.append(f"index.html: SEO element missing: {needle}")

for page in ["ranking/index.html", "briefing/archive/index.html", "reports/weekly/index.html", "reports/monthly/index.html"]:
    body = text(page)
    if len(re.sub(r"<[^>]+>", " ", body)) < 700:
        warnings.append(f"{page}: archive/report landing page may be too thin")

# Community long-tail SEO checks
community_expectations = {
    "community/dcinside/index.html": "디시인사이드 인기글 순위·급상승",
    "community/fmkorea/index.html": "에펨코리아 인기글 순위·급상승",
    "community/theqoo/index.html": "더쿠 인기글 순위·급상승",
    "community/ruliweb/index.html": "루리웹 인기글 순위·급상승",
    "community/clien/index.html": "클리앙 인기글 순위·급상승",
    "community/inven/index.html": "인벤 인기글 순위·급상승",
    "community/ppomppu/index.html": "뽐뿌 인기글 순위·급상승",
}
for page, phrase in community_expectations.items():
    body = text(page)
    if phrase not in body:
        errors.append(f"{page}: long-tail SEO title missing")
    if '"@type":"BreadcrumbList"' not in body:
        errors.append(f"{page}: BreadcrumbList structured data missing")
    if "커뮤니티 인기글 순위를 보는 방법" not in body:
        warnings.append(f"{page}: explanatory SEO content missing")

# Latest date-page SEO checks
daily_items = archive_index.get("periods", {}).get("daily", [])
if daily_items:
    daily_key = str(daily_items[0].get("key") or "")
    daily_page = f"ranking/daily/{daily_key}/index.html"
    daily_body = text(daily_page)
    try:
        daily_dt = __import__("datetime").datetime.strptime(daily_key, "%Y-%m-%d")
        natural_label = f"{daily_dt.year}년 {daily_dt.month}월 {daily_dt.day}일"
    except Exception:
        natural_label = daily_key
    for needle in [
        natural_label,
        f"/briefing/{daily_key}/",
        '"@type":"BreadcrumbList"',
        "커뮤니티 인기글 순위 TOP100",
    ]:
        if needle not in daily_body:
            errors.append(f"{daily_page}: date SEO element missing: {needle}")

if brief_index.get("items"):
    brief_key = str(brief_index["items"][0].get("key") or "")
    brief_page = f"briefing/{brief_key}/index.html"
    brief_body = text(brief_page)
    try:
        brief_dt = __import__("datetime").datetime.strptime(brief_key, "%Y-%m-%d")
        brief_label = f"{brief_dt.year}년 {brief_dt.month}월 {brief_dt.day}일"
    except Exception:
        brief_label = brief_key
    for needle in [
        brief_label,
        f"/ranking/daily/{brief_key}/",
        '"@type":"BreadcrumbList"',
        "인터넷 이슈·커뮤니티 인기글",
    ]:
        if needle not in brief_body:
            errors.append(f"{brief_page}: date SEO element missing: {needle}")

# SEO status snapshot checks
seo_status = json.loads(text("data/seo-status.json") or "{}")
sitemap_status = seo_status.get("sitemap", {})
if sitemap_status.get("url_count", 0) <= 0:
    errors.append("data/seo-status.json: sitemap URL count is zero")
if sitemap_status.get("duplicate_count", 0) != 0:
    errors.append("data/seo-status.json: duplicate sitemap URLs detected")
if not seo_status.get("verification", {}).get("google_meta"):
    errors.append("data/seo-status.json: Google verification meta missing")
if not seo_status.get("verification", {}).get("naver_meta"):
    errors.append("data/seo-status.json: Naver verification meta missing")
if not seo_status.get("verification", {}).get("robots_sitemap"):
    errors.append("data/seo-status.json: robots.txt sitemap declaration missing")

ads_script = text("ads.js")
if "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js" not in ads_script:
    errors.append("ads.js: Google AdSense loader URL missing")

ads = json.loads(text("ads-config.json") or "{}")
if ads.get("enabled"):
    client = str(ads.get("client_id") or "")
    if not re.fullmatch(r"ca-pub-\d+", client):
        errors.append("ads-config.json: enabled but client_id is not a valid ca-pub- ID")
    ads_txt = text("ads.txt")
    publisher = client.replace("ca-", "", 1)
    if publisher and publisher not in ads_txt:
        errors.append("ads.txt: enabled AdSense publisher ID missing")
else:
    print("AdSense config: disabled (expected before approval)")

analytics = json.loads(text("analytics-config.json") or "{}")
if analytics.get("enabled"):
    ga4 = str(analytics.get("ga4_id") or "")
    if not re.fullmatch(r"G-[A-Z0-9]+", ga4, re.I):
        errors.append("analytics-config.json: enabled but GA4 ID is invalid")

print(f"Quality check: {len(errors)} error(s), {len(warnings)} warning(s)")
for item in warnings:
    print(f"WARNING: {item}")
for item in errors:
    print(f"ERROR: {item}")

if errors:
    raise SystemExit(1)
