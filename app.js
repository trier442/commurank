(() => {
  if (document.querySelector('script[data-commurank-analytics], script[src$="/analytics.js"]')) return;
  const s = document.createElement("script");
  s.src = "/analytics.js";
  s.defer = true;
  s.setAttribute("data-commurank-analytics", "1");
  document.head.appendChild(s);
})();

const fallbackPosts = [
  {title:"랭킹 데이터를 불러오지 못했습니다.", source:"커뮤랭크", category:"이슈", views:0, likes:0, comments:0, change:"NEW", url:"#"},
  {title:"잠시 후 새로고침하면 최신 인기글을 다시 불러옵니다.", source:"커뮤랭크", category:"이슈", views:0, likes:0, comments:0, change:0, url:"#"}
];

const periodInfo = {
  rising: {label:"급상승"},
  realtime: {label:"실시간"},
  daily: {label:"일간"},
  weekly: {label:"주간"},
  monthly: {label:"월간"}
};

let period = "realtime";
let category = "전체";
let source = "전체";
let keyword = "";
let liveData = null;
let archiveIndex = null;
let archiveData = null;

const communitySlug = {
  "디시인사이드":"dcinside",
  "에펨코리아":"fmkorea",
  "더쿠":"theqoo",
  "루리웹":"ruliweb",
  "클리앙":"clien",
  "인벤":"inven",
  "뽐뿌":"ppomppu"
};

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

function sourcePageUrl(name) {
  const slug = communitySlug[name];
  return slug ? `./community/${slug}/` : "";
}

function currentPosts(){
  if (archiveData?.period === period && Array.isArray(archiveData.posts)) {
    return archiveData.posts;
  }
  if (!liveData?.rankings?.[period]) return fallbackPosts;
  return liveData.rankings[period];
}

function currentTopics(){
  if (archiveData?.period === period) return archiveData.topics || [];
  return liveData?.topics || [];
}

function currentLabel(){
  if (archiveData?.period === period) return archiveData.label || periodInfo[period].label;
  return periodInfo[period].label;
}

function renderSourceOptions(){
  const select = document.querySelector("#sourceFilter");
  const names = new Set();

  if (liveData?.sources) {
    liveData.sources
      .filter(s => s.count > 0)
      .forEach(s => names.add(s.source));
  }
  currentPosts().forEach(p => {
    if (p.source && p.source !== "커뮤랭크") names.add(p.source);
  });

  const ordered = [...names].sort((a,b)=>a.localeCompare(b,"ko"));
  select.innerHTML = '<option value="전체">전체 커뮤니티</option>' +
    ordered.map(name => `<option value="${safeText(name)}">${safeText(name)}</option>`).join("");

  if (source !== "전체" && !ordered.includes(source)) source = "전체";
  select.value = source;
}

function renderKeywords(){
  const rows = liveData?.keywords || [];
  const container = document.querySelector("#keywordList");
  const badge = document.querySelector("#keywordCount");
  badge.textContent = rows.length ? "TOP " + rows.length : "0건";

  if (!rows.length) {
    container.innerHTML = '<div class="empty">키워드 데이터가 아직 없습니다.</div>';
    return;
  }

  container.innerHTML = rows.map(row => {
    const ch = row.change;
    let change = '<span class="kw-change">―</span>';
    if (ch === "NEW") change = '<span class="kw-change new">NEW</span>';
    else if (Number(ch) > 0) change = '<span class="kw-change up">▲ ' + Number(ch) + '</span>';
    else if (Number(ch) < 0) change = '<span class="kw-change down">▼ ' + Math.abs(Number(ch)) + '</span>';

    const active = keyword === row.keyword ? " active" : "";
    return `
      <button class="keyword-row${active}" type="button" data-keyword="${safeText(row.keyword)}">
        <span class="keyword-rank">${Number(row.rank) || "-"}</span>
        <span class="keyword-name">#${safeText(row.keyword)}</span>
        <span class="keyword-meta">${Number(row.source_count) || 0}곳 · ${Number(row.post_count) || 0}글</span>
        ${change}
      </button>`;
  }).join("");
}

function renderTopics(){
  const topics = currentTopics();
  const container = document.querySelector("#topicList");
  const badge = document.querySelector("#topicCount");
  badge.textContent = topics.length ? topics.length + "건" : "0건";

  if (!topics.length) {
    container.innerHTML = '<div class="empty">여러 커뮤니티에서 동시에 잡힌 이슈가 없습니다.</div>';
    return;
  }

  container.innerHTML = topics.slice(0, 6).map(topic => {
    const links = (topic.posts || []).slice(0, 4).map(p =>
      `<a href="${postDetailUrl(p.url)}">${safeText(p.source)} ${Number(p.rank) || "-"}위</a>`
    ).join("");

    const keywords = (topic.keywords || []).length
      ? `<p class="topic-keywords">${topic.keywords.map(k => "#" + safeText(k)).join(" ")}</p>`
      : "";

    return `
      <article class="topic-card">
        <span class="topic-count">${Number(topic.source_count) || 0}개 커뮤니티 · 관련글 ${Number(topic.post_count) || 0}건</span>
        <h4><a class="topic-title-link" href="./issue/?id=${encodeURIComponent(topic.id || "")}">${safeText(topic.title)}</a></h4>
        ${keywords}
        <div class="topic-tags">${links}</div>
      </article>`;
  }).join("");
}

function renderArchiveControls(){
  const controls = document.querySelector("#archiveControls");
  const select = document.querySelector("#archiveSelect");

  if (period === "realtime" || period === "rising") {
    controls.hidden = true;
    archiveData = null;
    return;
  }

  controls.hidden = false;
  const items = archiveIndex?.periods?.[period] || [];
  const selectedKey = archiveData?.period === period ? archiveData.key : "";

  select.innerHTML = '<option value="">현재 순위</option>' +
    items.map(item =>
      `<option value="${safeText(item.key)}" ${item.key === selectedKey ? "selected" : ""}>${safeText(item.label)}</option>`
    ).join("");
}

function updateUrl(){
  const params = new URLSearchParams();
  if (period !== "realtime") params.set("period", period);
  if (archiveData?.period === period && archiveData.key) params.set("archive", archiveData.key);
  if (keyword) params.set("keyword", keyword);

  const next = params.toString() ? "?" + params.toString() : location.pathname;
  history.replaceState(null, "", next);
}

function renderPortalToday(){
  const container = document.querySelector("#portalToday");
  if (!container) return;
  const items = liveData?.rankings?.daily || [];

  if (!items.length) {
    container.innerHTML = '<div class="empty">오늘의 랭킹 데이터가 없습니다.</div>';
    return;
  }

  container.innerHTML = items.slice(0,3).map((p,i)=>`
    <a class="portal-feature-item portal-feature-card" href="${safeText(p.url || "#")}" target="_blank" rel="noopener noreferrer" aria-label="${safeText(p.title)} 원문 열기">
      <span class="portal-feature-rank">${i+1}</span>
      <div>
        <span class="portal-source">${safeText(p.source)}</span>
        <span class="portal-feature-title">${safeText(p.title)}</span>
        <div class="portal-metrics">
          <span>조회 ${fmt(p.views)}</span>
          <span>댓글 ${fmt(p.comments)}</span>
        </div>
      </div>
    </a>
  `).join("");
}

function renderPortalRising(){
  const container = document.querySelector("#portalRising");
  if (!container) return;
  const items = liveData?.rankings?.rising || [];
  const windowMinutes = Number(liveData?.rising_window_minutes || 30);

  if (!items.length) {
    container.innerHTML = '<div class="empty">급상승 데이터가 없습니다.</div>';
    return;
  }

  container.innerHTML = items.slice(0,5).map((p,i)=>`
    <article class="portal-mini-item">
      <span class="portal-mini-rank">${i+1}</span>
      <div class="portal-mini-body">
        <a href="${postDetailUrl(p.url)}">${safeText(p.title)}</a>
        <span>${safeText(p.source)} · ${windowMinutes}분 · +댓글 ${fmt(p.delta_comments)} · +조회 ${fmt(p.delta_views)}</span>
      </div>
      <strong>${Math.round(Number(p.rising_score)||0)}</strong>
    </article>
  `).join("");
}

function renderCommunityChampions(){
  const container = document.querySelector("#communityList");
  if (!container) return;

  const rows = Object.entries(liveData?.community_rankings || {})
    .map(([name,data]) => ({
      name,
      top:data?.realtime?.[0],
      count:data?.realtime?.length || 0,
      slug:communitySlug[name]
    }))
    .filter(row => row.top && row.slug)
    .sort((a,b) => Number(b.top?.score||0) - Number(a.top?.score||0));

  container.innerHTML = rows.length
    ? rows.map((row,i)=>`
      <li class="community-row portal-community-row">
        <span class="community-rank">${i+1}</span>
        <div class="community-champion">
          <a class="community-name community-link" href="./community/${row.slug}/">${safeText(row.name)}</a>
          <a class="community-top-title" href="${postDetailUrl(row.top.url)}">${safeText(row.top.title)}</a>
        </div>
        <span class="community-score">#1 · ${row.count}건</span>
      </li>`).join("")
    : '<li class="empty">수집 대기 중</li>';
}

function renderPortal(){
  renderPortalToday();
  renderPortalRising();
  renderCommunityChampions();
}

function renderSourceShortcutHealth(){
  const statusMap = new Map((liveData?.sources || []).map(row => [row.source, row]));
  document.querySelectorAll("[data-source-shortcut]").forEach(link => {
    const name = link.dataset.sourceShortcut;
    const status = statusMap.get(name);
    link.classList.remove("source-unavailable", "source-cached");
    link.removeAttribute("title");
    if (!status) return;
    if (status.cached && status.count > 0) {
      link.classList.add("source-cached");
      link.title = `${name} · 최근 정상 수집 캐시 사용 중`;
    } else if (!status.ok || status.count <= 0) {
      link.classList.add("source-unavailable");
      link.title = `${name} · 현재 수집 점검 중`;
    }
  });
}

function render(){
  const posts = currentPosts();
  const filtered = posts
    .filter(p => category === "전체" || p.category === category)
    .filter(p => source === "전체" || p.source === source)
    .filter(p => !keyword || String(p.title || "").toLowerCase().includes(keyword.toLowerCase()));

  const baseLabel = period === "rising"
    ? `급상승 · ${Number(liveData?.rising_window_minutes || 30)}분 변화`
    : currentLabel();
  document.querySelector("#periodLabel").textContent = keyword ? baseLabel + " · #" + keyword : baseLabel;
  document.querySelector("#heroCount").textContent = liveData?.rankings?.realtime?.length ?? 0;

  const list = document.querySelector("#rankingList");
  if (!filtered.length) {
    list.innerHTML = '<div class="empty">조건에 맞는 인기글이 없습니다.</div>';
  } else {
    list.innerHTML = filtered.map((p,i) => {
      const ch = p.change;
      let changeHtml = '<span class="rank-change">―</span>';
      if (ch === "NEW") changeHtml = '<span class="rank-change new">NEW</span>';
      else if (Number(ch) > 0) changeHtml = '<span class="rank-change up">▲ '+Number(ch)+'</span>';
      else if (Number(ch) < 0) changeHtml = '<span class="rank-change down">▼ '+Math.abs(Number(ch))+'</span>';

      const href = p.url && p.url !== "#" ? safeText(p.url) : "#";
      const analysisHref = p.url && p.url !== "#" ? "./post/?url=" + encodeURIComponent(p.url) : "#";
      const sourceHref = sourcePageUrl(p.source);
      return `
        <article class="rank-item">
          <div class="rank-num ${i < 3 ? "top" : ""}">${i+1}</div>
          <div>
            <a class="post-title" href="${href}" target="_blank" rel="noopener noreferrer">${safeText(p.title)}</a>
            <div class="meta">
              ${sourceHref
                ? `<a class="source source-link" href="${sourceHref}">${safeText(p.source)}</a>`
                : `<span class="source">${safeText(p.source)}</span>`}
              <span class="category">${safeText(p.category || "이슈")}</span>
              ${period === "rising"
                ? `<span class="delta hot-delta">+${Number(p.window_minutes || liveData?.rising_window_minutes || 30)}분</span>
                   <span>+조회 ${fmt(p.delta_views)}</span>
                   <span>+추천 ${fmt(p.delta_likes)}</span>
                   <span>+댓글 ${fmt(p.delta_comments)}</span>
                   <span>순위 +${Number(p.rank_gain) || 0}</span>`
                : `<span>조회 ${fmt(p.views)}</span>
                   <span>추천 ${fmt(p.likes)}</span>
                   <span>댓글 ${fmt(p.comments)}</span>`}
              ${analysisHref !== "#" ? `<a class="analysis-link" href="${analysisHref}">분석 보기</a>` : ""}
            </div>
          </div>
          ${changeHtml}
        </article>`;
    }).join("");
  }

  renderPortal();

  const activeDate = archiveData?.period === period ? new Date(archiveData.collected_at) : new Date(liveData?.collected_at || Date.now());
  const ageMinutes = Math.max(0, Math.round((Date.now() - activeDate.getTime()) / 60000));
  const updatedNode = document.querySelector("#updatedAt");
  const exactTime = activeDate.toLocaleString("ko-KR", {
    month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit"
  });
  updatedNode.textContent = ageMinutes < 1 ? exactTime + " · 방금 전" : exactTime + ` · ${ageMinutes}분 전`;
  updatedNode.classList.toggle("stale", ageMinutes > 30 && !archiveData);

  const keywordBar = document.querySelector("#activeKeywordBar");
  keywordBar.hidden = !keyword;
  document.querySelector("#activeKeywordText").textContent = keyword ? "#" + keyword + " 관련 인기글" : "";

  renderSourceOptions();
  renderKeywords();
  renderTopics();
  renderArchiveControls();
  renderSourceShortcutHealth();
  updateUrl();
}

async function loadArchiveIndex(){
  try {
    const response = await fetch("./data/archive-index.json?ts=" + Date.now(), {cache:"no-store"});
    if (!response.ok) throw new Error("archive index unavailable");
    archiveIndex = await response.json();
  } catch {
    archiveIndex = {periods:{daily:[],weekly:[],monthly:[]}};
  }
}

async function loadArchive(periodName, key){
  if (!periodName || !key || periodName === "realtime") {
    archiveData = null;
    render();
    return;
  }

  const item = (archiveIndex?.periods?.[periodName] || []).find(x => x.key === key);
  if (!item) {
    archiveData = null;
    render();
    return;
  }

  try {
    const response = await fetch("./data/" + item.path + "?ts=" + Date.now(), {cache:"no-store"});
    if (!response.ok) throw new Error("archive data unavailable");
    archiveData = await response.json();
    source = "전체";
    category = "전체";
    document.querySelectorAll(".chip").forEach(x=>x.classList.toggle("active", x.dataset.category === "전체"));
  } catch {
    archiveData = null;
  }
  render();
}

async function loadLiveData(){
  try {
    const [response] = await Promise.all([
      fetch("./data/latest.json?ts=" + Date.now(), {cache:"no-store"}),
      loadArchiveIndex()
    ]);

    if (!response.ok) throw new Error("ranking data unavailable");
    liveData = await response.json();

    const sourceRows = liveData.sources || [];
    const availableSources = sourceRows.filter(s => s.count > 0).length;
    const cachedSources = sourceRows.filter(s => s.cached && s.count > 0).length;
    const failedSources = sourceRows.filter(s => !s.ok && !s.cached);
    const totalSources = sourceRows.length;
    const sourceStatus = document.querySelector("#sourceStatus");
    sourceStatus.textContent = totalSources
      ? `${availableSources}개 수집${cachedSources ? " · " + cachedSources + "개 캐시" : ""}${failedSources.length ? " · " + failedSources.length + "개 점검 중" : ""}`
      : "수집 준비";
    sourceStatus.title = failedSources.length
      ? failedSources.map(s => s.source + " 수집 점검 중").join(" · ")
      : "현재 연결된 커뮤니티 수집 정상";

    const params = new URLSearchParams(location.search);
    const requestedPeriod = params.get("period");
    const requestedArchive = params.get("archive");
    const requestedKeyword = params.get("keyword");
    if (requestedKeyword) keyword = requestedKeyword;

    if (requestedPeriod && periodInfo[requestedPeriod]) {
      period = requestedPeriod;
      document.querySelectorAll(".nav-item").forEach(x =>
        x.classList.toggle("active", x.dataset.period === period)
      );
    }

    if (requestedArchive && period !== "realtime") {
      await loadArchive(period, requestedArchive);
      return;
    }
  } catch (err) {
    liveData = null;
    document.querySelector("#updatedAt").textContent = "자동 수집 대기";
    document.querySelector("#sourceStatus").textContent = "수집 대기";
  }
  render();
}

document.querySelectorAll(".nav-item").forEach(btn=>{
  btn.addEventListener("click", async ()=>{
    document.querySelectorAll(".nav-item").forEach(x=>x.classList.remove("active"));
    btn.classList.add("active");
    period = btn.dataset.period;
    archiveData = null;
    source = "전체";
    await Promise.resolve();
    render();
  });
});

document.querySelectorAll(".chip").forEach(btn=>{
  btn.addEventListener("click", ()=>{
    document.querySelectorAll(".chip").forEach(x=>x.classList.remove("active"));
    btn.classList.add("active");
    category = btn.dataset.category;
    render();
  });
});

document.querySelector("#keywordList").addEventListener("click", e=>{
  const button = e.target.closest("[data-keyword]");
  if (!button) return;
  keyword = button.dataset.keyword || "";
  render();
  document.querySelector("#rankingList")?.scrollIntoView({behavior:"smooth", block:"start"});
});

document.querySelector("#clearKeyword").addEventListener("click", ()=>{
  keyword = "";
  render();
});

document.querySelectorAll("[data-jump-period]").forEach(button=>{
  button.addEventListener("click", ()=>{
    const target = button.dataset.jumpPeriod;
    if (!periodInfo[target]) return;
    period = target;
    archiveData = null;
    keyword = "";
    source = "전체";
    category = "전체";
    document.querySelectorAll(".nav-item").forEach(x=>x.classList.toggle("active", x.dataset.period === period));
    document.querySelectorAll(".chip").forEach(x=>x.classList.toggle("active", x.dataset.category === "전체"));
    render();
    document.querySelector(".controls")?.scrollIntoView({behavior:"smooth", block:"start"});
  });
});

document.querySelector("#sourceFilter").addEventListener("change", e=>{
  source = e.target.value;
  render();
});

document.querySelector("#archiveSelect").addEventListener("change", async e=>{
  const key = e.target.value;
  if (!key) {
    archiveData = null;
    render();
    return;
  }
  await loadArchive(period, key);
});

document.querySelector("#latestButton").addEventListener("click", ()=>{
  archiveData = null;
  document.querySelector("#archiveSelect").value = "";
  render();
});

document.querySelector("#themeToggle").addEventListener("click", ()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme", document.body.classList.contains("dark") ? "dark" : "light");
});

if (localStorage.getItem("commurank-theme") === "dark") document.body.classList.add("dark");

loadLiveData();
