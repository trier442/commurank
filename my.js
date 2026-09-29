(() => {
  if (document.querySelector('script[data-commurank-analytics]')) return;
  const s = document.createElement("script");
  s.src = "/analytics.js";
  s.defer = true;
  s.setAttribute("data-commurank-analytics", "1");
  document.head.appendChild(s);
})();

const PREF_KEY="commurank_preferences_v1";
const RECENT_KEY="commurank_recent_posts_v1";
const LAST_VISIT_KEY="commurank_my_last_visit_v1";
const NOTIFY_KEY="commurank_interest_notify_v1";
const NOTIFIED_COLLECTION_KEY="commurank_interest_notified_collection_v1";
const SOURCES=["디시인사이드","더쿠","루리웹","클리앙","인벤","뽐뿌"];

let latest=null;
let archiveData={};
let prefs=loadPrefs();
const previousVisit=localStorage.getItem(LAST_VISIT_KEY)||"";

function safeText(value){
  return String(value??"").replace(/[&<>"']/g,ch=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[ch]));
}
function fmt(n){
  return new Intl.NumberFormat("ko-KR",{notation:Number(n)>9999?"compact":"standard"}).format(Number(n)||0);
}
function normalize(v){return String(v||"").toLowerCase().replace(/\s+/g," ").trim();}
function postUrl(url){return "../post/?url="+encodeURIComponent(url||"");}
function issueUrl(id){return "../issue/?id="+encodeURIComponent(id||"");}

function loadPrefs(){
  try{
    const v=JSON.parse(localStorage.getItem(PREF_KEY)||"{}");
    return {
      keywords:Array.isArray(v.keywords)?v.keywords.filter(Boolean).slice(0,20):[],
      sources:Array.isArray(v.sources)?v.sources.filter(x=>SOURCES.includes(x)):[],
    };
  }catch{return {keywords:[],sources:[]};}
}
function savePrefs(){
  localStorage.setItem(PREF_KEY,JSON.stringify(prefs));
}
function loadRecent(){
  try{
    const rows=JSON.parse(localStorage.getItem(RECENT_KEY)||"[]");
    return Array.isArray(rows)?rows.slice(0,20):[];
  }catch{return [];}
}
function postFirstSeen(post){
  const archived=archiveData?.[post?.url];
  return archived?.first_seen || archived?.last_seen || "";
}
function isNewSinceVisit(post){
  if(!previousVisit) return false;
  const firstSeen=postFirstSeen(post);
  if(firstSeen) return new Date(firstSeen)>new Date(previousVisit);
  return post?.change==="NEW" && latest?.collected_at && new Date(latest.collected_at)>new Date(previousVisit);
}
function notificationEnabled(){
  return localStorage.getItem(NOTIFY_KEY)==="1" && "Notification" in window && Notification.permission==="granted";
}
function renderNotificationState(){
  const button=document.querySelector("#notificationButton");
  const status=document.querySelector("#notificationStatus");
  if(!button||!status) return;

  if(!("Notification" in window)){
    button.disabled=true;
    button.textContent="알림 미지원";
    status.textContent="이 브라우저는 알림을 지원하지 않습니다.";
    return;
  }
  if(Notification.permission==="denied"){
    button.disabled=true;
    button.textContent="알림 차단됨";
    status.textContent="브라우저 설정에서 알림 권한을 허용해야 합니다.";
    return;
  }
  const on=notificationEnabled();
  button.disabled=false;
  button.textContent=on?"관심글 알림 끄기":"관심글 알림 켜기";
  status.textContent=on?"사이트를 열 때 새 관심 글을 알려줍니다.":"알림 꺼짐";
}
async function showInterestNotification(newPosts){
  if(!notificationEnabled()||!newPosts.length||!latest?.collected_at) return;
  if(localStorage.getItem(NOTIFIED_COLLECTION_KEY)===latest.collected_at) return;

  const first=newPosts[0];
  const title=`새 관심 글 ${newPosts.length}개`;
  const body=newPosts.length===1
    ? first.title
    : `${first.title} 외 ${newPosts.length-1}개`;
  const options={
    body:body.slice(0,180),
    icon:"/favicon.svg",
    badge:"/favicon.svg",
    tag:"commurank-interest",
    renotify:false,
    data:{url:"/my/"}
  };

  try{
    if("serviceWorker" in navigator){
      const registration=await navigator.serviceWorker.ready;
      await registration.showNotification(title,options);
    }else{
      new Notification(title,options);
    }
    localStorage.setItem(NOTIFIED_COLLECTION_KEY,latest.collected_at);
  }catch{}
}

function renderSettings(){
  const kwBox=document.querySelector("#savedKeywords");
  kwBox.innerHTML=prefs.keywords.length
    ? prefs.keywords.map(k=>`<button type="button" class="my-chip" data-remove-keyword="${safeText(k)}">#${safeText(k)} <span>×</span></button>`).join("")
    : '<div class="empty">관심 키워드를 추가하면 맞춤 피드가 만들어집니다.</div>';

  document.querySelector("#sourceChoices").innerHTML=SOURCES.map(source=>`
    <button type="button" class="my-source-choice ${prefs.sources.includes(source)?"active":""}" data-source-choice="${safeText(source)}">
      <strong>${safeText(source)}</strong>
      <span>${prefs.sources.includes(source)?"관심 설정됨":"선택"}</span>
    </button>`).join("");
}

function matchPost(post){
  const title=normalize(post.title);
  const keywordHits=prefs.keywords.filter(k=>title.includes(normalize(k)));
  const sourceHit=prefs.sources.includes(post.source);
  if(!keywordHits.length&&!sourceHit) return null;
  const newSinceVisit=isNewSinceVisit(post);
  return {
    ...post,
    keywordHits,
    newSinceVisit,
    matchScore:keywordHits.length*80+(sourceHit?30:0)+(newSinceVisit?35:0)+Number(post.score||0)*0.15
  };
}
function matchIssue(issue){
  const issueSources = (issue.sources?.length ? issue.sources : [...new Set((issue.posts||[]).map(p=>p.source).filter(Boolean))]);
  const hay=normalize([issue.title,...(issue.keywords||[]),...issueSources].join(" "));
  const keywordHits=prefs.keywords.filter(k=>hay.includes(normalize(k)));
  const sourceHits=prefs.sources.filter(s=>issueSources.includes(s));
  if(!keywordHits.length&&!sourceHits.length) return null;
  return {
    ...issue,
    sources:issueSources,
    keywordHits,
    sourceHits,
    matchScore:keywordHits.length*90+sourceHits.length*25+Number(issue.score||0)*0.08
  };
}

function renderFeed(){
  const hasPrefs=prefs.keywords.length||prefs.sources.length;
  const postMap=new Map();
  Object.values(latest?.community_rankings||{}).forEach(data=>{
    (data?.realtime||[]).forEach(p=>{ if(p?.url) postMap.set(p.url,p); });
  });
  (latest?.rankings?.realtime||[]).forEach(p=>{ if(p?.url) postMap.set(p.url,p); });

  const posts=[...postMap.values()]
    .map(matchPost).filter(Boolean)
    .sort((a,b)=>b.matchScore-a.matchScore)
    .slice(0,50);
  const issues=(latest?.topics||[])
    .map(matchIssue).filter(Boolean)
    .sort((a,b)=>b.matchScore-a.matchScore)
    .slice(0,20);

  const newPosts=posts.filter(p=>p.newSinceVisit);
  document.querySelector("#matchedPostCount").textContent=posts.length;
  document.querySelector("#matchedIssueCount").textContent=issues.length;
  document.querySelector("#newSinceVisit").textContent=newPosts.length;
  document.querySelector("#prefCount").textContent=prefs.keywords.length+prefs.sources.length;
  document.querySelector("#feedUpdated").textContent=latest?.collected_at
    ? new Date(latest.collected_at).toLocaleString("ko-KR",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"})
    : "-";

  const postBox=document.querySelector("#myPostList");
  if(!hasPrefs){
    postBox.innerHTML='<div class="empty my-empty">위에서 관심 키워드나 커뮤니티를 선택해 주세요.</div>';
  }else if(!posts.length){
    postBox.innerHTML='<div class="empty my-empty">현재 TOP100에서 관심 조건과 일치하는 글이 없습니다.</div>';
  }else{
    postBox.innerHTML=posts.map((p,i)=>`
      <article class="rank-item">
        <div class="rank-num ${i<3?"top":""}">${i+1}</div>
        <div>
          <a class="post-title" href="${postUrl(p.url)}">${safeText(p.title)}</a>
          <div class="meta">
            <span class="source">${safeText(p.source)}</span>
            <span>조회 ${fmt(p.views)}</span>
            <span>댓글 ${fmt(p.comments)}</span>
            ${p.newSinceVisit?'<span class="my-new-badge">NEW</span>':""}
            ${p.keywordHits.length?`<span class="my-match">#${safeText(p.keywordHits.join(" #"))}</span>`:""}
          </div>
        </div>
        <span class="rank-change">→</span>
      </article>`).join("");
  }

  const issueBox=document.querySelector("#myIssueList");
  if(!hasPrefs){
    issueBox.innerHTML='<div class="empty my-empty">관심 조건을 저장하면 관련 동시 화제를 찾아줍니다.</div>';
  }else if(!issues.length){
    issueBox.innerHTML='<div class="empty my-empty">현재 동시 화제 중 일치하는 이슈가 없습니다.</div>';
  }else{
    issueBox.innerHTML=issues.map((x,i)=>`
      <article class="issue-rank-row">
        <div class="rank-num">${i+1}</div>
        <div class="issue-rank-row-body">
          <a class="post-title" href="${issueUrl(x.id)}">${safeText(x.title)}</a>
          <div class="meta">
            <span>${Number(x.source_count)||0}개 커뮤니티</span>
            <span>관련글 ${Number(x.post_count)||0}건</span>
            ${x.keywordHits.length?`<span class="my-match">#${safeText(x.keywordHits.join(" #"))}</span>`:""}
          </div>
        </div>
        <span class="rank-change">→</span>
      </article>`).join("");
  }
}

function renderRecent(){
  const rows=loadRecent();
  document.querySelector("#recentCount").textContent=rows.length;
  const box=document.querySelector("#recentPosts");
  box.innerHTML=rows.length?rows.map(row=>`
    <a class="my-recent-row" href="${postUrl(row.url)}">
      <strong>${safeText(row.title||"최근 본 게시글")}</strong>
      <span>${safeText(row.source||"")} · ${row.at?new Date(row.at).toLocaleString("ko-KR",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}):""}</span>
    </a>`).join(""):'<div class="empty">아직 최근 본 글이 없습니다.</div>';
}

function renderAll(){renderSettings();renderFeed();renderRecent();}

document.querySelector("#notificationButton").addEventListener("click",async()=>{
  if(!("Notification" in window)) return;

  if(notificationEnabled()){
    localStorage.removeItem(NOTIFY_KEY);
    renderNotificationState();
    return;
  }

  const permission=await Notification.requestPermission();
  if(permission==="granted"){
    localStorage.setItem(NOTIFY_KEY,"1");
  }else{
    localStorage.removeItem(NOTIFY_KEY);
  }
  renderNotificationState();
});

document.querySelector("#keywordForm").addEventListener("submit",e=>{
  e.preventDefault();
  const input=document.querySelector("#keywordInput");
  const value=input.value.trim().replace(/^#/,"");
  if(!value) return;
  if(!prefs.keywords.some(k=>normalize(k)===normalize(value))){
    prefs.keywords=[value,...prefs.keywords].slice(0,20);
    savePrefs();
  }
  input.value="";
  renderAll();
});
document.querySelector("#savedKeywords").addEventListener("click",e=>{
  const btn=e.target.closest("[data-remove-keyword]");
  if(!btn) return;
  const value=btn.dataset.removeKeyword;
  prefs.keywords=prefs.keywords.filter(k=>k!==value);
  savePrefs();renderAll();
});
document.querySelector("#sourceChoices").addEventListener("click",e=>{
  const btn=e.target.closest("[data-source-choice]");
  if(!btn) return;
  const source=btn.dataset.sourceChoice;
  prefs.sources=prefs.sources.includes(source)
    ? prefs.sources.filter(x=>x!==source)
    : [...prefs.sources,source];
  savePrefs();renderAll();
});
document.querySelector("#clearKeywords").addEventListener("click",()=>{
  prefs.keywords=[];savePrefs();renderAll();
});
document.querySelector("#clearSources").addEventListener("click",()=>{
  prefs.sources=[];savePrefs();renderAll();
});
document.querySelector("#clearRecent").addEventListener("click",()=>{
  localStorage.removeItem(RECENT_KEY);renderRecent();
});
document.querySelector("#themeToggle").addEventListener("click",()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme",document.body.classList.contains("dark")?"dark":"light");
});
if(localStorage.getItem("commurank-theme")==="dark")document.body.classList.add("dark");

(async function load(){
  try{
    const [live,archive]=await Promise.all([
      fetch("../data/latest.json?ts="+Date.now(),{cache:"no-store"}),
      fetch("../data/archive.json?ts="+Date.now(),{cache:"no-store"})
    ]);
    if(live.ok) latest=await live.json();
    if(archive.ok) archiveData=await archive.json();
  }catch{}

  renderAll();

  const postMap=new Map();
  Object.values(latest?.community_rankings||{}).forEach(data=>{
    (data?.realtime||[]).forEach(p=>{ if(p?.url) postMap.set(p.url,p); });
  });
  (latest?.rankings?.realtime||[]).forEach(p=>{ if(p?.url) postMap.set(p.url,p); });
  const newMatched=[...postMap.values()].map(matchPost).filter(p=>p?.newSinceVisit);
  await showInterestNotification(newMatched);

  if(latest?.collected_at){
    localStorage.setItem(LAST_VISIT_KEY,latest.collected_at);
  }
})();