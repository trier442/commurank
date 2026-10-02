#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from difflib import SequenceMatcher
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LATEST_PATH = DATA_DIR / "latest.json"
ARCHIVE_PATH = DATA_DIR / "archive.json"
ARCHIVE_INDEX_PATH = DATA_DIR / "archive-index.json"
METRICS_HISTORY_PATH = DATA_DIR / "metric-history.json"
ISSUE_HISTORY_PATH = DATA_DIR / "issue-history.json"
ISSUE_RANKINGS_PATH = DATA_DIR / "issue-rankings.json"
BRIEFING_PATH = DATA_DIR / "briefing.json"
BRIEFING_INDEX_PATH = DATA_DIR / "briefing-index.json"
BRIEFING_SNAPSHOT_DIR = DATA_DIR / "briefings"
ISSUE_ARCHIVE_INDEX_PATH = DATA_DIR / "issue-archive-index.json"
ISSUE_SNAPSHOT_DIR = DATA_DIR / "issue-snapshots"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
SOURCE_CACHE_DIR = DATA_DIR / "source-cache"
EXCLUDED_SOURCES = {"에펨코리아"}

SOURCE_CACHE_FILES = {
    "루리웹": "ruliweb.json",
    "디시인사이드": "dcinside.json",
    "더쿠": "theqoo.json",
    "뽐뿌": "ppomppu.json",
    "클리앙": "clien.json",
    "인벤": "inven.json",
}

KST = timezone(timedelta(hours=9))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0 Safari/537.36 CommurankBot/0.1"
)

SITES = {
    "루리웹": "https://bbs.ruliweb.com/best",
    "디시인사이드": "https://gall.dcinside.com/board/lists/?id=dcbest",
    "더쿠": "https://theqoo.net/hot",
    "뽐뿌": "https://www.ppomppu.co.kr/hot.php",
    "클리앙": "https://www.clien.net/service/board/park",
    "인벤": "https://www.inven.co.kr/board/webzine/2097",
}

CATEGORY_KEYWORDS = {
    "스포츠": ["축구", "야구", "농구", "경기", "선수", "감독", "리그", "골", "올림픽", "아시안게임"],
    "연예": ["아이돌", "가수", "배우", "방송", "드라마", "영화", "콘서트", "컴백", "연예"],
    "게임": ["게임", "스팀", "플스", "PS5", "닌텐도", "엑스박스", "롤 ", "LOL", "메이플", "던파"],
    "생활": ["직장", "회사", "여행", "음식", "맛집", "편의점", "카페", "육아", "건강", "집"],
    "유머": ["ㅋㅋ", "웃", "유머", "레전드", "짤", "드립"],
    "이슈": ["속보", "논란", "발표", "공개", "사건", "이슈", "뉴스"],
}


def parse_number(value: str | None) -> int:
    if not value:
        return 0
    value = value.replace(",", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", value)
    if not m:
        return 0
    number = float(m.group())
    lower = value.lower()
    if "만" in value:
        number *= 10000
    elif "천" in value:
        number *= 1000
    elif "k" in lower:
        number *= 1000
    elif "m" in lower:
        number *= 1000000
    return max(0, int(number))


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_category(raw: str | None, title: str) -> str:
    raw = clean_text(raw)
    haystack = f"{raw} {title}"
    for category, words in CATEGORY_KEYWORDS.items():
        if any(word.lower() in haystack.lower() for word in words):
            return category
    if raw and any(k in raw.lower() for k in ["유머", "웃긴"]):
        return "유머"
    return "이슈"


def request_html(url: str, *, referer: str | None = None, user_agent: str | None = None) -> BeautifulSoup:
    headers = {
        "User-Agent": user_agent or USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
        "Cache-Control": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return BeautifulSoup(response.text, "html.parser")


def post(source: str, title: str, url: str, category: str | None = None,
         views: int = 0, likes: int = 0, comments: int = 0) -> dict:
    return {
        "source": source,
        "title": clean_text(title),
        "url": url,
        "category": normalize_category(category, title),
        "views": int(views or 0),
        "likes": int(likes or 0),
        "comments": int(comments or 0),
    }


def scrape_ruliweb() -> list[dict]:
    base = "https://bbs.ruliweb.com"
    soup = request_html(SITES["루리웹"])
    items = []
    for row in soup.select("table.board_list_table tr.table_body"):
        link = row.select_one("td.subject a.subject_link")
        title_node = row.select_one("td.subject strong.text_over, td.subject span.text_over")
        if not link or not title_node or not link.get("href"):
            continue
        items.append(post(
            "루리웹",
            title_node.get_text(" ", strip=True),
            urljoin(base, link["href"]),
            views=parse_number(row.select_one("td.hit").get_text() if row.select_one("td.hit") else ""),
            likes=parse_number(row.select_one("td.recomd").get_text() if row.select_one("td.recomd") else ""),
            comments=parse_number(row.select_one("span.num_reply").get_text() if row.select_one("span.num_reply") else ""),
        ))
    return items


def scrape_dcinside() -> list[dict]:
    base = "https://gall.dcinside.com"
    soup = request_html(SITES["디시인사이드"], referer="https://gall.dcinside.com/")
    items = []
    for row in soup.select("tr.ub-content.us-post"):
        link = row.select_one("td.gall_tit a")
        if not link or not link.get("href"):
            continue
        title = clean_text(link.get_text(" ", strip=True))
        strong = link.select_one("strong")
        raw_category = clean_text(strong.get_text(" ", strip=True)) if strong else ""
        if raw_category:
            title = clean_text(title.replace(raw_category, "", 1))
        if not title:
            continue
        items.append(post(
            "디시인사이드",
            title,
            urljoin(base, link["href"]),
            category=raw_category,
            views=parse_number(row.select_one("td.gall_count").get_text() if row.select_one("td.gall_count") else ""),
            likes=parse_number(row.select_one("td.gall_recommend").get_text() if row.select_one("td.gall_recommend") else ""),
            comments=parse_number(row.select_one(".reply_num").get_text() if row.select_one(".reply_num") else ""),
        ))
    return items


def scrape_theqoo() -> list[dict]:
    base = "https://theqoo.net"
    soup = request_html(SITES["더쿠"])
    items = []
    for row in soup.select("table.theqoo_board_table tbody tr"):
        classes = set(row.get("class") or [])
        if "notice" in classes or "notice_expand" in classes:
            continue
        link = row.select_one("td.title > a")
        if not link or not link.get("href"):
            continue
        title = clean_text(link.get_text(" ", strip=True))
        if not title:
            continue
        items.append(post(
            "더쿠",
            title,
            urljoin(base, link["href"]),
            category=clean_text(row.select_one("td.cate span").get_text() if row.select_one("td.cate span") else ""),
            views=parse_number(row.select_one("td.m_no").get_text() if row.select_one("td.m_no") else ""),
            comments=parse_number(row.select_one("td.title a.replyNum").get_text() if row.select_one("td.title a.replyNum") else ""),
        ))
    return items


def scrape_ppomppu() -> list[dict]:
    base = "https://www.ppomppu.co.kr"
    soup = request_html(SITES["뽐뿌"])
    items = []
    for row in soup.select('table.board_table tr[class*="baseList"]'):
        links = row.select("td.title a.baseList-title")
        if not links:
            continue
        link = links[1] if len(links) > 1 else links[0]
        href = link.get("href")
        title = clean_text(link.get_text(" ", strip=True))
        if not href or not title:
            continue
        tds = row.select("td")
        likes = parse_number(tds[5].get_text()) if len(tds) > 5 else 0
        views = parse_number(tds[6].get_text()) if len(tds) > 6 else 0
        items.append(post(
            "뽐뿌",
            title,
            urljoin(base, href),
            category=clean_text(row.select_one("td.baseList-numb a").get_text() if row.select_one("td.baseList-numb a") else ""),
            views=views,
            likes=likes,
            comments=parse_number(row.select_one("span.list_comment2").get_text() if row.select_one("span.list_comment2") else ""),
        ))
    return items


def scrape_clien() -> list[dict]:
    base = "https://www.clien.net"
    soup = request_html(SITES["클리앙"])
    items = []
    for row in soup.select("div.list_item"):
        link = row.select_one("a.list_subject")
        if not link or not link.get("href"):
            continue
        title_node = row.select_one("span.subject_fixed")
        title = clean_text(title_node.get("title") if title_node and title_node.get("title") else title_node.get_text(" ", strip=True) if title_node else "")
        if not title:
            continue
        comments = parse_number(row.get("data-comment-count"))
        if comments == 0:
            cmt = row.select_one("span.rSymph05")
            comments = parse_number(cmt.get_text() if cmt else "")
        hit = row.select_one("span.hit")
        views = parse_number(hit.get_text() if hit else "")
        if not hit:
            continue
        like = row.select_one('[data-role="list-like-count"] span')
        items.append(post(
            "클리앙",
            title,
            urljoin(base, link["href"]),
            views=views,
            likes=parse_number(like.get_text() if like else ""),
            comments=comments,
        ))
    return items


def scrape_inven() -> list[dict]:
    base = "https://www.inven.co.kr"
    soup = request_html(SITES["인벤"])
    items = []
    for row in soup.select("tr"):
        classes = set(row.get("class") or [])
        if "notice" in classes or row.select_one("span.notice-icon"):
            continue
        cell = row.select_one("td.tit")
        link = cell.select_one("a.subject-link") if cell else None
        if not link or not link.get("href"):
            continue
        category_node = link.select_one("span.category")
        raw_category = clean_text(category_node.get_text(" ", strip=True) if category_node else "")
        if category_node:
            category_node.extract()
        title = clean_text(link.get_text(" ", strip=True))
        if not title:
            continue
        view_node = row.select_one("td.view")
        if not view_node:
            continue
        reco_node = row.select_one("td.reco")
        cmt_node = cell.select_one("span.con-comment") if cell else None
        items.append(post(
            "인벤",
            title,
            urljoin(base, link["href"]),
            category=raw_category,
            views=parse_number(view_node.get_text()),
            likes=parse_number(reco_node.get_text() if reco_node else ""),
            comments=parse_number(cmt_node.get_text() if cmt_node else ""),
        ))
    return items


SCRAPERS = {
    "루리웹": scrape_ruliweb,
    "디시인사이드": scrape_dcinside,
    "더쿠": scrape_theqoo,
    "뽐뿌": scrape_ppomppu,
    "클리앙": scrape_clien,
    "인벤": scrape_inven,
}


def percentile(values: list[int], value: int) -> float:
    if not values:
        return 0.5
    ordered = sorted(values)
    if len(ordered) == 1:
        return 1.0
    below = sum(1 for x in ordered if x < value)
    equal = sum(1 for x in ordered if x == value)
    return min(1.0, max(0.0, (below + 0.5 * equal) / len(ordered)))


def score_source(items: list[dict]) -> list[dict]:
    n = len(items)
    view_values = [p["views"] for p in items if p["views"] > 0]
    like_values = [p["likes"] for p in items if p["likes"] > 0]
    comment_values = [p["comments"] for p in items if p["comments"] > 0]

    for i, p in enumerate(items):
        position = 1.0 if n <= 1 else 1 - i / (n - 1)
        metrics = []
        if p["views"] > 0:
            metrics.append(percentile(view_values, p["views"]))
        if p["likes"] > 0:
            metrics.append(percentile(like_values, p["likes"]))
        if p["comments"] > 0:
            metrics.append(percentile(comment_values, p["comments"]))
        engagement = sum(metrics) / len(metrics) if metrics else 0.5
        p["score"] = round(100 * (0.6 * position + 0.4 * engagement), 2)
    return items


TOPIC_STOPWORDS = {
    "오늘", "요즘", "지금", "현재", "진짜", "관련", "반응", "근황", "결과", "이유", "정리",
    "공개", "발표", "논란", "소식", "사진", "영상", "장면", "사람", "이야기", "게시글",
    "대한", "에서", "으로", "그리고", "하지만", "그런데", "했다", "하는", "있는", "없는",
    "jpg", "gif", "mp4", "webp", "ㅋㅋ", "ㅋㅋㅋ", "ㄷㄷ", "속보",
    "사람들", "레전드", "한국인", "애들이", "사람이", "사람은", "같은", "이런", "저런",
    "이거", "이게", "이번", "정도", "생각", "사실", "하나", "모두", "정말", "그냥",
    "현황", "가장", "avi", "싶다는", "맞고", "신고한", "도전", "남자", "여자",
    "선수", "배우", "공연", "사장님", "대통령",
    "근데", "문제", "싱글벙글", "안싱글벙글", "대충", "의외로", "알고보니", "알고보면",
    "너무", "보고", "ad", "넣었더니", "무려", "최고", "최고의", "여사",
    "manhwa", "유튜버", "유튜브", "관광객", "대통령", "때문에", "때문", "실수로", "떨어지는", "머리가", "머리"
}


def topic_tokens(title: str) -> set[str]:
    normalized = re.sub(r"[^0-9A-Za-z가-힣 ]+", " ", title.lower())
    tokens = []
    for token in normalized.split():
        token = token.strip()
        if len(token) < 2 or token in TOPIC_STOPWORDS:
            continue
        if token.isdigit() and len(token) < 3:
            continue
        tokens.append(token)
    return set(tokens)


def title_similarity(a: str, b: str) -> float:
    ta, tb = topic_tokens(a), topic_tokens(b)
    if not ta or not tb:
        return 0.0

    shared = ta & tb
    union = ta | tb
    jaccard = len(shared) / len(union)
    coverage = len(shared) / min(len(ta), len(tb))

    na = re.sub(r"\s+", "", re.sub(r"[^0-9A-Za-z가-힣 ]+", "", a.lower()))
    nb = re.sub(r"\s+", "", re.sub(r"[^0-9A-Za-z가-힣 ]+", "", b.lower()))
    seq = SequenceMatcher(None, na, nb).ratio() if na and nb else 0.0

    # 짧은 공통어 하나만으로는 서로 다른 이슈가 합쳐지지 않게 보수적으로 판정한다.
    if len(shared) >= 3:
        return max(jaccard, coverage * 0.95, seq * 0.9)
    if len(shared) == 2:
        return max(jaccard, coverage * 0.88, seq * 0.82)
    if len(shared) == 1:
        only = next(iter(shared))
        if len(only) >= 5 and seq >= 0.62:
            return max(coverage * 0.7, seq * 0.72)
        return 0.0
    return seq * 0.55 if seq >= 0.78 else 0.0


def issue_identity_anchor(keywords: list[str] | None, title: str = "") -> str:
    identity_tokens = {
        normalize_keyword_token(token)
        for token in (keywords or [])
        if normalize_keyword_token(token)
        and normalize_keyword_token(token) not in TOPIC_STOPWORDS
        and not re.fullmatch(r"\d{2}대", normalize_keyword_token(token))
    }
    if not identity_tokens:
        identity_tokens = {
            token for token in keyword_tokens(title)
            if token not in TOPIC_STOPWORDS and not re.fullmatch(r"\d{2}대", token)
        }
    return (
        sorted(identity_tokens, key=lambda token: (-len(token), token))[0]
        if identity_tokens
        else ""
    )


def issue_id_from_anchor(anchor: str) -> str:
    h = 2166136261
    for byte in anchor.encode("utf-8"):
        h ^= byte
        h = (h * 16777619) & 0xFFFFFFFF
    return f"i{h:08x}"


def build_topics(posts: list[dict], limit: int = 8) -> list[dict]:
    ranked = [{**p, "rank": i + 1} for i, p in enumerate(posts)]
    topics = []

    # 1) 제목 전체가 상당히 닮은 게시물은 같은 사건으로 묶는다.
    clusters: list[dict] = []
    for p in ranked:
        best_cluster = None
        best_similarity = 0.0

        for cluster in clusters:
            similarities = [title_similarity(p["title"], item["title"]) for item in cluster["posts"]]
            similarity = max(similarities) if similarities else 0.0
            if similarity > best_similarity:
                best_similarity = similarity
                best_cluster = cluster

        if best_cluster is not None and best_similarity >= 0.44:
            best_cluster["posts"].append(p)
        else:
            clusters.append({"posts": [p]})

    for cluster in clusters:
        items = cluster["posts"]
        source_names = list(dict.fromkeys(item["source"] for item in items))
        if len(source_names) < 2:
            continue

        token_counts = Counter()
        for item in items:
            token_counts.update(topic_tokens(item["title"]))
        keywords = [token for token, count in token_counts.most_common(5) if count >= 2]

        representative = max(items, key=lambda x: (x.get("score", 0), -x["rank"]))
        source_best = {}
        for item in sorted(items, key=lambda x: x["rank"]):
            source_best.setdefault(item["source"], item)

        topics.append({
            "title": representative["title"],
            "source_count": len(source_names),
            "post_count": len(items),
            "score": round(max(float(item.get("score", 0)) for item in items) + (len(source_names) - 1) * 6 + min(6, len(items)), 2),
            "keywords": keywords,
            "posts": [
                {
                    "source": item["source"],
                    "rank": item["rank"],
                    "title": item["title"],
                    "url": item["url"],
                    "score": item.get("score", 0),
                }
                for item in list(source_best.values())[:6]
            ],
        })

    # 2) 서로 다른 제목이어도 같은 고유 키워드가 여러 커뮤니티에서 동시에 뜨면
    #    '동시 화제'로 잡는다. 단, 흔한 일반어는 STOPWORDS에서 제외한다.
    token_posts: dict[str, list[dict]] = {}
    for item in ranked:
        for token in topic_tokens(item["title"]):
            if len(token) < 3 or token.isdigit():
                continue
            if re.fullmatch(r"\d{2}대", token):
                continue
            if token in TOPIC_STOPWORDS:
                continue
            token_posts.setdefault(token, []).append(item)

    for token, items in token_posts.items():
        source_names = list(dict.fromkeys(item["source"] for item in items))
        if len(source_names) < 2:
            continue

        source_best = {}
        for item in sorted(items, key=lambda x: x["rank"]):
            source_best.setdefault(item["source"], item)
        best_items = list(source_best.values())

        # 이미 제목 유사도 클러스터에서 거의 같은 글들이 묶였으면 중복 생성하지 않는다.
        candidate_urls = {item["url"] for item in best_items}
        duplicate = False
        for topic in topics:
            topic_urls = {item["url"] for item in topic["posts"]}
            overlap = len(candidate_urls & topic_urls)
            if overlap >= 2 and overlap / max(1, min(len(candidate_urls), len(topic_urls))) >= 0.66:
                if token not in topic["keywords"]:
                    topic["keywords"].append(token)
                duplicate = True
                break
        if duplicate:
            continue

        peak = max(float(item.get("score", 0)) for item in best_items)
        topics.append({
            "title": f"‘{token}’ 관련 글이 여러 커뮤니티에서 화제",
            "source_count": len(source_names),
            "post_count": len(items),
            "score": round(peak + (len(source_names) - 1) * 7 + min(5, len(items)), 2),
            "keywords": [token],
            "posts": [
                {
                    "source": item["source"],
                    "rank": item["rank"],
                    "title": item["title"],
                    "url": item["url"],
                    "score": item.get("score", 0),
                }
                for item in best_items[:6]
            ],
        })

    ranked_topics = sorted(
        topics,
        key=lambda t: (t["source_count"], t["post_count"], t["score"]),
        reverse=True,
    )

    # 같은 핵심 이슈가 제목 유사도 클러스터와 키워드 클러스터에서
    # 동시에 만들어질 수 있으므로 안정 ID 기준으로 최종 병합한다.
    merged_topics: dict[str, dict] = {}
    synthetic_pattern = re.compile(r"^[‘'](.+?)[’'] 관련 글이 여러 커뮤니티에서 화제$")

    for topic in ranked_topics:
        anchor = issue_identity_anchor(topic.get("keywords", []), topic.get("title", ""))
        if not anchor:
            continue
        issue_id = issue_id_from_anchor(anchor)
        topic["id"] = issue_id

        if issue_id not in merged_topics:
            merged_topics[issue_id] = dict(topic)
            merged_topics[issue_id]["posts"] = list(topic.get("posts", []))
            merged_topics[issue_id]["keywords"] = list(topic.get("keywords", []))
            continue

        base = merged_topics[issue_id]

        # 더 구체적인 실제 게시글 제목을 합성 제목보다 우선한다.
        base_is_synthetic = bool(synthetic_pattern.match(base.get("title", "")))
        topic_is_synthetic = bool(synthetic_pattern.match(topic.get("title", "")))
        if base_is_synthetic and not topic_is_synthetic:
            base["title"] = topic.get("title", base.get("title", ""))

        seen_urls = {p.get("url") for p in base.get("posts", []) if p.get("url")}
        for post_item in topic.get("posts", []):
            url = post_item.get("url")
            if url and url not in seen_urls:
                base.setdefault("posts", []).append(post_item)
                seen_urls.add(url)

        base["keywords"] = list(dict.fromkeys(
            list(base.get("keywords", [])) + list(topic.get("keywords", []))
        ))[:8]
        source_names = {
            p.get("source")
            for p in base.get("posts", [])
            if p.get("source")
        }
        base["source_count"] = len(source_names)
        base["post_count"] = len(base.get("posts", []))
        base["score"] = max(float(base.get("score", 0)), float(topic.get("score", 0)))

    return sorted(
        merged_topics.values(),
        key=lambda t: (t["source_count"], t["post_count"], t["score"]),
        reverse=True,
    )[:limit]

def normalize_keyword_token(token: str) -> str:
    token = token.strip().lower()
    if not token:
        return ""
    suffixes = [
        "에서는", "으로는", "에게는", "까지는", "부터는",
        "에서", "으로", "에게", "까지", "부터", "처럼", "보다",
        "하고", "이며", "에는", "에도", "과는", "와는",
        "은", "는", "이", "가", "을", "를", "의", "에", "와", "과", "도", "만",
    ]
    if re.fullmatch(r"[가-힣]+", token):
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                token = token[:-len(suffix)]
                break
    return token


def keyword_tokens(title: str) -> set[str]:
    result = set()
    for token in topic_tokens(title):
        normalized = normalize_keyword_token(token)
        if not normalized or normalized in TOPIC_STOPWORDS:
            continue
        if len(normalized) < 2:
            continue
        if normalized.isdigit():
            continue
        result.add(normalized)
    return result


def compute_keyword_rows(posts: list[dict], limit: int = 40) -> list[dict]:
    token_map: dict[str, list[dict]] = {}
    for rank, post_item in enumerate(posts, start=1):
        enriched = {**post_item, "_rank": rank}
        for token in keyword_tokens(post_item.get("title", "")):
            token_map.setdefault(token, []).append(enriched)

    candidates = []
    for token, items in token_map.items():
        post_count = len(items)
        source_count = len({item.get("source") for item in items if item.get("source")})

        if post_count < 2:
            continue
        if source_count < 2 and post_count < 3:
            continue

        best_rank = min(item["_rank"] for item in items)
        avg_rank_strength = sum(max(0, 101 - item["_rank"]) / 100 for item in items) / post_count
        avg_score = sum(float(item.get("score", 0)) for item in items) / post_count
        keyword_score = (
            source_count * 22
            + post_count * 7
            + avg_rank_strength * 24
            + avg_score * 0.28
            + max(0, 20 - best_rank) * 0.35
        )

        urls = sorted({item.get("url") for item in items if item.get("url")})
        first_position = min(
            (
                str(item.get("title", "")).lower().find(token)
                for item in items
                if token in str(item.get("title", "")).lower()
            ),
            default=999,
        )

        candidates.append({
            "keyword": token,
            "score": round(keyword_score, 2),
            "post_count": post_count,
            "source_count": source_count,
            "best_rank": best_rank,
            "sources": sorted({item.get("source") for item in items if item.get("source")}),
            "_urls": urls,
            "_first_position": first_position,
        })

    # 같은 게시물 묶음에서 여러 단어가 동시에 잡히면 대표 키워드 하나만 남긴다.
    grouped: dict[tuple[str, ...], list[dict]] = {}
    for row in candidates:
        grouped.setdefault(tuple(row["_urls"]), []).append(row)

    rows = []
    for group in grouped.values():
        representative = max(
            group,
            key=lambda row: (
                len(row["keyword"]),
                -int(row.get("_first_position", 999)),
                row["score"],
            ),
        )
        representative = dict(representative)
        representative["aliases"] = sorted(
            {row["keyword"] for row in group if row["keyword"] != representative["keyword"]}
        )[:5]
        representative.pop("_urls", None)
        representative.pop("_first_position", None)
        rows.append(representative)

    rows.sort(
        key=lambda row: (
            row["score"],
            row["source_count"],
            row["post_count"],
            -row["best_rank"],
        ),
        reverse=True,
    )
    return rows[:limit]

def build_keyword_trends(current: list[dict], previous: dict, limit: int = 20) -> list[dict]:
    current_rows = compute_keyword_rows(current, limit=max(limit * 3, 40))

    previous_rows = []
    if isinstance(previous, dict):
        previous_rows = previous.get("keywords") or []
        if not previous_rows:
            previous_realtime = previous.get("rankings", {}).get("realtime", [])
            previous_rows = compute_keyword_rows(previous_realtime, limit=max(limit * 3, 40))

    old_rank = {row.get("keyword"): i + 1 for i, row in enumerate(previous_rows)}

    result = []
    for i, row in enumerate(current_rows[:limit], start=1):
        item = dict(row)
        before = old_rank.get(row["keyword"])
        item["rank"] = i
        item["change"] = "NEW" if before is None else before - i
        result.append(item)

    return result


def compute_source_keywords(posts: list[dict], limit: int = 12) -> list[dict]:
    token_map: dict[str, list[dict]] = {}
    for rank, post_item in enumerate(posts, start=1):
        enriched = {**post_item, "_rank": rank}
        for token in keyword_tokens(post_item.get("title", "")):
            token_map.setdefault(token, []).append(enriched)

    rows = []
    for token, items in token_map.items():
        if len(items) < 2:
            continue
        best_rank = min(item["_rank"] for item in items)
        score = (
            len(items) * 12
            + sum(max(0, 61 - item["_rank"]) / 60 for item in items) * 14
            + sum(float(item.get("score", 0)) for item in items) / len(items) * 0.22
        )
        rows.append({
            "keyword": token,
            "post_count": len(items),
            "best_rank": best_rank,
            "score": round(score, 2),
        })

    rows.sort(key=lambda row: (row["score"], row["post_count"], -row["best_rank"]), reverse=True)
    return rows[:limit]


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def period_rank(archive: dict, since: datetime, now: datetime, limit: int = 100) -> list[dict]:
    candidates = []
    since_date = since.astimezone(KST).date()

    for entry in archive.values():
        last_seen = dt(entry["last_seen"]).astimezone(KST)
        daily_stats = entry.get("daily_stats", {})
        period_days = []

        if isinstance(daily_stats, dict):
            for day_key, stats in daily_stats.items():
                try:
                    day = datetime.strptime(day_key, "%Y-%m-%d").date()
                except Exception:
                    continue
                if day >= since_date and isinstance(stats, dict):
                    period_days.append(stats)

        # 이전 데이터 구조와 호환: daily_stats가 없는 기존 항목은 마지막 포착만 사용한다.
        if not period_days:
            if last_seen < since:
                continue
            period_days = [{
                "max_score": float(entry.get("peak_score", 0)),
                "max_views": int(entry.get("max_views", 0)),
                "max_likes": int(entry.get("max_likes", 0)),
                "max_comments": int(entry.get("max_comments", 0)),
                "appearances": 1,
            }]

        period_appearances = sum(max(1, int(day.get("appearances", 1))) for day in period_days)
        active_days = len(period_days)
        period_peak_score = max(float(day.get("max_score", 0)) for day in period_days)
        period_views = max(int(day.get("max_views", 0)) for day in period_days)
        period_likes = max(int(day.get("max_likes", 0)) for day in period_days)
        period_comments = max(int(day.get("max_comments", 0)) for day in period_days)

        p = dict(entry)
        recency_hours = max(0, (now - last_seen).total_seconds() / 3600)
        recency_bonus = max(0, 8 - min(8, recency_hours / 12))
        repeat_bonus = min(10, math.log1p(period_appearances) * 2.2)
        persistence_bonus = min(6, max(0, active_days - 1) * 1.5)

        p["score"] = round(period_peak_score + recency_bonus + repeat_bonus + persistence_bonus, 2)
        p["views"] = period_views
        p["likes"] = period_likes
        p["comments"] = period_comments
        p["appearances"] = period_appearances
        p["active_days"] = active_days
        candidates.append(p)

    return sorted(
        candidates,
        key=lambda x: (x["score"], x["active_days"], x["appearances"], x["views"], x["comments"]),
        reverse=True,
    )[:limit]


def attach_rank_changes(rankings: dict[str, list[dict]], previous: dict) -> None:
    previous_rankings = previous.get("rankings", {}) if isinstance(previous, dict) else {}
    for period, items in rankings.items():
        old_map = {p.get("url"): i + 1 for i, p in enumerate(previous_rankings.get(period, []))}
        for i, p in enumerate(items):
            old_rank = old_map.get(p.get("url"))
            p["change"] = "NEW" if old_rank is None else old_rank - (i + 1)


def build_rising(current: list[dict], previous: dict, collected_at: str, limit: int = 50) -> tuple[list[dict], int]:
    previous_items = previous.get("rankings", {}).get("realtime", []) if isinstance(previous, dict) else []
    previous_map = {p.get("url"): {**p, "_rank": i + 1} for i, p in enumerate(previous_items) if p.get("url")}

    window_minutes = 30
    previous_at = previous.get("collected_at") if isinstance(previous, dict) else None
    if previous_at:
        try:
            before = dt(previous_at).astimezone(KST)
            after = dt(collected_at).astimezone(KST)
            window_minutes = max(1, round((after - before).total_seconds() / 60))
        except Exception:
            window_minutes = 30

    rows = []
    for rank, p in enumerate(current, start=1):
        old = previous_map.get(p.get("url"))
        row = dict(p)
        row["current_rank"] = rank
        row["new_entry"] = old is None

        if old:
            row["delta_views"] = max(0, int(p.get("views", 0)) - int(old.get("views", 0)))
            row["delta_likes"] = max(0, int(p.get("likes", 0)) - int(old.get("likes", 0)))
            row["delta_comments"] = max(0, int(p.get("comments", 0)) - int(old.get("comments", 0)))
            row["rank_gain"] = max(0, int(old.get("_rank", rank)) - rank)
        else:
            row["delta_views"] = 0
            row["delta_likes"] = 0
            row["delta_comments"] = 0
            row["rank_gain"] = 0

        rows.append(row)

    # 커뮤니티 규모 차이를 줄이기 위해 증가량을 각 사이트 내부 백분위로 정규화한다.
    by_source = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)

    for source_rows in by_source.values():
        view_values = [r["delta_views"] for r in source_rows if r["delta_views"] > 0]
        like_values = [r["delta_likes"] for r in source_rows if r["delta_likes"] > 0]
        comment_values = [r["delta_comments"] for r in source_rows if r["delta_comments"] > 0]
        gain_values = [r["rank_gain"] for r in source_rows if r["rank_gain"] > 0]

        for row in source_rows:
            if row["new_entry"]:
                # 신규 진입 글은 현재 사이트 내 인기점수가 높을 때만 급상승 후보가 된다.
                row["rising_score"] = round(42 + float(row.get("score", 0)) * 0.42, 2)
                continue

            pieces = []
            weights = []
            if row["delta_views"] > 0:
                pieces.append(percentile(view_values, row["delta_views"]))
                weights.append(0.45)
            if row["delta_likes"] > 0:
                pieces.append(percentile(like_values, row["delta_likes"]))
                weights.append(0.25)
            if row["delta_comments"] > 0:
                pieces.append(percentile(comment_values, row["delta_comments"]))
                weights.append(0.20)
            if row["rank_gain"] > 0:
                pieces.append(percentile(gain_values, row["rank_gain"]))
                weights.append(0.10)

            if weights:
                normalized = sum(v * w for v, w in zip(pieces, weights)) / sum(weights)
                row["rising_score"] = round(100 * normalized, 2)
            else:
                row["rising_score"] = round(float(row.get("score", 0)) * 0.35, 2)

    rising = sorted(
        rows,
        key=lambda r: (
            r.get("rising_score", 0),
            r.get("rank_gain", 0),
            r.get("delta_comments", 0),
            r.get("delta_likes", 0),
            r.get("delta_views", 0),
        ),
        reverse=True,
    )[:limit]

    for i, row in enumerate(rising, start=1):
        row["change"] = "NEW" if row.get("new_entry") else row.get("rank_gain", 0)
        row["rising_rank"] = i
        row["window_minutes"] = window_minutes

    return rising, window_minutes


def snapshot_meta(period: str, key: str, label: str, collected_at: str, path: Path) -> dict:
    return {
        "period": period,
        "key": key,
        "label": label,
        "collected_at": collected_at,
        "path": str(path.relative_to(DATA_DIR)).replace("\\", "/"),
    }


def write_period_snapshots(now: datetime, collected_at: str, rankings: dict[str, list[dict]]) -> list[dict]:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    iso_year, iso_week, _ = now.isocalendar()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=6)

    specs = [
        ("daily", now.strftime("%Y-%m-%d"), now.strftime("%Y년 %m월 %d일")),
        (
            "weekly",
            f"{iso_year}-W{iso_week:02d}",
            f"{week_start.strftime('%Y.%m.%d')} ~ {week_end.strftime('%m.%d')}",
        ),
        ("monthly", now.strftime("%Y-%m"), now.strftime("%Y년 %m월")),
    ]

    metas = []
    for period, key, label in specs:
        period_dir = SNAPSHOT_DIR / period
        period_dir.mkdir(parents=True, exist_ok=True)
        path = period_dir / f"{key}.json"
        posts = rankings.get(period, [])
        snap = {
            "version": 1,
            "period": period,
            "key": key,
            "label": label,
            "collected_at": collected_at,
            "timezone": "Asia/Seoul",
            "posts": posts,
            "topics": build_topics(posts),
        }
        path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
        metas.append(snapshot_meta(period, key, label, collected_at, path))
    return metas


def update_archive_index(new_metas: list[dict]) -> dict:
    index = load_json(ARCHIVE_INDEX_PATH, {"version": 1, "periods": {"daily": [], "weekly": [], "monthly": []}})
    index.setdefault("periods", {})
    limits = {"daily": 400, "weekly": 120, "monthly": 60}

    for meta in new_metas:
        period = meta["period"]
        items = index["periods"].setdefault(period, [])
        items = [item for item in items if item.get("key") != meta["key"]]
        items.append(meta)
        items.sort(key=lambda item: item.get("key", ""), reverse=True)
        index["periods"][period] = items[:limits[period]]

    index["updated_at"] = max((m["collected_at"] for m in new_metas), default=None)
    ARCHIVE_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


# Temporary source failures use the last successful cache.
def source_cache_path(source: str) -> Path:
    return SOURCE_CACHE_DIR / SOURCE_CACHE_FILES[source]


def save_source_cache(source: str, collected_at: str, posts: list[dict]) -> None:
    SOURCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source": source,
        "collected_at": collected_at,
        "posts": posts,
    }
    source_cache_path(source).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_source_cache(source: str, now: datetime, max_age_hours: int = 24) -> dict | None:
    path = source_cache_path(source)
    cached = load_json(path, None)
    if not isinstance(cached, dict) or not isinstance(cached.get("posts"), list):
        return None
    try:
        cached_at = dt(cached["collected_at"]).astimezone(KST)
        age_minutes = max(0, round((now - cached_at).total_seconds() / 60))
    except Exception:
        return None
    if age_minutes > max_age_hours * 60:
        return None
    cached["age_minutes"] = age_minutes
    return cached


def update_issue_history(topics: list[dict], collected_at: str) -> dict:
    history = load_json(ISSUE_HISTORY_PATH, {"version": 1, "issues": {}})
    history.setdefault("issues", {})

    for topic in topics:
        issue_id = topic.get("id")
        if not issue_id:
            continue

        source_names = sorted({
            p.get("source") for p in topic.get("posts", []) if p.get("source")
        })
        item = history["issues"].get(issue_id, {
            "id": issue_id,
            "first_seen": collected_at,
            "last_seen": collected_at,
            "title": topic.get("title", ""),
            "keywords": topic.get("keywords", []),
            "points": [],
            "posts": [],
        })

        item["title"] = topic.get("title", item.get("title", ""))
        item["keywords"] = topic.get("keywords", item.get("keywords", []))
        item["last_seen"] = collected_at
        item["posts"] = topic.get("posts", [])[:12]

        point = {
            "at": collected_at,
            "source_count": int(topic.get("source_count", 0)),
            "post_count": int(topic.get("post_count", 0)),
            "score": round(float(topic.get("score", 0)), 2),
            "sources": source_names,
            "post_urls": [p.get("url") for p in topic.get("posts", []) if p.get("url")],
        }
        points = item.get("points", [])
        if not points or points[-1].get("at") != collected_at:
            points.append(point)
        item["points"] = points[-192:]
        history["issues"][issue_id] = item

    cutoff = dt(collected_at).astimezone(KST) - timedelta(days=62)
    kept = {}
    for issue_id, item in history["issues"].items():
        try:
            last_seen = dt(item.get("last_seen", "")).astimezone(KST)
        except Exception:
            continue
        if last_seen >= cutoff:
            kept[issue_id] = item

    newest = sorted(
        kept.items(),
        key=lambda kv: kv[1].get("last_seen", ""),
        reverse=True,
    )[:500]
    history["issues"] = dict(newest)
    history["updated_at"] = collected_at
    ISSUE_HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return history


def issue_topic_row(topic: dict) -> dict:
    return {
        "id": topic.get("id"),
        "title": topic.get("title", ""),
        "keywords": topic.get("keywords", []),
        "source_count": int(topic.get("source_count", 0)),
        "post_count": int(topic.get("post_count", 0)),
        "score": round(float(topic.get("score", 0)), 2),
        "peak_score": round(float(topic.get("score", 0)), 2),
        "appearances": 1,
        "sources": sorted({
            p.get("source") for p in topic.get("posts", []) if p.get("source")
        }),
        "posts": topic.get("posts", [])[:12],
    }


def attach_issue_rank_changes(rows: list[dict], previous_rows: list[dict]) -> None:
    old_map = {row.get("id"): i + 1 for i, row in enumerate(previous_rows) if row.get("id")}
    for i, row in enumerate(rows, start=1):
        old = old_map.get(row.get("id"))
        row["rank"] = i
        row["change"] = "NEW" if old is None else old - i


def issue_period_rank(history: dict, since: datetime, now: datetime, limit: int = 20) -> list[dict]:
    groups: dict[str, dict] = {}

    for issue_id, item in history.get("issues", {}).items():
        raw_keywords = [
            normalize_keyword_token(token)
            for token in item.get("keywords", [])
            if normalize_keyword_token(token)
        ]
        valid_raw_keywords = [
            token for token in raw_keywords
            if token not in TOPIC_STOPWORDS and not re.fullmatch(r"\d{2}대", token)
        ]
        synthetic_title = re.match(r"^[‘'](.+?)[’'] 관련 글이 여러 커뮤니티에서 화제$", item.get("title", ""))
        if synthetic_title and not valid_raw_keywords:
            continue

        anchor = issue_identity_anchor(item.get("keywords", []), item.get("title", ""))
        if not anchor:
            continue

        valid_points = []
        for point in item.get("points", []):
            try:
                at = dt(point.get("at", "")).astimezone(KST)
            except Exception:
                continue
            if since <= at <= now:
                valid_points.append(point)
        if not valid_points:
            continue

        group = groups.setdefault(anchor, {
            "anchor": anchor,
            "stable_id": issue_id_from_anchor(anchor),
            "items": [],
            "points": {},
        })
        group["items"].append(item)

        # 같은 시각에 구 ID/신 ID가 중복 저장된 경우 점수가 높은 관측치 하나만 유지한다.
        for point in valid_points:
            at_key = point.get("at", "")
            previous_point = group["points"].get(at_key)
            if previous_point is None or float(point.get("score", 0)) > float(previous_point.get("score", 0)):
                group["points"][at_key] = point

    rows = []
    for group in groups.values():
        points = sorted(group["points"].values(), key=lambda p: p.get("at", ""))
        if not points:
            continue

        items = group["items"]
        representative = max(
            items,
            key=lambda item: item.get("last_seen", ""),
        )
        stable_item = next(
            (item for item in items if item.get("id") == group["stable_id"]),
            None,
        )
        display_item = stable_item or representative

        peak_score = max(float(p.get("score", 0)) for p in points)
        max_sources = max(int(p.get("source_count", 0)) for p in points)
        max_posts = max(int(p.get("post_count", 0)) for p in points)
        appearances = len(points)
        source_names = sorted({
            source
            for point in points
            for source in point.get("sources", [])
            if source
        })
        latest = points[-1]

        period_score = (
            peak_score
            + min(18, math.log1p(appearances) * 5)
            + max(0, max_sources - 1) * 4
            + min(8, max_posts)
        )

        first_seen_values = [item.get("first_seen") for item in items if item.get("first_seen")]
        last_seen_values = [item.get("last_seen") for item in items if item.get("last_seen")]

        rows.append({
            "id": group["stable_id"] if stable_item else display_item.get("id"),
            "title": display_item.get("title", ""),
            "keywords": [
                token for token in display_item.get("keywords", [])
                if normalize_keyword_token(token) not in TOPIC_STOPWORDS
                and not re.fullmatch(r"\d{2}대", normalize_keyword_token(token))
            ],
            "source_count": max_sources,
            "post_count": max_posts,
            "score": round(period_score, 2),
            "peak_score": round(peak_score, 2),
            "appearances": appearances,
            "sources": source_names,
            "posts": display_item.get("posts", [])[:12],
            "first_seen": min(first_seen_values) if first_seen_values else None,
            "last_seen": max(last_seen_values) if last_seen_values else None,
            "latest_source_count": int(latest.get("source_count", 0)),
            "latest_post_count": int(latest.get("post_count", 0)),
        })

    rows.sort(
        key=lambda row: (
            row["score"],
            row["source_count"],
            row["post_count"],
            row["appearances"],
        ),
        reverse=True,
    )
    return rows[:limit]

def write_issue_snapshots(now: datetime, collected_at: str, rankings: dict[str, list[dict]]) -> list[dict]:
    ISSUE_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    iso_year, iso_week, _ = now.isocalendar()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=6)

    specs = [
        ("daily", now.strftime("%Y-%m-%d"), now.strftime("%Y년 %m월 %d일")),
        (
            "weekly",
            f"{iso_year}-W{iso_week:02d}",
            f"{week_start.strftime('%Y.%m.%d')} ~ {week_end.strftime('%m.%d')}",
        ),
        ("monthly", now.strftime("%Y-%m"), now.strftime("%Y년 %m월")),
    ]

    metas = []
    for period, key, label in specs:
        period_dir = ISSUE_SNAPSHOT_DIR / period
        period_dir.mkdir(parents=True, exist_ok=True)
        path = period_dir / f"{key}.json"
        payload = {
            "version": 1,
            "period": period,
            "key": key,
            "label": label,
            "collected_at": collected_at,
            "timezone": "Asia/Seoul",
            "issues": rankings.get(period, []),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        metas.append(snapshot_meta(period, key, label, collected_at, path))
    return metas


def update_issue_archive_index(new_metas: list[dict]) -> dict:
    index = load_json(
        ISSUE_ARCHIVE_INDEX_PATH,
        {"version": 1, "periods": {"daily": [], "weekly": [], "monthly": []}},
    )
    index.setdefault("periods", {})
    limits = {"daily": 400, "weekly": 120, "monthly": 60}

    for meta in new_metas:
        period = meta["period"]
        items = index["periods"].setdefault(period, [])
        items = [item for item in items if item.get("key") != meta["key"]]
        items.append(meta)
        items.sort(key=lambda item: item.get("key", ""), reverse=True)
        index["periods"][period] = items[:limits[period]]

    index["updated_at"] = max((m["collected_at"] for m in new_metas), default=None)
    ISSUE_ARCHIVE_INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return index


def build_issue_rankings(
    topics: list[dict],
    issue_history: dict,
    previous: dict,
    now: datetime,
    collected_at: str,
) -> dict:
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    realtime = [issue_topic_row(topic) for topic in topics][:20]
    previous_realtime = previous.get("rankings", {}).get("realtime", []) if isinstance(previous, dict) else []
    attach_issue_rank_changes(realtime, previous_realtime)

    rankings = {
        "realtime": realtime,
        "daily": issue_period_rank(issue_history, day_start, now),
        "weekly": issue_period_rank(issue_history, week_start, now),
        "monthly": issue_period_rank(issue_history, month_start, now),
    }

    for period in ("daily", "weekly", "monthly"):
        previous_rows = previous.get("rankings", {}).get(period, []) if isinstance(previous, dict) else []
        attach_issue_rank_changes(rankings[period], previous_rows)

    payload = {
        "version": 1,
        "collected_at": collected_at,
        "timezone": "Asia/Seoul",
        "period_basis": {
            "realtime": "현재 여러 커뮤니티에서 동시에 포착된 이슈",
            "daily": "오늘 00:00부터 현재까지 누적 이슈",
            "weekly": "이번 주 월요일 00:00부터 현재까지 누적 이슈",
            "monthly": "이번 달 1일 00:00부터 현재까지 누적 이슈",
        },
        "rankings": rankings,
    }
    ISSUE_RANKINGS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metas = write_issue_snapshots(now, collected_at, rankings)
    update_issue_archive_index(metas)
    return payload


def build_briefing(
    now: datetime,
    collected_at: str,
    rankings: dict[str, list[dict]],
    issue_rankings: dict,
    keywords: list[dict],
    community_rankings: dict,
    statuses: list[dict],
) -> dict:
    daily_posts = rankings.get("daily", [])
    rising_posts = rankings.get("rising", [])
    realtime_posts = rankings.get("realtime", [])
    daily_issues = issue_rankings.get("rankings", {}).get("daily", [])
    realtime_issues = issue_rankings.get("rankings", {}).get("realtime", [])

    top_post = daily_posts[0] if daily_posts else (realtime_posts[0] if realtime_posts else None)
    top_issue = daily_issues[0] if daily_issues else (realtime_issues[0] if realtime_issues else None)
    top_keyword = keywords[0] if keywords else None

    source_names = sorted({
        p.get("source") for p in realtime_posts if p.get("source")
    })
    total_comments = sum(int(p.get("comments", 0)) for p in realtime_posts[:100])
    total_views = sum(int(p.get("views", 0)) for p in realtime_posts[:100])

    highlights = []
    if top_issue:
        highlights.append({
            "type": "issue",
            "title": top_issue.get("title", ""),
            "text": f"{int(top_issue.get('source_count', 0))}개 커뮤니티에서 {int(top_issue.get('post_count', 0))}개 관련 인기글이 포착됐습니다.",
            "issue_id": top_issue.get("id"),
        })
    if top_post:
        highlights.append({
            "type": "post",
            "title": top_post.get("title", ""),
            "text": f"{top_post.get('source', '')}에서 현재 상위권에 오른 인기글입니다.",
            "url": top_post.get("url"),
        })
    if top_keyword:
        highlights.append({
            "type": "keyword",
            "title": f"#{top_keyword.get('keyword', '')}",
            "text": f"{int(top_keyword.get('source_count', 0))}개 커뮤니티 · {int(top_keyword.get('post_count', 0))}개 인기글에서 함께 등장했습니다.",
            "keyword": top_keyword.get("keyword"),
        })

    community_leaders = []
    for source_name, data in community_rankings.items():
        rows = data.get("realtime", [])
        if not rows:
            continue
        leader = rows[0]
        community_leaders.append({
            "source": source_name,
            "title": leader.get("title", ""),
            "url": leader.get("url"),
            "score": leader.get("score", 0),
            "views": leader.get("views", 0),
            "comments": leader.get("comments", 0),
        })
    community_leaders.sort(key=lambda row: float(row.get("score", 0)), reverse=True)

    ok_sources = sum(1 for s in statuses if s.get("ok") and int(s.get("count", 0)) > 0)
    cached_sources = sum(1 for s in statuses if s.get("cached") and int(s.get("count", 0)) > 0)

    overview_parts = []
    if top_issue:
        overview_parts.append(f"오늘 가장 두드러진 이슈는 ‘{top_issue.get('title', '')}’입니다.")
    if top_keyword:
        overview_parts.append(f"실시간 키워드 상위: #{top_keyword.get('keyword', '')}.")
    if rising_posts:
        overview_parts.append(f"직전 수집 대비 급상승 글 {min(5, len(rising_posts))}개를 별도로 추적 중입니다.")
    overview = " ".join(overview_parts) if overview_parts else "현재 수집된 데이터를 바탕으로 인터넷 인기 흐름을 집계 중입니다."

    payload = {
        "version": 1,
        "date": now.strftime("%Y-%m-%d"),
        "label": now.strftime("%Y년 %m월 %d일"),
        "collected_at": collected_at,
        "timezone": "Asia/Seoul",
        "overview": overview,
        "stats": {
            "sources": len(source_names),
            "ok_sources": ok_sources,
            "cached_sources": cached_sources,
            "realtime_posts": len(realtime_posts),
            "daily_posts": len(daily_posts),
            "daily_issues": len(daily_issues),
            "keywords": len(keywords),
            "top100_views": total_views,
            "top100_comments": total_comments,
        },
        "highlights": highlights,
        "top_posts": daily_posts[:10],
        "rising": rising_posts[:10],
        "issues": daily_issues[:10],
        "realtime_issues": realtime_issues[:10],
        "keywords": keywords[:15],
        "community_leaders": community_leaders[:10],
    }
    BRIEFING_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_briefing_snapshot(now: datetime, briefing: dict) -> None:
    BRIEFING_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    key = now.strftime("%Y-%m-%d")
    path = BRIEFING_SNAPSHOT_DIR / f"{key}.json"
    path.write_text(json.dumps(briefing, ensure_ascii=False, indent=2), encoding="utf-8")

    index = load_json(BRIEFING_INDEX_PATH, {"version": 1, "items": []})
    items = [item for item in index.get("items", []) if item.get("key") != key]
    items.append({
        "key": key,
        "label": briefing.get("label", key),
        "collected_at": briefing.get("collected_at"),
        "path": str(path.relative_to(DATA_DIR)).replace("\\", "/"),
    })
    items.sort(key=lambda item: item.get("key", ""), reverse=True)
    index["items"] = items[:400]
    index["updated_at"] = briefing.get("collected_at")
    BRIEFING_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def update_metric_history(posts: list[dict], collected_at: str) -> dict:
    history = load_json(METRICS_HISTORY_PATH, {"version": 1, "posts": {}})
    history.setdefault("posts", {})
    history["posts"] = {
        k: v for k, v in history["posts"].items()
        if v.get("source") not in EXCLUDED_SOURCES
    }

    global_rank = {p.get("url"): i + 1 for i, p in enumerate(posts[:100]) if p.get("url")}
    source_rank = {}
    by_source = {}
    for p in posts:
        by_source.setdefault(p.get("source", ""), []).append(p)
    for source_name, source_posts in by_source.items():
        ordered = sorted(
            source_posts,
            key=lambda x: (x.get("score", 0), x.get("views", 0), x.get("comments", 0), x.get("likes", 0)),
            reverse=True,
        )
        for i, p in enumerate(ordered, start=1):
            if p.get("url"):
                source_rank[p["url"]] = i

    for p in posts:
        url = p.get("url")
        if not url:
            continue
        item = history["posts"].get(url, {
            "title": p.get("title", ""),
            "source": p.get("source", ""),
            "category": p.get("category", "이슈"),
            "url": url,
            "last_seen": collected_at,
            "points": [],
        })
        item["title"] = p.get("title", item.get("title", ""))
        item["source"] = p.get("source", item.get("source", ""))
        item["category"] = p.get("category", item.get("category", "이슈"))
        item["last_seen"] = collected_at

        point = {
            "at": collected_at,
            "rank": global_rank.get(url),
            "source_rank": source_rank.get(url),
            "views": int(p.get("views", 0)),
            "likes": int(p.get("likes", 0)),
            "comments": int(p.get("comments", 0)),
            "score": round(float(p.get("score", 0)), 2),
        }

        points = item.get("points", [])
        if not points or points[-1].get("at") != collected_at:
            points.append(point)
        item["points"] = points[-96:]
        history["posts"][url] = item

    # 최근에 본 게시글 위주로 최대 500개만 유지한다.
    items = sorted(
        history["posts"].items(),
        key=lambda kv: kv[1].get("last_seen", ""),
        reverse=True,
    )[:500]
    history["posts"] = dict(items)
    history["updated_at"] = collected_at
    METRICS_HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return history


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(KST)
    collected_at = now.isoformat()
    statuses = []
    all_posts = []

    for source, scraper in SCRAPERS.items():
        started = time.time()
        try:
            items = scraper()
            items = [p for p in items if p.get("title") and p.get("url")][:60]
            score_source(items)
            save_source_cache(source, collected_at, items)
            all_posts.extend(items)
            statuses.append({
                "source": source,
                "ok": True,
                "cached": False,
                "count": len(items),
                "elapsed_ms": int((time.time() - started) * 1000),
            })
        except Exception as exc:
            cached = load_source_cache(source, now)
            if cached:
                items = cached["posts"]
                all_posts.extend(items)
                statuses.append({
                    "source": source,
                    "ok": False,
                    "cached": True,
                    "cached_at": cached.get("collected_at"),
                    "cache_age_minutes": cached.get("age_minutes", 0),
                    "count": len(items),
                    "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                    "elapsed_ms": int((time.time() - started) * 1000),
                })
            else:
                statuses.append({
                    "source": source,
                    "ok": False,
                    "cached": False,
                    "count": 0,
                    "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                    "elapsed_ms": int((time.time() - started) * 1000),
                })
        time.sleep(1.0)

    # URL 기준 중복 제거 후 통합 점수순
    dedup = {}
    for p in all_posts:
        if p["url"] not in dedup or p["score"] > dedup[p["url"]]["score"]:
            dedup[p["url"]] = p
    realtime = sorted(
        dedup.values(),
        key=lambda x: (x["score"], x["views"], x["comments"], x["likes"]),
        reverse=True,
    )[:100]

    archive = {
        k: v for k, v in load_json(ARCHIVE_PATH, {}).items()
        if v.get("source") not in EXCLUDED_SOURCES
    }
    for p in dedup.values():
        key = p["url"]
        old = archive.get(key, {})
        daily_stats = dict(old.get("daily_stats", {})) if isinstance(old.get("daily_stats", {}), dict) else {}
        day_key = now.strftime("%Y-%m-%d")
        day = dict(daily_stats.get(day_key, {}))
        daily_stats[day_key] = {
            "max_score": max(float(day.get("max_score", 0)), float(p["score"])),
            "max_views": max(int(day.get("max_views", 0)), p["views"]),
            "max_likes": max(int(day.get("max_likes", 0)), p["likes"]),
            "max_comments": max(int(day.get("max_comments", 0)), p["comments"]),
            "appearances": int(day.get("appearances", 0)) + 1,
            "last_seen": collected_at,
        }

        stats_cutoff = (now - timedelta(days=62)).date()
        daily_stats = {
            k: v for k, v in daily_stats.items()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", k)
            and datetime.strptime(k, "%Y-%m-%d").date() >= stats_cutoff
        }

        archive[key] = {
            "title": p["title"],
            "source": p["source"],
            "category": p["category"],
            "url": p["url"],
            "first_seen": old.get("first_seen", collected_at),
            "last_seen": collected_at,
            "peak_score": max(float(old.get("peak_score", 0)), float(p["score"])),
            "max_views": max(int(old.get("max_views", 0)), p["views"]),
            "max_likes": max(int(old.get("max_likes", 0)), p["likes"]),
            "max_comments": max(int(old.get("max_comments", 0)), p["comments"]),
            "appearances": int(old.get("appearances", 0)) + 1,
            "daily_stats": daily_stats,
        }

    # 최근 62일 + 최대 6000건만 유지
    cutoff = now - timedelta(days=62)
    archive = {
        k: v for k, v in archive.items()
        if dt(v["last_seen"]).astimezone(KST) >= cutoff
    }
    if len(archive) > 6000:
        newest = sorted(archive.items(), key=lambda kv: kv[1]["last_seen"], reverse=True)[:6000]
        archive = dict(newest)

    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rankings = {
        "realtime": realtime,
        "daily": period_rank(archive, day_start, now),
        "weekly": period_rank(archive, week_start, now),
        "monthly": period_rank(archive, month_start, now),
    }

    previous = load_json(LATEST_PATH, {})
    attach_rank_changes(rankings, previous)
    rising, rising_window_minutes = build_rising(rankings["realtime"], previous, collected_at)
    rankings["rising"] = rising

    community_rankings = {}
    for source_name in SCRAPERS.keys():
        source_posts = sorted(
            [dict(p) for p in dedup.values() if p.get("source") == source_name],
            key=lambda x: (x.get("score", 0), x.get("views", 0), x.get("comments", 0), x.get("likes", 0)),
            reverse=True,
        )[:60]

        previous_source = (
            previous.get("community_rankings", {})
            .get(source_name, {})
            .get("realtime", [])
            if isinstance(previous, dict)
            else []
        )
        if not previous_source and isinstance(previous, dict):
            previous_source = [
                p for p in previous.get("rankings", {}).get("realtime", [])
                if p.get("source") == source_name
            ]

        old_source_rank = {p.get("url"): i + 1 for i, p in enumerate(previous_source) if p.get("url")}
        for i, item in enumerate(source_posts):
            old_rank = old_source_rank.get(item.get("url"))
            item["change"] = "NEW" if old_rank is None else old_rank - (i + 1)

        source_previous_proxy = {
            "collected_at": previous.get("collected_at") if isinstance(previous, dict) else None,
            "rankings": {"realtime": previous_source},
        }
        source_rising, _ = build_rising(
            source_posts,
            source_previous_proxy,
            collected_at,
            limit=30,
        )

        community_rankings[source_name] = {
            "realtime": source_posts,
            "rising": source_rising,
            "keywords": compute_source_keywords(source_posts),
        }

    topics = build_topics(rankings["realtime"])
    keywords = build_keyword_trends(rankings["realtime"], previous)

    payload = {
        "version": 3,
        "collected_at": collected_at,
        "timezone": "Asia/Seoul",
        "period_basis": {
            "rising": f"직전 수집 대비 약 {rising_window_minutes}분 변화",
            "daily": "오늘 00:00부터 현재까지",
            "weekly": "이번 주 월요일 00:00부터 현재까지",
            "monthly": "이번 달 1일 00:00부터 현재까지",
        },
        "sources": statuses,
        "rising_window_minutes": rising_window_minutes,
        "rankings": rankings,
        "community_rankings": community_rankings,
        "topics": topics,
        "keywords": keywords,
    }

    LATEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ARCHIVE_PATH.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    update_metric_history(list(dedup.values()), collected_at)
    issue_history = update_issue_history(topics, collected_at)
    previous_issue_rankings = load_json(ISSUE_RANKINGS_PATH, {})
    issue_rankings = build_issue_rankings(
        topics,
        issue_history,
        previous_issue_rankings,
        now,
        collected_at,
    )
    briefing = build_briefing(
        now,
        collected_at,
        rankings,
        issue_rankings,
        keywords,
        community_rankings,
        statuses,
    )
    write_briefing_snapshot(now, briefing)
    snapshot_metas = write_period_snapshots(now, collected_at, rankings)
    update_archive_index(snapshot_metas)

    ok = sum(1 for s in statuses if s["ok"] and s["count"] > 0)
    print(f"Collected {len(dedup)} posts from {ok}/{len(statuses)} sources")


if __name__ == "__main__":
    main()
