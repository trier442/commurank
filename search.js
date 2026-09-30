(() => {
  if (document.querySelector('script[data-commurank-analytics]')) return;
  const s = document.createElement("script");
  s.src = "/analytics.js";
  s.defer = true;
  s.setAttribute("data-commurank-analytics", "1");
  document.head.appendChild(s);
})();

let liveData = null;
let searchIndexData = null;
let query = "";
let source = "전체";
let category = "전체";
let sort = "relevance";
let visible = 40;

const fmt = n => new Intl.NumberFormat("ko-KR", {
  notation: Number(n) > 9999 ? "compact" : "standard"
}).format(Number(n) || 0);

function safeText(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;"
  }[ch]));
}

function postDetailUrl(url) {
  return safeText(url || "#");
}

function normalize(value) {
  return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("ko-KR", {
    year:"numeric", month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit"
  });
}

function currentPosts() {
  const map = new Map();
  const community = liveData?.community_rankings || {};
  Object.values(community).forEach(data => {
    (data?.realtime || []).forEach(p => map.set(p.url, p));
  });
  (liveData?.rankings?.realtime || []).forEach(p => map.set(p.url, p));
  return [...map.values()];
}

function buildRecords() {
  const current = new Map(currentPosts().map(p => [p.url, p]));
  const records = new Map();
  const compact = Array.isArray(searchIndexData?.records) ? searchIndexData.records : [];

  compact.forEach(item => {
    if (!item?.u) return;
    records.set(item.u, {
      title:item.t || "",
      source:item.s || "",
      category:item.c || "이슈",
      url:item.u,
      views:Number(item.v || 0),
      likes:Number(item.l || 0),
      comments:Number(item.m || 0),
      score:Number(item.p || 0),
      first_seen:item.f || "",
      last_seen:item.d || "",
      appearances:Number(item.a || 0),
      current:Boolean(item.n)
    });
  });

  current.forEach((p, url) => {
    const old = records.get(url) || {};
    records.set(url, {
      ...old,
      title:p.title || old.title || "",
      source:p.source || old.source || "",
      category:p.category || old.category || "이슈",
      url,
      views:Math.max(Number(old.views || 0), Number(p.views || 0)),
      likes:Math.max(Number(old.likes || 0), Number(p.likes || 0)),
      comments:Math.max(Number(old.comments || 0), Number(p.comments || 0)),
      score:Math.max(Number(old.score || 0), Number(p.score || 0)),
      first_seen:old.first_seen || liveData?.collected_at || "",
      last_seen:liveData?.collected_at || old.last_seen || "",
      appearances:Number(old.appearances || 1),
      current:true
    });
  });

  return [...records.values()];
}

function relevanceScore(record, q) {
  const normalizedQuery = normalize(q);
  if (!normalizedQuery) return 0;
  const title = normalize(record.title);
  const sourceText = normalize(record.source);
  const categoryText = normalize(record.category);
  const tokens = normalizedQuery.split(" ").filter(Boolean);

  let score = 0;
  if (title === normalizedQuery) score += 260;
  if (title.includes(normalizedQuery)) score += 140;
  if (sourceText === normalizedQuery) score += 120;
  if (sourceText.includes(normalizedQuery)) score += 55;
  if (categoryText === normalizedQuery) score += 35;

  tokens.forEach(token => {
    if (title.includes(token)) score += 35;
    if (sourceText.includes(token)) score += 22;
    if (categoryText.includes(token)) score += 10;
  });

  if (record.current) score += 12;
  score += Math.min(18, Number(record.appearances || 0) * 0.8);
  score += Math.min(16, Number(record.score || 0) * 0.12);
  return score;
}

function matchesQuery(record, q) {
  const normalizedQuery = normalize(q);
  if (!normalizedQuery) return true;
  const haystack = normalize([record.title, record.source, record.category].join(" "));
  return normalizedQuery.split(" ").filter(Boolean).every(token => haystack.includes(token));
}

function filteredResults() {
  if (!query) return [];
  let rows = buildRecords()
    .filter(record => matchesQuery(record, query))
    .filter(record => source === "전체" || record.source === source)
    .filter(record => category === "전체" || record.category === category)
    .map(record => ({...record, relevance:relevanceScore(record, query)}));

  if (sort === "recent") rows.sort((a,b) => new Date(b.last_seen) - new Date(a.last_seen));
  else if (sort === "views") rows.sort((a,b) => b.views - a.views);
  else if (sort === "comments") rows.sort((a,b) => b.comments - a.comments);
  else if (sort === "likes") rows.sort((a,b) => b.likes - a.likes);
  else rows.sort((a,b) => b.relevance - a.relevance || new Date(b.last_seen) - new Date(a.last_seen));

  return rows;
}

function renderSources() {
  const names = [...new Set(buildRecords().map(r => r.source).filter(Boolean))]
    .sort((a,b)=>a.localeCompare(b,"ko"));
  const select = document.querySelector("#searchSource");
  select.innerHTML = '<option value="전체">전체 커뮤니티</option>' +
    names.map(name => `<option value="${safeText(name)}">${safeText(name)}</option>`).join("");
  if (!names.includes(source)) source = "전체";
  select.value = source;
  document.querySelector("#sourceTotal").textContent = names.length;
}

function renderRelatedKeywords() {
  const box = document.querySelector("#relatedKeywords");
  const rows = liveData?.keywords || [];
  const q = normalize(query);
  let related = rows.filter(row => {
    const all = [row.keyword, ...(row.aliases || [])].map(normalize);
    return !q || all.some(k => k.includes(q) || q.includes(k));
  });
  if (!related.length) related = rows.slice(0, 8);
  else related = related.slice(0, 8);

  if (!related.length) {
    box.innerHTML = '<div class="empty">현재 키워드 데이터가 없습니다.</div>';
    return;
  }

  box.innerHTML = related.map(row =>
    `<a href="./?q=${encodeURIComponent(row.keyword)}">#${safeText(row.keyword)} <span>${Number(row.post_count)||0}글</span></a>`
  ).join("");
}

function render() {
  const rows = filteredResults();
  const shown = rows.slice(0, visible);
  const results = document.querySelector("#searchResults");

  document.querySelector("#searchInput").value = query;
  document.querySelector("#headerSearchInput").value = query;
  document.querySelector("#searchHeading").textContent = query ? `“${query}” 검색 결과` : "검색어를 입력하세요";
  document.querySelector("#resultCount").textContent = rows.length;

  if (!query) {
    results.innerHTML = '<div class="empty search-empty">검색어를 입력하면 최근 누적 데이터에서 결과를 찾습니다.</div>';
  } else if (!rows.length) {
    results.innerHTML = '<div class="empty search-empty">검색 결과가 없습니다. 다른 키워드나 커뮤니티 이름으로 검색해 보세요.</div>';
  } else {
    results.innerHTML = shown.map((record, i) => `
      <article class="search-result-card">
        <div class="search-result-rank">${i + 1}</div>
        <div class="search-result-body">
          <div class="search-result-badges">
            ${record.current ? '<span class="live-result">현재 인기글</span>' : '<span>아카이브</span>'}
            <span>${safeText(record.source)}</span>
            <span>${safeText(record.category)}</span>
          </div>
          <a class="search-result-title" href="${postDetailUrl(record.url)}" target="_blank" rel="noopener noreferrer">${safeText(record.title)}</a>
          <div class="meta search-result-meta">
            <span>조회 ${fmt(record.views)}</span>
            <span>추천 ${fmt(record.likes)}</span>
            <span>댓글 ${fmt(record.comments)}</span>
            <span>포착 ${formatDate(record.last_seen)}</span>
          </div>
        </div>
      </article>
    `).join("");
  }

  const loadMore = document.querySelector("#loadMore");
  loadMore.hidden = shown.length >= rows.length || !query;

  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (source !== "전체") params.set("source", source);
  if (category !== "전체") params.set("category", category);
  if (sort !== "relevance") params.set("sort", sort);
  history.replaceState(null, "", params.toString() ? "?" + params.toString() : location.pathname);

  renderRelatedKeywords();
}

function submitSearch(value) {
  query = String(value || "").trim();
  visible = 40;
  render();
}

async function load() {
  const params = new URLSearchParams(location.search);
  query = params.get("q") || "";
  source = params.get("source") || "전체";
  category = params.get("category") || "전체";
  sort = params.get("sort") || "relevance";

  try {
    const [liveResponse, searchResponse] = await Promise.all([
      fetch("../data/latest.json?ts=" + Date.now(), {cache:"no-store"}),
      fetch("../data/search-index.json?ts=" + Date.now(), {cache:"no-store"})
    ]);
    if (liveResponse.ok) liveData = await liveResponse.json();
    if (searchResponse.ok) searchIndexData = await searchResponse.json();
  } catch {}

  document.querySelector("#archiveTotal").textContent = Number(searchIndexData?.count || searchIndexData?.records?.length || 0);
  document.querySelector("#currentTotal").textContent = currentPosts().length;
  renderSources();

  document.querySelector("#searchCategory").value = category;
  document.querySelector("#searchSort").value = sort;
  render();
}

document.querySelector("#searchForm").addEventListener("submit", e=>{
  e.preventDefault();
  submitSearch(document.querySelector("#searchInput").value);
});

document.querySelector("#headerSearchForm").addEventListener("submit", e=>{
  e.preventDefault();
  submitSearch(document.querySelector("#headerSearchInput").value);
});

document.querySelector("#searchSource").addEventListener("change", e=>{
  source = e.target.value;
  visible = 40;
  render();
});

document.querySelector("#searchCategory").addEventListener("change", e=>{
  category = e.target.value;
  visible = 40;
  render();
});

document.querySelector("#searchSort").addEventListener("change", e=>{
  sort = e.target.value;
  visible = 40;
  render();
});

document.querySelector("#loadMore").addEventListener("click", ()=>{
  visible += 40;
  render();
});

document.querySelector("#themeToggle").addEventListener("click", ()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme", document.body.classList.contains("dark") ? "dark" : "light");
});

if (localStorage.getItem("commurank-theme") === "dark") document.body.classList.add("dark");

load();
