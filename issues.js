(() => {
  if (document.querySelector('script[data-commurank-analytics]')) return;
  const s = document.createElement("script");
  s.src = "/analytics.js";
  s.defer = true;
  s.setAttribute("data-commurank-analytics", "1");
  document.head.appendChild(s);
})();

let data = null;
let archiveIndex = null;
let archiveData = null;
let period = "realtime";

const labels = {
  realtime:"실시간 이슈",
  daily:"오늘의 이슈",
  weekly:"이번 주 이슈",
  monthly:"이번 달 이슈"
};

const fmt = n => new Intl.NumberFormat("ko-KR", {
  notation: Number(n) > 9999 ? "compact" : "standard"
}).format(Number(n) || 0);

function safeText(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;"
  }[ch]));
}

function issueUrl(id) {
  return "../issue/?id=" + encodeURIComponent(id || "");
}

function rows() {
  if (archiveData?.period === period) return archiveData.issues || [];
  return data?.rankings?.[period] || [];
}

function formatDate(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString("ko-KR",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"});
}

function movement(row) {
  if (row.change === "NEW") return '<span class="rank-change new">NEW</span>';
  if (Number(row.change) > 0) return '<span class="rank-change up">▲ '+Number(row.change)+'</span>';
  if (Number(row.change) < 0) return '<span class="rank-change down">▼ '+Math.abs(Number(row.change))+'</span>';
  return '<span class="rank-change">―</span>';
}

function renderArchiveControls() {
  const controls = document.querySelector("#issueArchiveControls");
  const select = document.querySelector("#issueArchiveSelect");

  if (period === "realtime") {
    controls.hidden = true;
    archiveData = null;
    return;
  }

  controls.hidden = false;
  const items = archiveIndex?.periods?.[period] || [];
  const selected = archiveData?.period === period ? archiveData.key : "";
  select.innerHTML = '<option value="">현재 순위</option>' +
    items.map(item => `<option value="${safeText(item.key)}" ${item.key===selected?"selected":""}>${safeText(item.label)}</option>`).join("");
}

function renderTopCards(all) {
  const box = document.querySelector("#issueTopCards");
  const top = all.slice(0,3);
  if (!top.length) {
    box.innerHTML = "";
    return;
  }
  box.innerHTML = top.map((row,i)=>`
    <a class="issue-rank-feature rank-${i+1}" href="${issueUrl(row.id)}">
      <div class="issue-rank-number">${i+1}</div>
      <div class="issue-rank-feature-body">
        <span>${Number(row.source_count)||0}개 커뮤니티 · 관련글 ${Number(row.post_count)||0}건</span>
        <strong>${safeText(row.title)}</strong>
        <div class="issue-card-keywords">
          ${(row.keywords||[]).slice(0,4).map(k=>`<em>#${safeText(k)}</em>`).join("")}
        </div>
      </div>
      <div class="issue-score-badge">${Math.round(Number(row.score)||0)}</div>
    </a>
  `).join("");
}

function renderKeywords(all) {
  const counts = new Map();
  all.slice(0,20).forEach(row => {
    (row.keywords||[]).forEach(k => counts.set(k,(counts.get(k)||0)+1));
  });
  const ranked = [...counts.entries()]
    .sort((a,b)=>b[1]-a[1] || b[0].length-a[0].length)
    .slice(0,12);

  const box = document.querySelector("#issueRankKeywords");
  box.innerHTML = ranked.length
    ? ranked.map(([k,n])=>`<a href="../search/?q=${encodeURIComponent(k)}">#${safeText(k)} <span>${n}이슈</span></a>`).join("")
    : '<div class="empty">키워드 데이터가 없습니다.</div>';
}

function render() {
  const all = rows();
  document.querySelector("#issuePeriodLabel").textContent =
    archiveData?.period === period ? archiveData.label : labels[period];

  const activeAt = archiveData?.collected_at || data?.collected_at;
  document.querySelector("#issueUpdatedAt").textContent = formatDate(activeAt);

  renderTopCards(all);

  const rest = all.slice(3);
  const list = document.querySelector("#issueRankingList");
  list.innerHTML = rest.length ? rest.map((row,i)=>`
    <article class="issue-rank-row">
      <div class="rank-num">${i+4}</div>
      <div class="issue-rank-row-body">
        <a class="post-title" href="${issueUrl(row.id)}">${safeText(row.title)}</a>
        <div class="meta">
          <span class="category">${Number(row.source_count)||0}개 커뮤니티</span>
          <span>관련글 ${Number(row.post_count)||0}건</span>
          <span>이슈점수 ${Math.round(Number(row.score)||0)}</span>
          ${Number(row.appearances)>1 ? `<span>포착 ${Number(row.appearances)}회</span>` : ""}
        </div>
        <div class="issue-row-keywords">
          ${(row.keywords||[]).slice(0,5).map(k=>`<span>#${safeText(k)}</span>`).join("")}
        </div>
      </div>
      ${movement(row)}
    </article>
  `).join("") : (all.length ? "" : '<div class="empty">이 기간에 랭크된 이슈가 없습니다.</div>');

  const sources = new Set();
  let posts = 0;
  all.forEach(row=>{
    (row.sources||[]).forEach(s=>sources.add(s));
    posts += Number(row.post_count)||0;
  });
  document.querySelector("#issueCount").textContent = all.length;
  document.querySelector("#issueSourceCount").textContent = sources.size;
  document.querySelector("#issuePostCount").textContent = posts;
  renderKeywords(all);
  renderArchiveControls();

  const params = new URLSearchParams();
  if (period !== "realtime") params.set("period",period);
  if (archiveData?.period === period && archiveData.key) params.set("archive",archiveData.key);
  history.replaceState(null,"",params.toString() ? "?"+params.toString() : location.pathname);
}

async function loadArchive(key) {
  if (!key) {
    archiveData = null;
    render();
    return;
  }
  const item = (archiveIndex?.periods?.[period] || []).find(x=>x.key===key);
  if (!item) {
    archiveData = null;
    render();
    return;
  }
  try {
    const response = await fetch("../data/" + item.path + "?ts=" + Date.now(),{cache:"no-store"});
    if (response.ok) archiveData = await response.json();
  } catch {
    archiveData = null;
  }
  render();
}

async function load() {
  try {
    const [rankingResponse,indexResponse] = await Promise.all([
      fetch("../data/issue-rankings.json?ts="+Date.now(),{cache:"no-store"}),
      fetch("../data/issue-archive-index.json?ts="+Date.now(),{cache:"no-store"})
    ]);
    if (rankingResponse.ok) data = await rankingResponse.json();
    if (indexResponse.ok) archiveIndex = await indexResponse.json();
  } catch {}

  const params = new URLSearchParams(location.search);
  const requestedPeriod = params.get("period");
  const requestedArchive = params.get("archive");

  if (labels[requestedPeriod]) {
    period = requestedPeriod;
    document.querySelectorAll("[data-issue-period]").forEach(btn=>
      btn.classList.toggle("active",btn.dataset.issuePeriod===period)
    );
  }
  if (requestedArchive && period !== "realtime") {
    await loadArchive(requestedArchive);
    return;
  }
  render();
}

document.querySelectorAll("[data-issue-period]").forEach(button=>{
  button.addEventListener("click",()=>{
    period=button.dataset.issuePeriod;
    archiveData=null;
    document.querySelectorAll("[data-issue-period]").forEach(x=>x.classList.toggle("active",x===button));
    render();
  });
});

document.querySelector("#issueArchiveSelect").addEventListener("change",e=>loadArchive(e.target.value));
document.querySelector("#issueLatestButton").addEventListener("click",()=>{
  archiveData=null;
  document.querySelector("#issueArchiveSelect").value="";
  render();
});

document.querySelector("#themeToggle").addEventListener("click",()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme",document.body.classList.contains("dark")?"dark":"light");
});
if(localStorage.getItem("commurank-theme")==="dark") document.body.classList.add("dark");

load();
