#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RANKING = ROOT / "ranking"
ARCHIVE_INDEX = DATA / "archive-index.json"
LATEST_PATH = DATA / "latest.json"
BASE = "https://commurank.kr"

PERIODS = {
    "daily": ("일간", "오늘과 과거 날짜별 커뮤니티 인기글 TOP100"),
    "weekly": ("주간", "주간 단위 커뮤니티 인기글 TOP100"),
    "monthly": ("월간", "월간 단위 커뮤니티 인기글 TOP100"),
}

COMMUNITIES = ["dcinside", "fmkorea", "theqoo", "ruliweb", "clien", "inven", "ppomppu"]


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def json_script(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def fmt_number(value) -> str:
    try:
        return f"{int(value or 0):,}"
    except Exception:
        return "0"


def page_shell(title: str, description: str, canonical: str, body: str, structured=None) -> str:
    ld = ""
    if structured:
        ld = f'<script type="application/ld+json">{json_script(structured)}</script>'
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="theme-color" content="#5b45ff" />
  <meta name="robots" content="index,follow" />
  <meta name="description" content="{esc(description)}" />
  <meta property="og:site_name" content="커뮤랭크" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(description)}" />
  <meta property="og:url" content="{esc(canonical)}" />
  <meta property="og:locale" content="ko_KR" />
  <link rel="canonical" href="{esc(canonical)}" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="manifest" href="/manifest.webmanifest" />
  <link rel="alternate" type="application/rss+xml" title="커뮤랭크 실시간 인기글 RSS" href="/feed.xml" />
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="/styles.css" />
  {ld}
</head>
<body>
  <header class="site-header">
    <div class="shell search-header">
      <a class="brand" href="/" aria-label="커뮤랭크 홈">
        <span class="brand-mark">C</span>
        <span><strong>커뮤랭크</strong><small>COMMURANK</small></span>
      </a>
      <form class="global-search global-search-wide" action="/search/" method="get" role="search">
        <input type="search" name="q" autocomplete="off" placeholder="게시글·키워드·커뮤니티 검색" />
        <button type="submit">검색</button>
      </form>
      <button id="themeToggle" class="icon-button" aria-label="테마 전환">◐</button>
    </div>
  </header>
  <main>{body}</main>
  <footer>
    <div class="shell footer-inner">
      <div><strong>커뮤랭크</strong><p>대한민국 커뮤니티 인기글 랭킹 아카이브</p></div>
      <p>원문은 각 커뮤니티에서 확인합니다.</p>
    </div>
  </footer>
  <script src="/analytics.js"></script>
  <script>
    document.querySelector("#themeToggle").addEventListener("click",()=>{{document.body.classList.toggle("dark");localStorage.setItem("commurank-theme",document.body.classList.contains("dark")?"dark":"light")}});
    if(localStorage.getItem("commurank-theme")==="dark") document.body.classList.add("dark");
  </script>
</body>
</html>"""


def ranking_rows(posts: list[dict]) -> str:
    rows = []
    for i, p in enumerate(posts[:100], start=1):
        title = esc(p.get("title"))
        source = esc(p.get("source"))
        category = esc(p.get("category") or "이슈")
        original = esc(p.get("url"))
        detail = "/post/?url=" + quote(str(p.get("url") or ""), safe="")
        rows.append(
            f"""<article class="rank-item">
  <div class="rank-num {'top' if i <= 3 else ''}">{i}</div>
  <div>
    <a class="post-title" href="{detail}">{title}</a>
    <div class="meta">
      <span class="source">{source}</span>
      <span class="category">{category}</span>
      <span>조회 {fmt_number(p.get('views'))}</span>
      <span>추천 {fmt_number(p.get('likes'))}</span>
      <span>댓글 {fmt_number(p.get('comments'))}</span>
      <a class="outbound-link" href="{original}" target="_blank" rel="noopener noreferrer">원문 ↗</a>
    </div>
  </div>
</article>"""
        )
    return "\n".join(rows) if rows else '<div class="empty">랭킹 데이터가 없습니다.</div>'


def archive_page(period: str, item: dict, snap: dict) -> str:
    label = item.get("label") or item.get("key")
    period_label, _ = PERIODS[period]
    posts = snap.get("posts", []) if isinstance(snap, dict) else []
    canonical = f"{BASE}/ranking/{period}/{item['key']}/"
    title = f"{label} 커뮤니티 인기글 TOP100 | 커뮤랭크"
    description = f"{label} {period_label} 커뮤니티 통합 인기글 TOP100. 여러 커뮤니티의 공개 인기글 반응을 정규화해 정리한 커뮤랭크 아카이브입니다."

    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{label} 커뮤니티 인기글 TOP100",
        "numberOfItems": min(100, len(posts)),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": p.get("title", ""),
                "url": p.get("url", ""),
            }
            for i, p in enumerate(posts[:100], start=1)
        ],
    }

    body = f"""
    <section class="shell info-hero ranking-archive-hero">
      <p class="eyebrow">COMMURANK {period.upper()} ARCHIVE</p>
      <h1>{esc(label)}<br><span>커뮤니티 인기글 TOP100</span></h1>
      <p>{esc(description)}</p>
      <div class="archive-page-nav">
        <a href="/ranking/{period}/">← {period_label} 아카이브</a>
        <a href="/?period={period}">현재 {period_label} 랭킹 →</a>
      </div>
    </section>
    <section class="shell ranking-seo-layout">
      <div class="ranking-panel">
        <div class="section-head">
          <div><span class="section-kicker">{esc(period_label)}</span><h2>통합 인기글 TOP100</h2></div>
          <div class="updated">수집 기준 <strong>{esc(item.get('collected_at', ''))}</strong></div>
        </div>
        <div class="ranking-list">{ranking_rows(posts)}</div>
      </div>
    </section>
    """
    return page_shell(title, description, canonical, body, item_list)


def period_index(period: str, items: list[dict]) -> str:
    period_label, description = PERIODS[period]
    canonical = f"{BASE}/ranking/{period}/"
    cards = []
    for item in items:
        cards.append(
            f'<a class="archive-index-row" href="/ranking/{period}/{esc(item.get("key"))}/">'
            f'<strong>{esc(item.get("label") or item.get("key"))}</strong>'
            f'<span>TOP100 보기 →</span></a>'
        )
    body = f"""
    <section class="shell info-hero">
      <p class="eyebrow">COMMURANK ARCHIVE</p>
      <h1>{period_label} 인기글 아카이브</h1>
      <p>{description}. 날짜별 순위를 남겨 과거에 어떤 글이 화제가 되었는지 다시 확인할 수 있습니다.</p>
    </section>
    <section class="shell info-layout">
      <div class="info-main">
        <section class="info-card">
          <h2>{period_label} 순위 목록</h2>
          <div class="archive-index-list">{''.join(cards) if cards else '<div class="empty">아카이브를 쌓는 중입니다.</div>'}</div>
        </section>
      </div>
      <aside class="info-side">
        <nav class="info-nav">
          <a href="/ranking/daily/"{' class="active"' if period == 'daily' else ''}>일간</a>
          <a href="/ranking/weekly/"{' class="active"' if period == 'weekly' else ''}>주간</a>
          <a href="/ranking/monthly/"{' class="active"' if period == 'monthly' else ''}>월간</a>
          <a href="/">현재 랭킹</a>
        </nav>
      </aside>
    </section>
    """
    return page_shell(f"{period_label} 인기글 아카이브 | 커뮤랭크", description, canonical, body)


def root_index(index: dict) -> str:
    counts = {period: len(index.get("periods", {}).get(period, [])) for period in PERIODS}
    body = f"""
    <section class="shell info-hero">
      <p class="eyebrow">COMMURANK RANKING ARCHIVE</p>
      <h1>커뮤니티 인기글<br>랭킹 아카이브</h1>
      <p>실시간 흐름뿐 아니라 날짜가 지난 뒤에도 일간·주간·월간 인기글 순위를 확인할 수 있습니다.</p>
    </section>
    <section class="shell info-layout">
      <div class="info-main">
        <section class="info-card">
          <h2>기간별 아카이브</h2>
          <div class="archive-period-grid">
            <a href="/ranking/daily/"><strong>일간</strong><span>{counts['daily']}개 날짜</span></a>
            <a href="/ranking/weekly/"><strong>주간</strong><span>{counts['weekly']}개 주</span></a>
            <a href="/ranking/monthly/"><strong>월간</strong><span>{counts['monthly']}개 월</span></a>
          </div>
        </section>
      </div>
      <aside class="info-side"><nav class="info-nav"><a href="/">현재 랭킹</a><a href="/issues/">이슈 TOP20</a><a href="/briefing/">오늘의 브리핑</a></nav></aside>
    </section>
    """
    structured = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "커뮤랭크 인기글 랭킹 아카이브",
        "url": f"{BASE}/ranking/",
    }
    return page_shell("커뮤니티 인기글 랭킹 아카이브 | 커뮤랭크", "일간·주간·월간 커뮤니티 인기글 TOP100 과거 순위 아카이브", f"{BASE}/ranking/", body, structured)



def write_feed(latest: dict) -> None:
    posts = latest.get("rankings", {}).get("realtime", [])[:30] if isinstance(latest, dict) else []
    collected_at = str(latest.get("collected_at", "")) if isinstance(latest, dict) else ""
    try:
        stamp = datetime.fromisoformat(collected_at)
        pub_date = stamp.strftime("%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        pub_date = datetime.now().astimezone().strftime("%a, %d %b %Y %H:%M:%S %z")

    rows = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '<channel>',
        '<title>커뮤랭크 실시간 인기글</title>',
        f'<link>{BASE}/</link>',
        '<description>여러 커뮤니티의 실시간 인기글 TOP30</description>',
        '<language>ko</language>',
        f'<lastBuildDate>{esc(pub_date)}</lastBuildDate>',
    ]

    for p in posts:
        original = str(p.get("url") or "")
        detail = f"{BASE}/post/?url=" + quote(original, safe="")
        summary = (
            f"{p.get('source','')} · 조회 {fmt_number(p.get('views'))} · "
            f"추천 {fmt_number(p.get('likes'))} · 댓글 {fmt_number(p.get('comments'))}"
        )
        rows.extend([
            '<item>',
            f'<title>{esc(p.get("title"))}</title>',
            f'<link>{esc(detail)}</link>',
            f'<guid isPermaLink="false">{esc(original)}</guid>',
            f'<description>{esc(summary)}</description>',
            f'<pubDate>{esc(pub_date)}</pubDate>',
            '</item>',
        ])

    rows.extend(['</channel>', '</rss>'])
    (ROOT / "feed.xml").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_sitemap(index: dict) -> None:
    static = [
        ("/", "hourly", "1.0"),
        ("/issues/", "hourly", "0.9"),
        ("/briefing/", "hourly", "0.9"),
        ("/ranking/", "daily", "0.9"),
        ("/ranking/daily/", "daily", "0.9"),
        ("/ranking/weekly/", "daily", "0.8"),
        ("/ranking/monthly/", "weekly", "0.8"),
        ("/about/", "monthly", "0.6"),
        ("/methodology/", "monthly", "0.7"),
        ("/privacy/", "monthly", "0.4"),
        ("/policy/", "monthly", "0.5"),
        ("/status/", "hourly", "0.5"),
    ]
    for slug in COMMUNITIES:
        static.append((f"/community/{slug}/", "hourly", "0.8"))

    rows = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = datetime.now().strftime("%Y-%m-%d")
    for path, freq, priority in static:
        rows.append(f"  <url><loc>{BASE}{path}</loc><lastmod>{today}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>")

    for period in PERIODS:
        period_items = index.get("periods", {}).get(period, [])
        for idx, item in enumerate(period_items):
            collected = str(item.get("collected_at", today))[:10]
            current = idx == 0
            freq = "hourly" if current and period == "daily" else ("daily" if current else "never")
            rows.append(
                f"  <url><loc>{BASE}/ranking/{period}/{esc(item.get('key'))}/</loc>"
                f"<lastmod>{collected}</lastmod><changefreq>{freq}</changefreq><priority>0.7</priority></url>"
            )
    rows.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    index = read_json(ARCHIVE_INDEX, {"periods": {}})
    latest = read_json(LATEST_PATH, {})
    RANKING.mkdir(parents=True, exist_ok=True)
    (RANKING / "index.html").write_text(root_index(index), encoding="utf-8")

    for period in PERIODS:
        period_dir = RANKING / period
        period_dir.mkdir(parents=True, exist_ok=True)
        items = index.get("periods", {}).get(period, [])
        (period_dir / "index.html").write_text(period_index(period, items), encoding="utf-8")

        for item in items:
            snap_path = DATA / str(item.get("path", ""))
            snap = read_json(snap_path, {})
            out_dir = period_dir / str(item.get("key"))
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "index.html").write_text(archive_page(period, item, snap), encoding="utf-8")

    write_sitemap(index)
    write_feed(latest)
    print("SEO ranking pages, sitemap, and RSS feed updated.")


if __name__ == "__main__":
    main()
