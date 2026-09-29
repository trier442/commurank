const REPO="trier442/commurank";
let latest=null, issueRankings=null, archiveIndex=null, issueArchiveIndex=null, briefing=null, briefingIndex=null, metricHistory=null, issueHistory=null, analyticsConfig=null;

const fmt=n=>new Intl.NumberFormat("ko-KR",{notation:Number(n)>9999?"compact":"standard"}).format(Number(n)||0);
const safe=v=>String(v??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[ch]));
function minutesAgo(value){
  const t=new Date(value).getTime();
  if(!Number.isFinite(t)) return null;
  return Math.max(0,Math.round((Date.now()-t)/60000));
}
function statusPill(kind,text){return '<span class="admin-pill '+kind+'">'+safe(text)+'</span>'}
function duplicateValues(values){
  const seen=new Set(),dups=new Set();
  values.forEach(v=>{if(seen.has(v))dups.add(v);else seen.add(v)});
  return [...dups];
}
function diagnostic(ok,title,detail){
  return '<div class="diagnostic-row '+(ok?'ok':'warn')+'"><span>'+(ok?'✓':'!')+'</span><div><strong>'+safe(title)+'</strong><p>'+safe(detail)+'</p></div></div>';
}

function renderSummary(){
  const age=minutesAgo(latest?.collected_at);
  const fresh=age!==null && age<=75;
  document.querySelector("#freshness").textContent=age===null?"-":age+"분";
  document.querySelector("#freshnessSub").textContent=fresh?"정상 갱신 중":"갱신 지연 확인 필요";

  const sources=latest?.sources||[];
  const ok=sources.filter(s=>s.ok&&Number(s.count)>0).length;
  const cached=sources.filter(s=>s.cached&&Number(s.count)>0).length;
  document.querySelector("#sourceHealth").textContent=ok+"/"+sources.length;
  document.querySelector("#sourceHealthSub").textContent=cached?cached+"개 캐시 대체":"직접 수집 기준";

  document.querySelector("#realtimeCount").textContent=latest?.rankings?.realtime?.length||0;
  document.querySelector("#issueCount").textContent=issueRankings?.rankings?.realtime?.length||0;

  const briefAge=minutesAgo(briefing?.collected_at);
  const analyticsOn=Boolean(analyticsConfig?.enabled && analyticsConfig?.ga4_id);
  document.querySelector("#analyticsState").textContent=analyticsOn ? "GA4 연결됨" : "미연결";
  document.querySelector("#analyticsState").className=analyticsOn ? "analytics-on" : "";

  document.querySelector("#briefingState").textContent=briefing?.date||"-";
  document.querySelector("#briefingSub").textContent=briefAge===null?"데이터 없음":briefAge+"분 전 갱신";
}

function renderSources(){
  const rows=latest?.sources||[];
  document.querySelector("#collectorUpdated").textContent=latest?.collected_at?new Date(latest.collected_at).toLocaleString("ko-KR"):"-";
  const box=document.querySelector("#sourceTable");
  box.innerHTML='<div class="admin-table-head"><span>소스</span><span>상태</span><span>수집</span><span>응답</span></div>'+
    rows.map(s=>{
      let state=s.ok?statusPill("ok","정상"):s.cached?statusPill("cache","캐시"):statusPill("warn","실패");
      const elapsed=s.elapsed_ms!=null?Math.round(Number(s.elapsed_ms))+"ms":"-";
      const err=s.error?'<small title="'+safe(s.error)+'">'+safe(s.error.slice(0,60))+'</small>':'';
      return '<div class="admin-table-row"><strong>'+safe(s.source)+'</strong><div>'+state+err+'</div><span>'+fmt(s.count)+'</span><span>'+elapsed+'</span></div>';
    }).join("");
}

function collectDiagnostics(){
  const out=[];
  const realtime=latest?.rankings?.realtime||[];
  const topicIds=(latest?.topics||[]).map(x=>x.id).filter(Boolean);
  const issueIds=(issueRankings?.rankings?.realtime||[]).map(x=>x.id).filter(Boolean);

  const age=minutesAgo(latest?.collected_at);
  out.push({ok:age!==null&&age<=75,title:"수집 주기",detail:age===null?"최근 수집 시각을 읽을 수 없습니다.":"최근 갱신 "+age+"분 전"});
  out.push({ok:realtime.length===100,title:"실시간 TOP100",detail:"현재 "+realtime.length+"개"});
  out.push({ok:duplicateValues(realtime.map(x=>x.url).filter(Boolean)).length===0,title:"게시글 URL 중복",detail:"중복 "+duplicateValues(realtime.map(x=>x.url).filter(Boolean)).length+"건"});
  out.push({ok:duplicateValues(topicIds).length===0,title:"동시 화제 ID",detail:"중복 "+duplicateValues(topicIds).length+"건"});
  out.push({ok:duplicateValues(issueIds).length===0,title:"이슈 랭킹 ID",detail:"중복 "+duplicateValues(issueIds).length+"건"});

  const failed=(latest?.sources||[]).filter(s=>!s.ok&&!s.cached);
  out.push({ok:failed.length===0,title:"소스 완전 실패",detail:failed.length?failed.map(s=>s.source).join(", "):"없음"});

  const cached=(latest?.sources||[]).filter(s=>s.cached);
  out.push({ok:cached.length===0,title:"캐시 대체 사용",detail:cached.length?cached.map(s=>s.source).join(", "):"현재 없음"});

  const bAge=minutesAgo(briefing?.collected_at);
  out.push({ok:bAge!==null&&bAge<=90,title:"브리핑 갱신",detail:bAge===null?"브리핑 없음":"최근 "+bAge+"분 전"});

  return out;
}
function renderDiagnostics(){
  const rows=collectDiagnostics();
  const warnings=rows.filter(x=>!x.ok);
  document.querySelector("#alertCount").textContent=warnings.length;
  document.querySelector("#alertSub").textContent=warnings.length?"확인 필요":"이상 없음";
  document.querySelector("#diagnosticList").innerHTML=rows.map(x=>diagnostic(x.ok,x.title,x.detail)).join("");
}

function renderVolumes(){
  const archPeriods=archiveIndex?.periods||{};
  const issuePeriods=issueArchiveIndex?.periods||{};
  const metrics=Object.keys(metricHistory?.posts||{}).length;
  const issueHist=Object.keys(issueHistory?.issues||{}).length;
  const cards=[
    ["일간 아카이브",(archPeriods.daily||[]).length+"일"],
    ["주간 아카이브",(archPeriods.weekly||[]).length+"주"],
    ["월간 아카이브",(archPeriods.monthly||[]).length+"개월"],
    ["이슈 아카이브",(issuePeriods.daily||[]).length+"일"],
    ["게시글 시계열",fmt(metrics)+"개"],
    ["이슈 시계열",fmt(issueHist)+"개"],
    ["브리핑 아카이브",(briefingIndex?.items||[]).length+"일"],
    ["실시간 키워드",(latest?.keywords||[]).length+"개"]
  ];
  document.querySelector("#volumeGrid").innerHTML=cards.map(([k,v])=>'<div><span>'+safe(k)+'</span><strong>'+safe(v)+'</strong></div>').join("");
}

async function renderWorkflows(){
  const box=document.querySelector("#workflowStatus");
  try{
    const r=await fetch("https://api.github.com/repos/"+REPO+"/actions/runs?per_page=8",{headers:{Accept:"application/vnd.github+json"}});
    if(!r.ok) throw new Error("GitHub API "+r.status);
    const d=await r.json();
    const rows=(d.workflow_runs||[]).filter((x,i,a)=>i<6);
    box.innerHTML=rows.map(run=>{
      const kind=run.status!=="completed"?"cache":run.conclusion==="success"?"ok":"warn";
      const label=run.status!=="completed"?run.status:(run.conclusion||"-");
      return '<a class="workflow-row" href="'+safe(run.html_url)+'" target="_blank" rel="noopener noreferrer"><div><strong>'+safe(run.name)+'</strong><small>'+safe(new Date(run.updated_at).toLocaleString("ko-KR"))+'</small></div>'+statusPill(kind,label)+'</a>';
    }).join("");
  }catch(e){
    box.innerHTML='<div class="empty">GitHub 자동화 상태를 불러오지 못했습니다.</div>';
  }
}

async function load(){
  const base="../data/";
  const reqs=[
    ["latest",base+"latest.json"],
    ["issues",base+"issue-rankings.json"],
    ["archive",base+"archive-index.json"],
    ["issueArchive",base+"issue-archive-index.json"],
    ["briefing",base+"briefing.json"],
    ["briefingIndex",base+"briefing-index.json"],
    ["metrics",base+"metric-history.json"],
    ["issueHistory",base+"issue-history.json"],
    ["analytics","../analytics-config.json"]
  ];
  const results=await Promise.all(reqs.map(async([k,url])=>{
    try{const r=await fetch(url+"?ts="+Date.now(),{cache:"no-store"});return [k,r.ok?await r.json():null]}catch{return [k,null]}
  }));
  const map=Object.fromEntries(results);
  latest=map.latest;issueRankings=map.issues;archiveIndex=map.archive;issueArchiveIndex=map.issueArchive;
  briefing=map.briefing;briefingIndex=map.briefingIndex;metricHistory=map.metrics;issueHistory=map.issueHistory;analyticsConfig=map.analytics;
  renderSummary();renderSources();renderDiagnostics();renderVolumes();renderWorkflows();
}
document.querySelector("#themeToggle").addEventListener("click",()=>{
  document.body.classList.toggle("dark");
  localStorage.setItem("commurank-theme",document.body.classList.contains("dark")?"dark":"light");
});
if(localStorage.getItem("commurank-theme")==="dark")document.body.classList.add("dark");
load();