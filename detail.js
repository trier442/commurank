const originalUrl = new URLSearchParams(location.search).get("url") || "";
let liveData = null;
let archiveData = {};
let historyData = {};
let post = null;
let historyItem = null;
let metric = "views";

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

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("ko-KR", {
    year:"numeric", month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit"
  });
}

function allCurrentPosts() {
  const map = new Map();
  Object.values(liveData?.community_rankings || {}).forEach(data => {
    (data?.realtime || []).forEach(p => map.set(p.url, p));
  });
  (liveData?.rankings?.realtime || []).forEach(p => map.set(p.url, p));
  return [...map.values()];
}

function resolvePost() {
  const current = allCurrentPosts().find(p => p.url === originalUrl);
  const archived = archiveData?.[originalUrl];
  const historic = historyData?.posts?.[originalUrl];

  post = current || (archived ? {
    title:archived.title,
    source:archived.source,
    category:archived.category,
    url:archived.url,
    views:archived.max_views || 0,
    likes:archived.max_likes || 0,
    comments:archived.max_comments || 0,
    score:archived.peak_score || 0
  } : historic || null);

  historyItem = historic || null;
}

function rememberCurrentPost() {
  if (!post?.url) return;
  try {
    const key = "commurank_recent_posts_v1";
    const old = JSON.parse(localStorage.getItem(key) || "[]");
    const rows = Array.isArray(old) ? old.filter(item => item?.url !== post.url) : [];
    rows.unshift({
      url: post.url,
      title: post.title || "",
      source: post.source || "",
      at: new Date().toISOString()
    });
    localStorage.setItem(key, JSON.stringify(rows.slice(0,20)));
  } catch {}
}

function currentRank() {
  const idx = (liveData?.rankings?.realtime || []).findIndex(p => p.url === originalUrl);
  return idx >= 0 ? idx + 1 : null;
}

function currentSourceRank() {
  const rows = liveData?.community_rankings?.[post?.source]?.realtime || [];
  const idx = rows.findIndex(p => p.url === originalUrl);
  return idx >= 0 ? idx + 1 : null;
}

function deltas() {
  const points = historyItem?.points || [];
  if (points.length < 2) return {views:0,likes:0,comments:0,rank:0,minutes:0};
  const a = points[points.length - 2];
  const b = points[points.length - 1];
  const minutes = Math.max(1, Math.round((new Date(b.at) - new Date(a.at))/60000));
  return {
    views:Math.max(0, Number(b.views||0)-Number(a.views||0)),
    likes:Math.max(0, Number(b.likes||0)-Number(a.likes||0)),
    comments:Math.max(0, Number(b.comments||0)-Number(a.comments||0)),
    rank:(a.rank && b.rank) ? Number(a.rank)-Number(b.rank) : 0,
    minutes
  };
}

function titleTokens(title) {
  const stop = new Set(["오늘","요즘","지금","현재","진짜","관련","반응","근황","결과","이유","정리","공개","발표","논란","소식","사진","영상","사람","이야기","게시글","대한","에서","으로","그리고","하지만","그런데","했다","하는","있는","없는","jpg","gif","mp4","webp","ㅋㅋ","ㅋㅋㅋ","ㄷㄷ","속보","이번","그냥","정도"]);
  return [...new Set(
    String(title||"").toLowerCase()
      .replace(/[^0-9a-z가-힣 ]+/g," ")
      .split(/\s+/)
      .map(x=>x.trim())
      .filter(x=>x.length>=2 && !stop.has(x) && !/^\d+$/.test(x))
  )];
}

function relatedPosts() {
  const all = allCurrentPosts().filter(p => p.url !== originalUrl);
  const tokens = titleTokens(post?.title);
  const currentTopic = (liveData?.topics || []).find(topic =>
    (topic.posts || []).some(p => p.url === originalUrl)
  );
  const issueLink = document.querySelector("#issueLink");
  if (currentTopic?.id) {
    issueLink.href = "../issue/?id=" + encodeURIComponent(currentTopic.id);
    issueLink.hidden = false;
  } else {
    issueLink.hidden = true;
  }

  const topicUrls = new Set((currentTopic?.posts || []).map(p=>p.url));
  const scored = all.map(p => {
    const pt = titleTokens(p.title);
    const shared = tokens.filter(t => pt.includes(t));
    let score = shared.length * 20;
    if (topicUrls.has(p.url)) score += 80;
    if (p.source !== post?.source) score += 5;
    score += Math.min(10, Number(p.score||0)*0.08);
    return {...p, shared, relatedScore:score};
  }).filter(p => p.relatedScore >= 20)
    .sort((a,b)=>b.relatedScore-a.relatedScore)
    .slice(0,8);

  return scored;
}

function keywordRows() {
  const tokens = titleTokens(post?.title);
  const liveKeywords = liveData?.keywords || [];
  const weighted = tokens.map(token => {
    const hit = liveKeywords.find(k => k.keyword === token || (k.aliases||[]).includes(token));
    return {token, score:hit ? Number(hit.score||0)+50 : token.length*2};
  }).sort((a,b)=>b.score-a.score);
  return weighted.slice(0,10);
}

function chartSvg(points, accessor, {invert=false, label=""}={}) {
  if (!points.length) return '<div class="empty">아직 변화 기록이 충분하지 않습니다.</div>';

  const values = points.map(accessor).filter(v => Number.isFinite(v));
  if (!values.length) return '<div class="empty">표시할 수치가 없습니다.</div>';

  const width = 760, height = 230, padX = 44, padY = 26;
  const min = Math.min(...values), max = Math.max(...values);
  const range = Math.max(1, max-min);
  const n = Math.max(1, points.length-1);

  const coords = points.map((p,i)=>{
    const v = accessor(p);
    const x = padX + (width-padX*2)*(i/n);
    let t = (v-min)/range;
    if (invert) t = 1-t;
    const y = padY + (height-padY*2)*(1-t);
    return {x,y,v,p};
  });

  const poly = coords.map(c=>c.x.toFixed(1)+","+c.y.toFixed(1)).join(" ");
  const first = coords[0], last = coords[coords.length-1];
  const minLabel = invert ? max : min;
  const maxLabel = invert ? min : max;

  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${safeText(label)} 추이">
      <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height-padY}" class="chart-axis"/>
      <line x1="${padX}" y1="${height-padY}" x2="${width-padX}" y2="${height-padY}" class="chart-axis"/>
      <line x1="${padX}" y1="${padY}" x2="${width-padX}" y2="${padY}" class="chart-grid"/>
      <line x1="${padX}" y1="${height/2}" x2="${width-padX}" y2="${height/2}" class="chart-grid"/>
      <polyline points="${poly}" fill="none" class="chart-line"/>
      ${coords.map(c=>`<circle cx="${c.x}" cy="${c.y}" r="3.5" class="chart-dot"><title>${safeText(formatDate(c.p.at))}: ${fmt(c.v)}</title></circle>`).join("")}
      <text x="8" y="${padY+4}" class="chart-label">${safeText(String(maxLabel))}</text>
      <text x="8" y="${height-padY+4}" class="chart-label">${safeText(String(minLabel))}</text>
      <text x="${padX}" y="${height-5}" class="chart-label">${safeText(new Date(first.p.at).toLocaleTimeString("ko-KR",{hour:"2-digit",minute:"2-digit"}))}</text>
      <text x="${width-padX}" y="${height-5}" text-anchor="end" class="chart-label">${safeText(new Date(last.p.at).toLocaleTimeString("ko-KR",{hour:"2-digit",minute:"2-digit"}))}</text>
    </svg>`;
}

function renderCharts() {
  const points = historyItem?.points || [];
  const rankPoints = points.filter(p => Number.isFinite(Number(p.rank)) && p.rank !== null);
  document.querySelector("#rankChart").innerHTML = chartSvg(rankPoints, p=>Number(p.rank), {invert:true,label:"통합 순위"});
  document.querySelector("#metricChart").innerHTML = chartSvg(points, p=>Number(p[metric]||0), {label:metric});

  if (points.length) {
    document.querySelector("#historyRange").textContent =
      `${formatDate(points[0].at)} ~ ${formatDate(points[points.length-1].at)} · ${points.length}회`;
  }
}

function detailLink(url) {
  return safeText(url || "#");
}

function render() {
  if (!post) {
    document.querySelector("#postTitle").textContent = "게시글 데이터를 찾을 수 없습니다.";
    document.querySelector("#postMeta").innerHTML = '<span>검색 또는 메인 랭킹에서 다시 선택해 주세요.</span>';
    document.querySelector("#originalLink").hidden = true;
    document.querySelector("#communityLink").hidden = true;
    return;
  }

  rememberCurrentPost();
  document.title = post.title + " | 커뮤랭크";
  document.querySelector("#postTitle").textContent = post.title;
  document.querySelector("#postMeta").innerHTML =
    `<span>${safeText(post.source)}</span><span>${safeText(post.category||"이슈")}</span><span>커뮤랭크 분석</span>`;

  document.querySelector("#originalLink").href = post.url;
  const slug = communitySlug[post.source];
  if (slug) document.querySelector("#communityLink").href = "../community/" + slug + "/";
  else document.querySelector("#communityLink").hidden = true;

  const rank = currentRank();
  const sourceRank = currentSourceRank();
  const d = deltas();

  document.querySelector("#statRank").textContent = rank ? "#" + rank : "아카이브";
  document.querySelector("#statRankMove").textContent = d.rank > 0
    ? `직전 대비 ▲ ${d.rank}`
    : d.rank < 0 ? `직전 대비 ▼ ${Math.abs(d.rank)}`
    : sourceRank ? `${post.source} 내부 #${sourceRank}` : "현재 통합 순위 밖";

  document.querySelector("#statViews").textContent = fmt(post.views);
  document.querySelector("#statLikes").textContent = fmt(post.likes);
  document.querySelector("#statComments").textContent = fmt(post.comments);
  document.querySelector("#statViewsDelta").textContent = d.minutes ? `${d.minutes}분간 +${fmt(d.views)}` : "변화 데이터 누적 중";
  document.querySelector("#statLikesDelta").textContent = d.minutes ? `${d.minutes}분간 +${fmt(d.likes)}` : "변화 데이터 누적 중";
  document.querySelector("#statCommentsDelta").textContent = d.minutes ? `${d.minutes}분간 +${fmt(d.comments)}` : "변화 데이터 누적 중";

  const archive = archiveData?.[originalUrl] || {};
  document.querySelector("#infoSource").textContent = post.source || "-";
  document.querySelector("#infoCategory").textContent = post.category || "-";
  document.querySelector("#infoFirstSeen").textContent = formatDate(archive.first_seen || historyItem?.points?.[0]?.at);
  document.querySelector("#infoLastSeen").textContent = formatDate(archive.last_seen || historyItem?.last_seen);
  document.querySelector("#infoAppearances").textContent = archive.appearances ? fmt(archive.appearances) + "회" : (historyItem?.points?.length ? historyItem.points.length+"회" : "-");

  const keywords = keywordRows();
  document.querySelector("#postKeywords").innerHTML = keywords.length
    ? keywords.map(k=>`<a href="../search/?q=${encodeURIComponent(k.token)}">#${safeText(k.token)}</a>`).join("")
    : '<div class="empty">키워드 분석 결과가 없습니다.</div>';

  const related = relatedPosts();
  document.querySelector("#relatedPosts").innerHTML = related.length
    ? related.map((p,i)=>`
      <article class="rank-item related-rank-item">
        <div class="rank-num">${i+1}</div>
        <div>
          <a class="post-title" href="${detailLink(p.url)}" target="_blank" rel="noopener noreferrer">${safeText(p.title)}</a>
          <div class="meta">
            <span class="source">${safeText(p.source)}</span>
            <span>${p.shared.length ? "공통어 #" + safeText(p.shared.slice(0,3).join(" #")) : "같은 이슈 클러스터"}</span>
          </div>
        </div>
        <span class="rank-change">→</span>
      </article>`).join("")
    : '<div class="empty">현재 수집 데이터에서 충분히 가까운 관련 글이 없습니다.</div>';

  renderCharts();
}

async function load() {
  if (!originalUrl) {
    render();
    return;
  }
  try {
    const [live, archive, history] = await Promise.all([
      fetch("../data/latest.json?ts="+Date.now(), {cache:"no-store"}),
      fetch("../data/archive.json?ts="+Date.now(), {cache:"no-store"}),
      fetch("../data/metric-history.json?ts="+Date.now(), {cache:"no-store"})
    ]);
    if (live.ok) liveData = await live.json();
    if (archive.ok) archiveData = await archive.json();
    if (history.ok) historyData = await history.json();
  } catch {}
  resolvePost();
  render();
}

document.querySelectorAll(".metric-tab").forEach(button=>{
  button.addEventListener("click", ()=>{
    document.querySelectorAll(".metric-tab").forEach(x=>x.classList.remove("active"));
    button.classList.add("active");
    metric = button.dataset.metric;
    renderCharts();
  });
});

document.querySelector("#themeToggle").addEventListener("click", ()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme", document.body.classList.contains("dark") ? "dark" : "light");
});
if (localStorage.getItem("commurank-theme") === "dark") document.body.classList.add("dark");

load();
