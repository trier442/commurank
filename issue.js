(() => {
  if (document.querySelector('script[data-commurank-analytics], script[src$="/analytics.js"]')) return;
  const s = document.createElement("script");
  s.src = "/analytics.js";
  s.defer = true;
  s.setAttribute("data-commurank-analytics", "1");
  document.head.appendChild(s);
})();

const issueId = new URLSearchParams(location.search).get("id") || "";
let liveData = null;
let archiveData = {};
let historyData = {};
let issue = null;
let liveIssue = null;
let issueMetric = "post_count";

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

function formatDate(value, short=false) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString("ko-KR", short
    ? {month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}
    : {year:"numeric",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}
  );
}

function resolveIssue() {
  liveIssue = (liveData?.topics || []).find(t => t.id === issueId) || null;
  const archived = historyData?.issues?.[issueId] || null;
  issue = archived || liveIssue;
  if (liveIssue && archived) {
    issue = {...archived, ...liveIssue, points:archived.points || [], posts:liveIssue.posts || archived.posts || []};
  }
}

function getPost(url) {
  const current = (liveData?.rankings?.realtime || []).find(p=>p.url===url);
  if (current) return current;
  const a = archiveData?.[url];
  if (!a) return null;
  return {
    title:a.title, source:a.source, category:a.category, url:a.url,
    views:a.max_views||0, likes:a.max_likes||0, comments:a.max_comments||0,
    score:a.peak_score||0
  };
}

function issuePosts() {
  const rows = (liveIssue?.posts || issue?.posts || [])
    .map(p => ({...p, detail:getPost(p.url)}));
  return rows;
}

function chartSvg(points, accessor, label) {
  if (!points.length) return '<div class="empty">이슈 변화 기록이 아직 충분하지 않습니다.</div>';
  const values = points.map(accessor).map(Number).filter(Number.isFinite);
  if (!values.length) return '<div class="empty">표시할 수치가 없습니다.</div>';

  const width=760,height=230,padX=44,padY=26;
  const min=Math.min(...values),max=Math.max(...values),range=Math.max(1,max-min);
  const n=Math.max(1,points.length-1);
  const coords=points.map((p,i)=>{
    const v=Number(accessor(p)||0);
    const x=padX+(width-padX*2)*(i/n);
    const y=padY+(height-padY*2)*(1-(v-min)/range);
    return {x,y,v,p};
  });
  const poly=coords.map(c=>c.x.toFixed(1)+","+c.y.toFixed(1)).join(" ");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${safeText(label)} 변화">
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height-padY}" class="chart-axis"/>
      <line x1="${padX}" y1="${height-padY}" x2="${width-padX}" y2="${height-padY}" class="chart-axis"/>
      <line x1="${padX}" y1="${padY}" x2="${width-padX}" y2="${padY}" class="chart-grid"/>
      <line x1="${padX}" y1="${height/2}" x2="${width-padX}" y2="${height/2}" class="chart-grid"/>
      <polyline points="${poly}" fill="none" class="chart-line"/>
      ${coords.map(c=>`<circle cx="${c.x}" cy="${c.y}" r="3.5" class="chart-dot"><title>${safeText(formatDate(c.p.at))}: ${fmt(c.v)}</title></circle>`).join("")}
      <text x="8" y="${padY+4}" class="chart-label">${fmt(max)}</text>
      <text x="8" y="${height-padY+4}" class="chart-label">${fmt(min)}</text>
      <text x="${padX}" y="${height-5}" class="chart-label">${safeText(formatDate(points[0].at,true))}</text>
      <text x="${width-padX}" y="${height-5}" text-anchor="end" class="chart-label">${safeText(formatDate(points[points.length-1].at,true))}</text>
    </svg>`;
}

function renderChart() {
  const points = issue?.points || [];
  const labels = {post_count:"관련글 수",source_count:"커뮤니티 수",score:"이슈 점수"};
  document.querySelector("#issueChart").innerHTML = chartSvg(points,p=>p[issueMetric],labels[issueMetric]);
  if (points.length) {
    document.querySelector("#issueHistoryRange").textContent =
      `${formatDate(points[0].at,true)} ~ ${formatDate(points[points.length-1].at,true)} · ${points.length}회`;
  }
}

function renderSources(containerId, sources, first=false) {
  const box=document.querySelector(containerId);
  if (!sources?.length) {
    box.innerHTML='<div class="empty">데이터가 없습니다.</div>';
    return;
  }
  box.innerHTML=sources.map((source,i)=>{
    const slug=communitySlug[source];
    const tag=first && i===0 ? "최초 기록" : "포착";
    return `
      <div class="issue-source-row">
        <span>${i+1}</span>
        ${slug ? `<a href="../community/${slug}/">${safeText(source)}</a>` : `<strong>${safeText(source)}</strong>`}
        <small>${tag}</small>
      </div>`;
  }).join("");
}

function renderReactions() {
  const rows=issuePosts().map(row=>{
    const p=row.detail||{};
    return {
      source:row.source,
      rank:row.rank,
      views:Number(p.views||0),
      likes:Number(p.likes||0),
      comments:Number(p.comments||0),
      url:row.url
    };
  }).sort((a,b)=>(b.comments+b.likes)-(a.comments+a.likes));

  const box=document.querySelector("#reactionTable");
  if (!rows.length) {
    box.innerHTML='<div class="empty">반응 지표가 없습니다.</div>';
    return;
  }
  box.innerHTML=`
    <div class="reaction-head"><span>커뮤니티</span><span>순위</span><span>조회</span><span>추천</span><span>댓글</span></div>
    ${rows.map(r=>`
      <a class="reaction-row" href="${safeText(r.url || "#")}" target="_blank" rel="noopener noreferrer">
        <strong>${safeText(r.source)}</strong>
        <span>#${Number(r.rank)||"-"}</span>
        <span>${fmt(r.views)}</span>
        <span>${fmt(r.likes)}</span>
        <span>${fmt(r.comments)}</span>
      </a>`).join("")}`;
}

function render() {
  if (!issue) {
    document.querySelector("#issueTitle").textContent="이슈 데이터를 찾을 수 없습니다.";
    document.querySelector("#issueSummary").textContent="메인의 동시 화제 카드에서 다시 선택해 주세요.";
    return;
  }

  const points=issue.points||[];
  const latest=points[points.length-1]||{};
  const previous=points[points.length-2]||{};
  const sourceCount=Number(liveIssue?.source_count ?? latest.source_count ?? 0);
  const postCount=Number(liveIssue?.post_count ?? latest.post_count ?? 0);
  const score=Number(liveIssue?.score ?? latest.score ?? 0);
  const firstSources=points[0]?.sources||[];
  const currentSources=latest.sources || [...new Set(issuePosts().map(p=>p.source).filter(Boolean))];

  document.title=issue.title+" | 커뮤랭크 이슈";
  document.querySelector("#issueTitle").textContent=issue.title;
  document.querySelector("#issueMeta").innerHTML=
    `<span>${sourceCount}개 커뮤니티</span><span>관련글 ${postCount}건</span><span>크로스 커뮤니티 이슈</span>`;
  document.querySelector("#issueSummary").textContent=
    sourceCount>1
      ? `${currentSources.join(" · ")} 등 여러 커뮤니티에서 함께 포착된 주제입니다.`
      : "최근 수집 기록에 남아 있는 이슈입니다.";

  const kws=issue.keywords||[];
  document.querySelector("#issueKeywords").innerHTML=kws.length
    ? kws.map(k=>`<a href="../search/?q=${encodeURIComponent(k)}">#${safeText(k)}</a>`).join("")
    : "";

  document.querySelector("#statSources").textContent=sourceCount+"곳";
  document.querySelector("#statPosts").textContent=postCount+"건";
  document.querySelector("#statScore").textContent=Math.round(score);
  document.querySelector("#statFirstSeen").textContent=formatDate(issue.first_seen||points[0]?.at,true);
  document.querySelector("#statLastSeen").textContent="마지막 포착 "+formatDate(issue.last_seen||latest.at,true);
  document.querySelector("#statFirstSources").textContent=firstSources.length ? "최초 "+firstSources.join(" · ") : "최초 포착 기록 없음";
  document.querySelector("#statPostDelta").textContent=previous.at ? `직전 대비 ${postCount-Number(previous.post_count||0)>=0?"+":""}${postCount-Number(previous.post_count||0)}건` : "변화 데이터 누적 중";
  document.querySelector("#statScoreDelta").textContent=previous.at ? `직전 대비 ${(score-Number(previous.score||0))>=0?"+":""}${(score-Number(previous.score||0)).toFixed(1)}` : "변화 데이터 누적 중";

  renderSources("#firstCommunityList",firstSources,true);
  renderSources("#currentCommunityList",currentSources,false);

  const posts=issuePosts();
  document.querySelector("#issuePosts").innerHTML=posts.length
    ? posts.map((row,i)=>{
      const p=row.detail||row;
      return `
        <article class="rank-item related-rank-item">
          <div class="rank-num ${i<3?"top":""}">${Number(row.rank)||i+1}</div>
          <div>
            <a class="post-title" href="${safeText(row.url || "#")}" target="_blank" rel="noopener noreferrer">${safeText(row.title)}</a>
            <div class="meta">
              <span class="source">${safeText(row.source)}</span>
              <span>조회 ${fmt(p.views)}</span>
              <span>추천 ${fmt(p.likes)}</span>
              <span>댓글 ${fmt(p.comments)}</span>
            </div>
          </div>
          <span class="rank-change">→</span>
        </article>`;
    }).join("")
    : '<div class="empty">관련 인기글 데이터가 없습니다.</div>';

  renderChart();
  renderReactions();
}

async function load() {
  if (!issueId) { render(); return; }
  try {
    const [live,archive,history]=await Promise.all([
      fetch("../data/latest.json?ts="+Date.now(),{cache:"no-store"}),
      fetch("../data/archive.json?ts="+Date.now(),{cache:"no-store"}),
      fetch("../data/issue-history.json?ts="+Date.now(),{cache:"no-store"})
    ]);
    if(live.ok) liveData=await live.json();
    if(archive.ok) archiveData=await archive.json();
    if(history.ok) historyData=await history.json();
  } catch {}
  resolveIssue();
  render();
}

document.querySelectorAll("[data-issue-metric]").forEach(button=>{
  button.addEventListener("click",()=>{
    document.querySelectorAll("[data-issue-metric]").forEach(x=>x.classList.remove("active"));
    button.classList.add("active");
    issueMetric=button.dataset.issueMetric;
    renderChart();
  });
});

document.querySelector("#themeToggle").addEventListener("click",()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme",document.body.classList.contains("dark")?"dark":"light");
});
if(localStorage.getItem("commurank-theme")==="dark") document.body.classList.add("dark");

load();
