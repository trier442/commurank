(() => {
  if (document.querySelector('script[data-commurank-analytics]')) return;
  const s = document.createElement("script");
  s.src = "/analytics.js";
  s.defer = true;
  s.setAttribute("data-commurank-analytics", "1");
  document.head.appendChild(s);
})();

let briefing=null;
let indexData=null;

function safeText(value){
  return String(value??"").replace(/[&<>"']/g,ch=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[ch]));
}
function fmt(n){
  return new Intl.NumberFormat("ko-KR",{notation:Number(n)>9999?"compact":"standard"}).format(Number(n)||0);
}
function timeText(value){
  if(!value) return "-";
  const d=new Date(value);
  return d.toLocaleString("ko-KR",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"});
}
function postUrl(url){ return safeText(url||"#"); }
function issueUrl(id){ return "../issue/?id="+encodeURIComponent(id||""); }

function renderHighlights(){
  const box=document.querySelector("#briefingHighlights");
  const rows=briefing?.highlights||[];
  box.innerHTML=rows.length?rows.map((row,i)=>{
    let href="#";
    if(row.type==="issue"&&row.issue_id) href=issueUrl(row.issue_id);
    else if(row.type==="post"&&row.url) href=postUrl(row.url);
    else if(row.type==="keyword"&&row.keyword) href="../search/?q="+encodeURIComponent(row.keyword);
    return `<a class="brief-highlight" href="${href}">
      <span>${i+1}</span>
      <div><strong>${safeText(row.title)}</strong><p>${safeText(row.text)}</p></div>
    </a>`;
  }).join(""):'<div class="empty">브리핑 하이라이트가 없습니다.</div>';
}
function renderPosts(){
  const rows=briefing?.top_posts||[];
  document.querySelector("#briefingPosts").innerHTML=rows.length?rows.map((p,i)=>`
    <article class="brief-list-row">
      <span class="brief-rank">${i+1}</span>
      <div>
        <a href="${postUrl(p.url)}" target="_blank" rel="noopener noreferrer">${safeText(p.title)}</a>
        <small>${safeText(p.source)} · 조회 ${fmt(p.views)} · 댓글 ${fmt(p.comments)}</small>
      </div>
    </article>`).join(""):'<div class="empty">데이터가 없습니다.</div>';
}
function renderRising(){
  const rows=briefing?.rising||[];
  document.querySelector("#briefingRising").innerHTML=rows.length?rows.slice(0,10).map((p,i)=>`
    <article class="brief-list-row">
      <span class="brief-rank hot">${i+1}</span>
      <div>
        <a href="${postUrl(p.url)}" target="_blank" rel="noopener noreferrer">${safeText(p.title)}</a>
        <small>${safeText(p.source)} · +조회 ${fmt(p.delta_views)} · +댓글 ${fmt(p.delta_comments)}</small>
      </div>
    </article>`).join(""):'<div class="empty">데이터가 없습니다.</div>';
}
function renderIssues(){
  const rows=briefing?.issues||[];
  document.querySelector("#briefingIssues").innerHTML=rows.length?rows.slice(0,10).map((row,i)=>`
    <article class="brief-list-row">
      <span class="brief-rank">${i+1}</span>
      <div>
        <a href="${issueUrl(row.id)}">${safeText(row.title)}</a>
        <small>${Number(row.source_count)||0}개 커뮤니티 · 관련글 ${Number(row.post_count)||0}건 · 점수 ${Math.round(Number(row.score)||0)}</small>
      </div>
    </article>`).join(""):'<div class="empty">데이터가 없습니다.</div>';
}
function renderKeywords(){
  const rows=briefing?.keywords||[];
  document.querySelector("#briefingKeywords").innerHTML=rows.length?rows.map((row,i)=>`
    <a href="../search/?q=${encodeURIComponent(row.keyword)}"><span>${i+1}</span><strong>#${safeText(row.keyword)}</strong><small>${Number(row.post_count)||0}글</small></a>
  `).join(""):'<div class="empty">키워드가 없습니다.</div>';
}
function renderCommunities(){
  const rows=briefing?.community_leaders||[];
  document.querySelector("#briefingCommunities").innerHTML=rows.length?rows.map((row,i)=>`
    <article class="brief-list-row">
      <span class="brief-rank">${i+1}</span>
      <div>
        <a href="${postUrl(row.url)}">${safeText(row.source)} · ${safeText(row.title)}</a>
        <small>조회 ${fmt(row.views)} · 댓글 ${fmt(row.comments)}</small>
      </div>
    </article>`).join(""):'<div class="empty">데이터가 없습니다.</div>';
}
function renderArchive(){
  const select=document.querySelector("#briefingArchive");
  const items=indexData?.items||[];
  const selected=briefing?.date||"";
  select.innerHTML='<option value="">오늘</option>'+items.map(item=>`<option value="${safeText(item.key)}" ${item.key===selected?"selected":""}>${safeText(item.label)}</option>`).join("");
}
function render(){
  if(!briefing) return;
  document.querySelector("#briefingOverview").textContent=briefing.overview||"";
  document.querySelector("#briefSources").textContent=briefing.stats?.sources||0;
  document.querySelector("#briefPosts").textContent=briefing.stats?.daily_posts||0;
  document.querySelector("#briefIssues").textContent=briefing.stats?.daily_issues||0;
  document.querySelector("#briefKeywords").textContent=briefing.stats?.keywords||0;
  document.querySelector("#briefingUpdated").textContent=timeText(briefing.collected_at);
  document.title=(briefing.label||"오늘")+" 인터넷 브리핑 | 커뮤랭크";
  renderHighlights();renderPosts();renderRising();renderIssues();renderKeywords();renderCommunities();renderArchive();
}
async function loadDate(key){
  if(!key){
    const r=await fetch("../data/briefing.json?ts="+Date.now(),{cache:"no-store"});
    if(r.ok) briefing=await r.json();
    render(); return;
  }
  const item=(indexData?.items||[]).find(x=>x.key===key);
  if(!item) return;
  const r=await fetch("../data/"+item.path+"?ts="+Date.now(),{cache:"no-store"});
  if(r.ok){ briefing=await r.json(); render(); }
}
async function load(){
  try{
    const [b,i]=await Promise.all([
      fetch("../data/briefing.json?ts="+Date.now(),{cache:"no-store"}),
      fetch("../data/briefing-index.json?ts="+Date.now(),{cache:"no-store"})
    ]);
    if(b.ok) briefing=await b.json();
    if(i.ok) indexData=await i.json();
  }catch{}
  const params=new URLSearchParams(location.search);
  const date=params.get("date");
  if(date) await loadDate(date); else render();
}
document.querySelector("#briefingArchive").addEventListener("change",e=>{
  const key=e.target.value;
  location.href = key ? "../briefing/" + encodeURIComponent(key) + "/" : "../briefing/";
});
document.querySelector("#briefingLatest").addEventListener("click",()=>{
  history.replaceState(null,"",location.pathname);
  loadDate("");
});
document.querySelector("#themeToggle").addEventListener("click",()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme",document.body.classList.contains("dark")?"dark":"light");
});
if(localStorage.getItem("commurank-theme")==="dark") document.body.classList.add("dark");
load();