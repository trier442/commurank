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
SEARCH_INDEX_PATH = DATA / "search-index.json"
BRIEFING_INDEX_PATH = DATA / "briefing-index.json"
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
    <a class="post-title" href="{original}" target="_blank" rel="noopener noreferrer">{title}</a>
    <div class="meta">
      <span class="source">{source}</span>
      <span class="category">{category}</span>
      <span>조회 {fmt_number(p.get('views'))}</span>
      <span>추천 {fmt_number(p.get('likes'))}</span>
      <span>댓글 {fmt_number(p.get('comments'))}</span>
      <a class="analysis-link" href="{detail}">분석 보기</a>
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
        <section class="info-card">
          <h2>아카이브를 이렇게 활용하세요</h2>
          <p>일간 아카이브는 특정 날짜에 어떤 글이 상위권에 있었는지 확인하는 용도이고, 주간·월간 아카이브는 여러 날 반복적으로 노출된 글과 장기 반응을 함께 반영합니다. 현재 랭킹과 과거 랭킹을 분리해 과거 누적 반응이 오늘 순위에 그대로 섞이지 않도록 합니다.</p>
          <p>각 목록은 게시글 제목, 출처, 조회·추천·댓글 등 공개 지표를 보여 주며 제목을 누르면 원문으로 바로 이동합니다. 순위는 커뮤랭크의 상대 점수이므로 인터넷 전체 여론이나 이용자 전체의 선호를 의미하지 않습니다.</p>
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





def briefing_article_page(item: dict, briefing: dict) -> str:
    key = str(item.get("key") or briefing.get("date") or "")
    label = str(briefing.get("label") or item.get("label") or key)
    canonical = f"{BASE}/briefing/{key}/"
    stats = briefing.get("stats", {}) if isinstance(briefing, dict) else {}
    issues = briefing.get("issues", []) if isinstance(briefing, dict) else []
    rising = briefing.get("rising", []) if isinstance(briefing, dict) else []
    keywords = briefing.get("keywords", []) if isinstance(briefing, dict) else []
    leaders = briefing.get("community_leaders", []) if isinstance(briefing, dict) else []
    top_posts = briefing.get("top_posts", []) if isinstance(briefing, dict) else []

    description = (
        f"{label} 커뮤니티 인터넷 이슈 브리핑. "
        f"{int(stats.get('sources', 0) or 0)}개 커뮤니티의 인기글, 급상승 글, 핵심 이슈와 키워드를 데이터로 정리합니다."
    )

    paragraphs = [
        f"{label} 커뮤랭크는 {int(stats.get('sources', 0) or 0)}개 커뮤니티에서 "
        f"실시간 인기글 {int(stats.get('realtime_posts', 0) or 0)}건과 일간 인기글 "
        f"{int(stats.get('daily_posts', 0) or 0)}건을 집계했습니다. "
        f"상위 인기글의 누적 조회는 {fmt_number(stats.get('top100_views'))}회, "
        f"댓글은 {fmt_number(stats.get('top100_comments'))}개로 집계됐습니다."
    ]

    if issues:
        top = issues[0]
        paragraphs.append(
            f"여러 커뮤니티에서 동시에 포착된 이슈 가운데 상위에는 ‘{top.get('title','')}’가 올랐습니다. "
            f"{int(top.get('source_count', 0) or 0)}개 커뮤니티에서 "
            f"{int(top.get('post_count', 0) or 0)}개의 관련 인기글이 잡혔습니다."
        )
    if keywords:
        lead_keywords = ", ".join(f"#{row.get('keyword','')}" for row in keywords[:5] if row.get("keyword"))
        if lead_keywords:
            paragraphs.append(
                f"실시간 키워드에서는 {lead_keywords} 등이 상위권에 나타났습니다. "
                "키워드 순위는 여러 커뮤니티의 인기글 제목에서 반복적으로 등장한 표현을 기준으로 계산합니다."
            )
    if rising:
        top = rising[0]
        paragraphs.append(
            f"급상승 영역에서는 ‘{top.get('title','')}’의 반응 증가가 크게 포착됐습니다. "
            f"직전 수집과 비교해 조회 {fmt_number(top.get('delta_views'))}회, "
            f"댓글 {fmt_number(top.get('delta_comments'))}개가 늘었습니다."
        )
    paragraphs.append(
        "이 브리핑은 공개 인기글 목록의 제목과 반응 지표를 바탕으로 자동 정리한 데이터 요약입니다. "
        "특정 커뮤니티나 게시글의 주장에 대한 사실 판정이나 찬반 평가를 뜻하지 않습니다."
    )

    issue_cards = "".join(
        f"""<article class="daily-brief-topic">
          <span>{i}</span>
          <div>
            <a href="/issue/?id={quote(str(row.get('id') or ''), safe='')}">{esc(row.get('title'))}</a>
            <p>{int(row.get('source_count',0) or 0)}개 커뮤니티 · 관련글 {int(row.get('post_count',0) or 0)}건</p>
            <div>{' '.join('#'+esc(k) for k in (row.get('keywords') or [])[:4])}</div>
          </div>
        </article>"""
        for i, row in enumerate(issues[:8], start=1)
    ) or '<div class="empty">동시 화제 이슈 데이터가 없습니다.</div>'

    rising_rows = "".join(
        f"""<article class="brief-list-row">
          <span class="brief-rank hot">{i}</span>
          <div>
            <a href="{esc(row.get('url'))}" target="_blank" rel="noopener noreferrer">{esc(row.get('title'))}</a>
            <small>{esc(row.get('source'))} · +조회 {fmt_number(row.get('delta_views'))} · +댓글 {fmt_number(row.get('delta_comments'))}</small>
          </div>
        </article>"""
        for i, row in enumerate(rising[:10], start=1)
    ) or '<div class="empty">급상승 데이터가 없습니다.</div>'

    leader_rows = "".join(
        f"""<article class="brief-list-row">
          <span class="brief-rank">{i}</span>
          <div>
            <a href="{esc(row.get('url'))}" target="_blank" rel="noopener noreferrer">{esc(row.get('source'))} · {esc(row.get('title'))}</a>
            <small>조회 {fmt_number(row.get('views'))} · 댓글 {fmt_number(row.get('comments'))}</small>
          </div>
        </article>"""
        for i, row in enumerate(leaders[:10], start=1)
    ) or '<div class="empty">커뮤니티별 데이터가 없습니다.</div>'

    top_rows = "".join(
        f"""<article class="brief-list-row">
          <span class="brief-rank">{i}</span>
          <div>
            <a href="{esc(row.get('url'))}" target="_blank" rel="noopener noreferrer">{esc(row.get('title'))}</a>
            <small>{esc(row.get('source'))} · 조회 {fmt_number(row.get('views'))} · 댓글 {fmt_number(row.get('comments'))}</small>
          </div>
        </article>"""
        for i, row in enumerate(top_posts[:10], start=1)
    ) or '<div class="empty">인기글 데이터가 없습니다.</div>'

    keyword_html = "".join(
        f'<a href="/search/?q={quote(str(row.get("keyword") or ""), safe="")}">#{esc(row.get("keyword"))}<span>{int(row.get("post_count",0) or 0)}글</span></a>'
        for row in keywords[:16]
        if row.get("keyword")
    )

    article_body = "".join(f"<p>{esc(p)}</p>" for p in paragraphs)
    body = f"""
    <article class="shell daily-brief-article">
      <header class="daily-brief-header">
        <p class="eyebrow">DAILY INTERNET BRIEFING</p>
        <h1>{esc(label)}<br><span>인터넷 이슈 브리핑</span></h1>
        <p>{esc(description)}</p>
        <div class="archive-page-nav">
          <a href="/briefing/">오늘의 브리핑</a>
          <a href="/briefing/archive/">지난 브리핑 보기 →</a>
        </div>
      </header>

      <section class="daily-brief-stats">
        <div><strong>{int(stats.get('sources',0) or 0)}</strong><span>수집 커뮤니티</span></div>
        <div><strong>{int(stats.get('daily_posts',0) or 0)}</strong><span>일간 인기글</span></div>
        <div><strong>{int(stats.get('daily_issues',0) or 0)}</strong><span>핵심 이슈</span></div>
        <div><strong>{int(stats.get('keywords',0) or 0)}</strong><span>키워드</span></div>
      </section>

      <div class="daily-brief-layout">
        <main class="daily-brief-main">
          <section class="briefing-card daily-brief-copy">
            <div class="briefing-card-head"><div><span>SUMMARY</span><h2>오늘의 흐름</h2></div></div>
            {article_body}
          </section>
          <section class="briefing-card">
            <div class="briefing-card-head"><div><span>ISSUES</span><h2>여러 커뮤니티에서 함께 잡힌 이슈</h2></div></div>
            <div class="daily-brief-topics">{issue_cards}</div>
          </section>
          <section class="briefing-card">
            <div class="briefing-card-head"><div><span>TOP POSTS</span><h2>오늘의 인기글 TOP10</h2></div></div>
            {top_rows}
          </section>
        </main>
        <aside class="daily-brief-side">
          <section class="briefing-card">
            <div class="briefing-card-head"><div><span>FAST RISING</span><h2>급상승</h2></div></div>
            {rising_rows}
          </section>
          <section class="briefing-card">
            <div class="briefing-card-head"><div><span>KEYWORDS</span><h2>실시간 키워드</h2></div></div>
            <div class="daily-brief-keywords">{keyword_html}</div>
          </section>
          <section class="briefing-card">
            <div class="briefing-card-head"><div><span>COMMUNITIES</span><h2>커뮤니티별 1위</h2></div></div>
            {leader_rows}
          </section>
        </aside>
      </div>
    </article>
    """

    structured = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{label} 인터넷 이슈 브리핑",
        "description": description,
        "datePublished": key,
        "dateModified": briefing.get("collected_at", key),
        "mainEntityOfPage": canonical,
        "publisher": {"@type": "Organization", "name": "커뮤랭크", "url": BASE},
    }
    return page_shell(f"{label} 인터넷 이슈 브리핑 | 커뮤랭크", description, canonical, body, structured)


def briefing_archive_page(briefing_index: dict) -> str:
    items = briefing_index.get("items", []) if isinstance(briefing_index, dict) else []
    rows = "".join(
        f'<a class="archive-index-row" href="/briefing/{esc(item.get("key"))}/"><strong>{esc(item.get("label"))} 인터넷 브리핑</strong><span>읽기 →</span></a>'
        for item in items
    )
    body = f"""
    <section class="shell info-hero">
      <p class="eyebrow">DAILY BRIEFING ARCHIVE</p>
      <h1>인터넷 이슈<br>브리핑 아카이브</h1>
      <p>날짜별로 여러 커뮤니티의 인기글, 급상승 흐름, 동시 화제와 키워드를 데이터 중심으로 정리합니다.</p>
    </section>
    <section class="shell info-layout">
      <div class="info-main">
        <section class="info-card"><h2>날짜별 브리핑</h2><div class="archive-index-list">{rows or '<div class="empty">브리핑을 쌓는 중입니다.</div>'}</div></section>
        <section class="info-card"><h2>브리핑 아카이브의 기준</h2><p>각 날짜 브리핑은 그날 수집된 인기글, 급상승 반응, 여러 커뮤니티에서 함께 포착된 이슈와 반복 키워드를 보존합니다. 날짜가 지난 뒤 최신 결과로 덮어쓰지 않기 때문에 당시의 관심 흐름을 다시 확인할 수 있습니다.</p><p>브리핑에 표시되는 ‘화제’나 ‘급상승’은 수집 데이터의 변화량을 설명하는 표현이며 게시글의 사실 여부나 찬반을 판단하는 의미가 아닙니다. 원문 내용은 각 출처 사이트에서 직접 확인할 수 있습니다.</p></section>
      </div>
      <aside class="info-side"><nav class="info-nav"><a href="/briefing/">오늘의 브리핑</a><a href="/ranking/">랭킹 아카이브</a><a href="/issues/">이슈 TOP20</a></nav></aside>
    </section>
    """
    return page_shell(
        "인터넷 이슈 브리핑 아카이브 | 커뮤랭크",
        "날짜별 커뮤니티 인기글·급상승·동시 화제·키워드 데이터 브리핑",
        f"{BASE}/briefing/archive/",
        body,
        {"@context":"https://schema.org","@type":"CollectionPage","name":"커뮤랭크 인터넷 브리핑 아카이브","url":f"{BASE}/briefing/archive/"},
    )


def write_briefing_pages(briefing_index: dict) -> None:
    briefing_root = ROOT / "briefing"
    archive_dir = briefing_root / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.html").write_text(briefing_archive_page(briefing_index), encoding="utf-8")

    for item in briefing_index.get("items", []):
        key = str(item.get("key") or "")
        if not key:
            continue
        briefing = read_json(DATA / str(item.get("path") or ""), {})
        out_dir = briefing_root / key
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(briefing_article_page(item, briefing), encoding="utf-8")


def write_search_index(archive: dict, latest: dict) -> None:
    current_urls = {
        p.get("url")
        for p in (latest.get("rankings", {}).get("realtime", []) if isinstance(latest, dict) else [])
        if p.get("url")
    }

    rows = []
    if isinstance(archive, dict):
        for item in archive.values():
            if not isinstance(item, dict) or not item.get("url"):
                continue
            rows.append({
                "t": item.get("title", ""),
                "s": item.get("source", ""),
                "c": item.get("category", "이슈"),
                "u": item.get("url", ""),
                "v": int(item.get("max_views", 0) or 0),
                "l": int(item.get("max_likes", 0) or 0),
                "m": int(item.get("max_comments", 0) or 0),
                "p": float(item.get("peak_score", 0) or 0),
                "f": item.get("first_seen", ""),
                "d": item.get("last_seen", ""),
                "a": int(item.get("appearances", 0) or 0),
                "n": 1 if item.get("url") in current_urls else 0,
            })

    rows.sort(key=lambda x: (x.get("d", ""), x.get("p", 0)), reverse=True)
    payload = {
        "version": 1,
        "generated_at": latest.get("collected_at", "") if isinstance(latest, dict) else "",
        "count": len(rows),
        "records": rows,
    }
    SEARCH_INDEX_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


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
        summary = (
            f"{p.get('source','')} · 조회 {fmt_number(p.get('views'))} · "
            f"추천 {fmt_number(p.get('likes'))} · 댓글 {fmt_number(p.get('comments'))}"
        )
        rows.extend([
            '<item>',
            f'<title>{esc(p.get("title"))}</title>',
            f'<link>{esc(original)}</link>',
            f'<guid isPermaLink="false">{esc(original)}</guid>',
            f'<description>{esc(summary)}</description>',
            f'<pubDate>{esc(pub_date)}</pubDate>',
            '</item>',
        ])

    rows.extend(['</channel>', '</rss>'])
    (ROOT / "feed.xml").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_sitemap(index: dict, briefing_index: dict) -> None:
    static = [
        ("/", "hourly", "1.0"),
        ("/issues/", "hourly", "0.9"),
        ("/briefing/", "hourly", "0.9"),
        ("/briefing/archive/", "daily", "0.8"),
        ("/ranking/", "daily", "0.9"),
        ("/ranking/daily/", "daily", "0.9"),
        ("/ranking/weekly/", "daily", "0.8"),
        ("/ranking/monthly/", "weekly", "0.8"),
        ("/about/", "monthly", "0.6"),
        ("/methodology/", "monthly", "0.7"),
        ("/privacy/", "monthly", "0.4"),
        ("/policy/", "monthly", "0.5"),
        ("/editorial/", "monthly", "0.6"),
        ("/site-map/", "weekly", "0.5"),
        ("/status/", "hourly", "0.5"),
    ]
    for slug in COMMUNITIES:
        static.append((f"/community/{slug}/", "hourly", "0.8"))

    rows = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = datetime.now().strftime("%Y-%m-%d")
    for path, freq, priority in static:
        rows.append(f"  <url><loc>{BASE}{path}</loc><lastmod>{today}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>")

    for item in briefing_index.get("items", []):
        key = str(item.get("key") or "")
        if not key:
            continue
        collected = str(item.get("collected_at", today))[:10]
        rows.append(
            f"  <url><loc>{BASE}/briefing/{esc(key)}/</loc>"
            f"<lastmod>{collected}</lastmod><changefreq>{'hourly' if key == today else 'never'}</changefreq><priority>0.8</priority></url>"
        )

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
    briefing_index = read_json(BRIEFING_INDEX_PATH, {"items": []})
    latest = read_json(LATEST_PATH, {})
    archive = read_json(DATA / "archive.json", {})
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

    write_briefing_pages(briefing_index)
    write_sitemap(index, briefing_index)
    write_feed(latest)
    write_search_index(archive, latest)
    print("SEO ranking pages, daily briefing articles, sitemap, RSS feed, and search index updated.")


if __name__ == "__main__":
    main()
