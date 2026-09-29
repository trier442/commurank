(() => {
  if (document.querySelector('script[data-commurank-analytics]')) return;
  const s = document.createElement("script");
  s.src = "/analytics.js";
  s.defer = true;
  s.setAttribute("data-commurank-analytics", "1");
  document.head.appendChild(s);
})();

const sourceName = document.body.dataset.source || "";
const sourceSlug = document.body.dataset.slug || "";
let liveData = null;
let mode = "realtime";
let keyword = "";

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

function sourceData(){
  return liveData?.community_rankings?.[sourceName] || {
    realtime: (liveData?.rankings?.realtime || []).filter(p => p.source === sourceName),
    rising: (liveData?.rankings?.rising || []).filter(p => p.source === sourceName),
    keywords: []
  };
}

function sourceStatus(){
  return (liveData?.sources || []).find(s => s.source === sourceName);
}

function posts(){
  const data = sourceData();
  return mode === "rising" ? (data.rising || []) : (data.realtime || []);
}

function renderKeywords(){
  const list = document.querySelector("#sourceKeywordList");
  const rows = sourceData().keywords || [];
  if (!rows.length) {
    list.innerHTML = '<div class="empty">반복 키워드가 아직 충분하지 않습니다.</div>';
    return;
  }

  list.innerHTML = rows.map((row, i) => `
    <button class="source-keyword ${keyword === row.keyword ? "active" : ""}" data-keyword="${safeText(row.keyword)}" type="button">
      <span>${i + 1}</span>
      <strong>#${safeText(row.keyword)}</strong>
      <small>${Number(row.post_count) || 0}글</small>
    </button>
  `).join("");
}

function render(){
  const all = posts();
  const filtered = all.filter(p => !keyword || String(p.title || "").toLowerCase().includes(keyword.toLowerCase()));
  const status = sourceStatus();

  document.querySelector("#communityName").textContent = sourceName;
  document.querySelector("#communityNameHero").textContent = sourceName;
  document.title = sourceName + " 인기글 랭킹 | 커뮤랭크";

  document.querySelector("#statusCount").textContent = status?.count ?? 0;
  document.querySelector("#rankingCount").textContent = sourceData().realtime?.length ?? 0;
  document.querySelector("#risingCount").textContent = sourceData().rising?.length ?? 0;
  document.querySelector("#collectorState").textContent =
    status?.ok && status?.count > 0 ? "정상 수집" :
    status?.cached && status?.count > 0 ? "캐시 데이터" : "수집 제한";

  const updated = new Date(liveData?.collected_at || Date.now());
  document.querySelector("#updatedAt").textContent = updated.toLocaleString("ko-KR", {
    month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit"
  });

  const heading = keyword
    ? `${mode === "rising" ? "급상승" : "인기"} · #${keyword}`
    : (mode === "rising" ? "급상승 TOP 30" : "인기글 TOP 60");
  document.querySelector("#listHeading").textContent = heading;

  document.querySelector("#activeSourceKeyword").hidden = !keyword;
  document.querySelector("#activeSourceKeywordText").textContent = keyword ? "#" + keyword + " 관련 글" : "";

  const list = document.querySelector("#sourceRankingList");
  if (!filtered.length) {
    list.innerHTML = '<div class="empty">조건에 맞는 게시글이 없습니다.</div>';
  } else {
    list.innerHTML = filtered.map((p, i) => {
      const change = p.change;
      let movement = '<span class="rank-change">―</span>';
      if (change === "NEW") movement = '<span class="rank-change new">NEW</span>';
      else if (Number(change) > 0) movement = '<span class="rank-change up">▲ '+Number(change)+'</span>';
      else if (Number(change) < 0) movement = '<span class="rank-change down">▼ '+Math.abs(Number(change))+'</span>';

      const metrics = mode === "rising"
        ? `<span>+조회 ${fmt(p.delta_views)}</span><span>+추천 ${fmt(p.delta_likes)}</span><span>+댓글 ${fmt(p.delta_comments)}</span><span>순위 +${Number(p.rank_gain) || 0}</span>`
        : `<span>조회 ${fmt(p.views)}</span><span>추천 ${fmt(p.likes)}</span><span>댓글 ${fmt(p.comments)}</span>`;

      return `
        <article class="rank-item">
          <div class="rank-num ${i < 3 ? "top" : ""}">${i + 1}</div>
          <div>
            <a class="post-title" href="${postDetailUrl(p.url)}" target="_blank" rel="noopener noreferrer">${safeText(p.title)}</a>
            <div class="meta">
              <span class="category">${safeText(p.category || "이슈")}</span>
              ${metrics}
            </div>
          </div>
          ${movement}
        </article>
      `;
    }).join("");
  }

  renderKeywords();
}

async function load(){
  try {
    const response = await fetch("../../data/latest.json?ts=" + Date.now(), {cache:"no-store"});
    if (!response.ok) throw new Error("data unavailable");
    liveData = await response.json();
  } catch {
    liveData = null;
  }
  render();
}

document.querySelectorAll("[data-mode]").forEach(button=>{
  button.addEventListener("click", ()=>{
    document.querySelectorAll("[data-mode]").forEach(x=>x.classList.remove("active"));
    button.classList.add("active");
    mode = button.dataset.mode;
    keyword = "";
    render();
  });
});

document.querySelector("#sourceKeywordList").addEventListener("click", e=>{
  const button = e.target.closest("[data-keyword]");
  if (!button) return;
  keyword = button.dataset.keyword || "";
  render();
});

document.querySelector("#clearSourceKeyword").addEventListener("click", ()=>{
  keyword = "";
  render();
});

document.querySelector("#themeToggle").addEventListener("click", ()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme", document.body.classList.contains("dark") ? "dark" : "light");
});

if (localStorage.getItem("commurank-theme") === "dark") document.body.classList.add("dark");

load();
