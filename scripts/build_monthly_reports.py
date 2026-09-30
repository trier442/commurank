#!/usr/bin/env python3
from __future__ import annotations

import calendar
import html
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "reports" / "monthly"
BASE = "https://commurank.kr"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def esc(v) -> str:
    return html.escape(str(v or ""), quote=True)


def fmt(v) -> str:
    try:
        return f"{int(v or 0):,}"
    except Exception:
        return "0"


def parse_month(key: str):
    try:
        year, month = map(int, key.split("-"))
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        return start, end
    except Exception:
        return None, None


def shell(title: str, desc: str, canonical: str, body: str, structured=None) -> str:
    ld = ""
    if structured:
        ld = '<script type="application/ld+json">' + json.dumps(
            structured, ensure_ascii=False, separators=(",", ":")
        ).replace("</", "<\\/") + "</script>"
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="theme-color" content="#5b45ff" />
  <meta name="robots" content="index,follow" />
  <meta name="description" content="{esc(desc)}" />
  <meta property="og:site_name" content="커뮤랭크" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{esc(canonical)}" />
  <meta property="og:locale" content="ko_KR" />
  <link rel="canonical" href="{esc(canonical)}" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="manifest" href="/manifest.webmanifest" />
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="/styles.css" />
  {ld}
</head>
<body>
<header class="site-header">
  <div class="shell search-header">
    <a class="brand" href="/" aria-label="커뮤랭크 홈"><span class="brand-mark">C</span><span><strong>커뮤랭크</strong><small>COMMURANK</small></span></a>
    <form class="global-search global-search-wide" action="/search/" method="get" role="search"><input type="search" name="q" placeholder="게시글·키워드·커뮤니티 검색" /><button type="submit">검색</button></form>
    <button id="themeToggle" class="icon-button" aria-label="테마 전환">◐</button>
  </div>
</header>
<main>{body}</main>
<footer><div class="shell footer-inner"><div><strong>커뮤랭크</strong><p>대한민국 커뮤니티 인기글 랭킹 아카이브</p></div><p>원문은 각 커뮤니티에서 확인합니다.</p></div></footer>
<script src="/analytics.js"></script>
<script>
document.querySelector("#themeToggle").addEventListener("click",()=>{{document.body.classList.toggle("dark");localStorage.setItem("commurank-theme",document.body.classList.contains("dark")?"dark":"light")}});
if(localStorage.getItem("commurank-theme")==="dark") document.body.classList.add("dark");
</script>
</body>
</html>"""


def aggregate_briefings(items, start: date, end: date):
    selected = []
    for item in items:
        try:
            d = datetime.strptime(item.get("key", ""), "%Y-%m-%d").date()
        except Exception:
            continue
        if start <= d <= end:
            selected.append(read_json(DATA / item.get("path", ""), {}))

    keywords = {}
    issues = {}
    for briefing in selected:
        day = briefing.get("date", "")
        for row in briefing.get("keywords", []):
            key = str(row.get("keyword") or "").strip()
            if not key:
                continue
            rec = keywords.setdefault(key, {
                "keyword": key, "days": set(), "sources": set(),
                "score": 0.0, "posts": 0
            })
            rec["days"].add(day)
            rec["sources"].update(row.get("sources") or [])
            rec["score"] = max(rec["score"], float(row.get("score", 0) or 0))
            rec["posts"] = max(rec["posts"], int(row.get("post_count", 0) or 0))

        for row in briefing.get("issues", []):
            iid = str(row.get("id") or row.get("title") or "")
            if not iid:
                continue
            rec = issues.setdefault(iid, {
                "id": row.get("id", ""),
                "title": row.get("title", ""),
                "days": set(),
                "keywords": set(),
                "source_count": 0,
                "post_count": 0,
                "score": 0.0,
            })
            rec["days"].add(day)
            rec["keywords"].update(row.get("keywords") or [])
            rec["source_count"] = max(rec["source_count"], int(row.get("source_count", 0) or 0))
            rec["post_count"] = max(rec["post_count"], int(row.get("post_count", 0) or 0))
            rec["score"] = max(rec["score"], float(row.get("score", 0) or 0))

    keyword_rows = sorted(
        keywords.values(),
        key=lambda x: (len(x["days"]), len(x["sources"]), x["score"], x["posts"]),
        reverse=True,
    )
    issue_rows = sorted(
        issues.values(),
        key=lambda x: (len(x["days"]), x["source_count"], x["score"], x["post_count"]),
        reverse=True,
    )
    return selected, keyword_rows, issue_rows


def report_page(item, briefing_index):
    snap = read_json(DATA / item.get("path", ""), {})
    posts = snap.get("posts", []) if isinstance(snap, dict) else []
    key = str(item.get("key") or "")
    start, end = parse_month(key)
    if not start or not end:
        return ""

    selected, keywords, issues = aggregate_briefings(briefing_index.get("items", []), start, end)
    covered_days = sorted({b.get("date") for b in selected if b.get("date")})
    today = datetime.now().date()

    if start <= today <= end:
        status = "집계 중"
    elif len(covered_days) >= 20:
        status = "월간 확정"
    else:
        status = "부분 집계"

    sources = sorted({p.get("source") for p in posts if p.get("source")})
    category_counts = Counter(p.get("category") or "이슈" for p in posts)
    leaders = {}
    for p in posts:
        source = p.get("source")
        if source and (source not in leaders or float(p.get("score", 0) or 0) > float(leaders[source].get("score", 0) or 0)):
            leaders[source] = p

    persistent = sorted(
        posts,
        key=lambda p: (
            int(p.get("active_days", 0) or 0),
            int(p.get("appearances", 0) or 0),
            float(p.get("score", 0) or 0),
        ),
        reverse=True,
    )

    top_keywords = ", ".join("#" + row["keyword"] for row in keywords[:6]) if keywords else "집계 중"
    top_issue = issues[0]["title"] if issues else "동시 화제 데이터 집계 중"
    coverage_text = f"{len(covered_days)}일치 브리핑 데이터" if covered_days else "브리핑 데이터 축적 중"
    desc = f"{item.get('label')} 커뮤니티 월간 트렌드 리포트. 월간 인기글, 반복 키워드, 지속 화제와 커뮤니티별 대표 글을 데이터로 정리합니다."

    paragraphs = [
        f"{item.get('label')} 커뮤랭크 월간 집계에는 {len(posts)}개의 상위 인기글과 {len(sources)}개 커뮤니티가 반영됐습니다. 현재 리포트 상태는 ‘{status}’이며 {coverage_text}를 바탕으로 정리했습니다.",
        f"월간 키워드에서는 {top_keywords} 등이 반복적으로 포착됐습니다. 단순 한 번의 등장보다 여러 날짜와 여러 커뮤니티에서 반복된 표현을 우선해 보여 줍니다.",
        f"여러 커뮤니티에서 함께 포착된 이슈 중 상위에는 ‘{top_issue}’가 나타났습니다. 이는 인기글 제목에서 동시 또는 반복적으로 관련 표현이 포착됐다는 의미이며, 해당 내용에 대한 사실 판정이나 찬반 평가를 뜻하지 않습니다.",
        "월간 리포트는 공개 인기글 목록의 제목과 조회·추천·댓글, 노출 지속성 데이터를 바탕으로 자동 정리한 통계 요약입니다. 커뮤니티 이용자 전체나 인터넷 전체 여론을 대표하지 않습니다.",
    ]

    top_posts_html = "".join(
        f'<article class="brief-list-row"><span class="brief-rank">{i}</span><div><a href="{esc(p.get("url"))}" target="_blank" rel="noopener noreferrer">{esc(p.get("title"))}</a><small>{esc(p.get("source"))} · 조회 {fmt(p.get("views"))} · 댓글 {fmt(p.get("comments"))} · 활동 {int(p.get("active_days",0) or 0)}일</small></div></article>'
        for i, p in enumerate(posts[:15], 1)
    ) or '<div class="empty">월간 인기글 데이터가 없습니다.</div>'

    keyword_html = "".join(
        f'<a href="/search/?q={quote(row["keyword"], safe="")}">#{esc(row["keyword"])}<span>{len(row["days"])}일 · {len(row["sources"])}곳</span></a>'
        for row in keywords[:20]
    ) or '<div class="empty">키워드 데이터가 아직 충분하지 않습니다.</div>'

    issue_html = "".join(
        f'<article class="daily-brief-topic"><span>{i}</span><div><a href="/issue/?id={quote(str(row.get("id") or ""), safe="")}">{esc(row.get("title"))}</a><p>{len(row["days"])}일 포착 · 최대 {row["source_count"]}개 커뮤니티 · 관련글 {row["post_count"]}건</p><div>{" ".join("#"+esc(k) for k in list(row["keywords"])[:4])}</div></div></article>'
        for i, row in enumerate(issues[:10], 1)
    ) or '<div class="empty">동시 화제 데이터가 아직 충분하지 않습니다.</div>'

    persistent_html = "".join(
        f'<article class="brief-list-row"><span class="brief-rank">{i}</span><div><a href="{esc(p.get("url"))}" target="_blank" rel="noopener noreferrer">{esc(p.get("title"))}</a><small>{esc(p.get("source"))} · {int(p.get("active_days",0) or 0)}일 · 인기목록 {int(p.get("appearances",0) or 0)}회 포착</small></div></article>'
        for i, p in enumerate(persistent[:10], 1)
    ) or '<div class="empty">지속성 데이터가 없습니다.</div>'

    leader_html = "".join(
        f'<article class="brief-list-row"><span class="brief-rank">{i}</span><div><a href="{esc(p.get("url"))}" target="_blank" rel="noopener noreferrer">{esc(source)} · {esc(p.get("title"))}</a><small>조회 {fmt(p.get("views"))} · 댓글 {fmt(p.get("comments"))}</small></div></article>'
        for i, (source, p) in enumerate(sorted(leaders.items()), 1)
    )

    category_html = "".join(
        f'<div class="weekly-category-row"><strong>{esc(cat)}</strong><span>{count}건</span><i style="--share:{max(5, round(count/max(1,len(posts))*100))}%"></i></div>'
        for cat, count in category_counts.most_common(10)
    )

    body = f"""
    <article class="shell weekly-report monthly-report">
      <header class="daily-brief-header">
        <p class="eyebrow">MONTHLY INTERNET TREND REPORT</p>
        <h1>{esc(item.get("label"))}<br><span>월간 인터넷 트렌드</span></h1>
        <p>{esc(desc)}</p>
        <div class="archive-page-nav"><a href="/reports/monthly/">월간 리포트 목록</a><a href="/ranking/monthly/{esc(key)}/">월간 TOP100 →</a></div>
      </header>

      <section class="daily-brief-stats">
        <div><strong>{len(sources)}</strong><span>반영 커뮤니티</span></div>
        <div><strong>{len(posts)}</strong><span>월간 상위 글</span></div>
        <div><strong>{len(covered_days)}</strong><span>브리핑 집계 일수</span></div>
        <div><strong>{esc(status)}</strong><span>리포트 상태</span></div>
      </section>

      <div class="daily-brief-layout">
        <main class="daily-brief-main">
          <section class="briefing-card daily-brief-copy"><div class="briefing-card-head"><div><span>MONTHLY SUMMARY</span><h2>이번 달 흐름</h2></div></div>{''.join('<p>'+esc(p)+'</p>' for p in paragraphs)}</section>
          <section class="briefing-card"><div class="briefing-card-head"><div><span>CROSS-COMMUNITY</span><h2>여러 커뮤니티에서 반복된 화제</h2></div></div><div class="daily-brief-topics">{issue_html}</div></section>
          <section class="briefing-card"><div class="briefing-card-head"><div><span>MONTHLY TOP15</span><h2>월간 인기글 TOP15</h2></div></div>{top_posts_html}</section>
          <section class="briefing-card"><div class="briefing-card-head"><div><span>PERSISTENCE</span><h2>오래 이어진 인기글</h2></div></div>{persistent_html}</section>
        </main>

        <aside class="daily-brief-side">
          <section class="briefing-card"><div class="briefing-card-head"><div><span>KEYWORDS</span><h2>월간 키워드</h2></div></div><div class="daily-brief-keywords">{keyword_html}</div></section>
          <section class="briefing-card"><div class="briefing-card-head"><div><span>CATEGORIES</span><h2>카테고리 분포</h2></div></div><div class="weekly-category-list">{category_html}</div></section>
          <section class="briefing-card"><div class="briefing-card-head"><div><span>COMMUNITIES</span><h2>커뮤니티별 대표 글</h2></div></div>{leader_html}</section>
        </aside>
      </div>
    </article>"""

    structured = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{item.get('label')} 월간 인터넷 트렌드 리포트",
        "description": desc,
        "datePublished": start.isoformat(),
        "dateModified": item.get("collected_at", end.isoformat()),
        "mainEntityOfPage": f"{BASE}/reports/monthly/{key}/",
        "publisher": {"@type": "Organization", "name": "커뮤랭크", "url": BASE},
    }

    return shell(
        f"{item.get('label')} 월간 인터넷 트렌드 | 커뮤랭크",
        desc,
        f"{BASE}/reports/monthly/{key}/",
        body,
        structured,
    )


def index_page(items):
    rows = "".join(
        f'<a class="archive-index-row" href="/reports/monthly/{esc(item.get("key"))}/"><strong>{esc(item.get("label"))} 월간 트렌드</strong><span>리포트 보기 →</span></a>'
        for item in items
    )
    body = f"""
    <section class="shell info-hero">
      <p class="eyebrow">MONTHLY TREND ARCHIVE</p>
      <h1>월간 인터넷<br>트렌드 리포트</h1>
      <p>한 달 동안 여러 커뮤니티에서 반복된 키워드, 동시 화제, 인기글 지속성과 커뮤니티별 대표 글을 데이터 중심으로 정리합니다.</p>
    </section>
    <section class="shell info-layout">
      <div class="info-main"><section class="info-card"><h2>월간 리포트</h2><div class="archive-index-list">{rows or '<div class="empty">월간 데이터를 쌓는 중입니다.</div>'}</div></section></div>
      <aside class="info-side"><nav class="info-nav"><a href="/reports/weekly/">주간 리포트</a><a href="/briefing/archive/">일간 브리핑</a><a href="/ranking/monthly/">월간 TOP100</a></nav></aside>
    </section>"""
    return shell(
        "월간 인터넷 트렌드 리포트 | 커뮤랭크",
        "월간 커뮤니티 인기글·키워드·동시 화제·지속성 데이터 리포트",
        f"{BASE}/reports/monthly/",
        body,
        {"@context":"https://schema.org","@type":"CollectionPage","name":"커뮤랭크 월간 인터넷 트렌드 리포트","url":f"{BASE}/reports/monthly/"},
    )


def update_sitemap(items):
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [(f"{BASE}/reports/monthly/", "weekly", "0.8", today)]
    for item in items:
        urls.append((
            f"{BASE}/reports/monthly/{item.get('key')}/",
            "monthly",
            "0.8",
            str(item.get("collected_at", today))[:10],
        ))
    for loc, freq, priority, lastmod in urls:
        if loc in text:
            continue
        row = f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>\n"
        text = text.replace("</urlset>", row + "</urlset>")
    path.write_text(text, encoding="utf-8")


def main():
    archive_index = read_json(DATA / "archive-index.json", {"periods": {}})
    briefing_index = read_json(DATA / "briefing-index.json", {"items": []})
    items = archive_index.get("periods", {}).get("monthly", [])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(index_page(items), encoding="utf-8")
    for item in items:
        out_dir = OUT / str(item.get("key"))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(report_page(item, briefing_index), encoding="utf-8")
    update_sitemap(items)
    print(f"Monthly reports updated: {len(items)}")


if __name__ == "__main__":
    main()
