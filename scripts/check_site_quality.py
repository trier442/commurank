#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
# Quality gate version: 1

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

ads = json.loads(text("ads-config.json") or "{}")
if ads.get("enabled"):
    client = str(ads.get("client_id") or "")
    if not re.fullmatch(r"ca-pub-\d+", client):
        errors.append("ads-config.json: enabled but client_id is not a valid ca-pub- ID")
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
