(() => {
  const fmt = n => new Intl.NumberFormat("ko-KR").format(Number(n) || 0);
  const safe = v => String(v ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[ch]));

  function ageMinutes(value) {
    const t = new Date(value).getTime();
    if (!Number.isFinite(t)) return null;
    return Math.max(0, Math.round((Date.now() - t) / 60000));
  }

  function stateRow(row) {
    const count = Number(row?.count) || 0;
    let kind = "warn";
    let label = "점검";
    let detail = row?.error ? String(row.error).replace(/^\w+Error:\s*/,"") : "현재 수집 결과가 없습니다.";

    if (row?.ok && count > 0) {
      kind = "ok";
      label = "정상";
      detail = `이번 수집 ${fmt(count)}건 · ${fmt(row.elapsed_ms)}ms`;
    } else if (row?.cached && count > 0) {
      kind = "cache";
      label = "캐시";
      const age = Number(row.cache_age_minutes) || 0;
      detail = `최근 정상 데이터 ${fmt(count)}건 · 캐시 ${fmt(age)}분 전`;
    }

    return `
      <div class="public-status-row">
        <div>
          <strong>${safe(row?.source || "알 수 없음")}</strong>
          <span>${safe(detail)}</span>
        </div>
        <em class="public-status-pill ${kind}">${label}</em>
      </div>`;
  }

  async function load() {
    try {
      const response = await fetch("/data/latest.json?ts=" + Date.now(), {cache:"no-store"});
      if (!response.ok) throw new Error("data unavailable");
      const data = await response.json();
      const sources = Array.isArray(data.sources) ? data.sources : [];
      const available = sources.filter(s => Number(s.count) > 0).length;
      const direct = sources.filter(s => s.ok && Number(s.count) > 0).length;
      const cached = sources.filter(s => s.cached && Number(s.count) > 0).length;
      const age = ageMinutes(data.collected_at);

      document.querySelector("#statusFreshness").textContent = age === null ? "-" : (age < 1 ? "방금 전" : age + "분 전");
      document.querySelector("#statusFreshnessSub").textContent = data.collected_at
        ? new Date(data.collected_at).toLocaleString("ko-KR",{year:"numeric",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"})
        : "수집 시각 없음";

      document.querySelector("#statusAvailable").textContent = available + "/" + sources.length;
      document.querySelector("#statusAvailableSub").textContent =
        direct + "개 직접" + (cached ? " · " + cached + "개 캐시" : "");
      document.querySelector("#statusPosts").textContent = fmt(data.rankings?.realtime?.length || 0);
      document.querySelector("#statusRising").textContent = fmt(data.rankings?.rising?.length || 0);
      document.querySelector("#publicSourceStatus").innerHTML = sources.length
        ? sources.map(stateRow).join("")
        : '<div class="empty">연결된 수집 소스가 없습니다.</div>';

      document.body.classList.toggle("status-stale", age !== null && age > 30);
    } catch {
      document.querySelector("#statusFreshness").textContent = "확인 실패";
      document.querySelector("#statusFreshnessSub").textContent = "잠시 후 다시 확인해 주세요.";
      document.querySelector("#publicSourceStatus").innerHTML =
        '<div class="empty">상태 데이터를 불러오지 못했습니다.</div>';
    }
  }

  document.querySelector("#themeToggle").addEventListener("click", ()=>{
    document.body.classList.toggle("dark");
    localStorage.setItem("commurank-theme", document.body.classList.contains("dark") ? "dark" : "light");
  });
  if (localStorage.getItem("commurank-theme") === "dark") document.body.classList.add("dark");

  load();
})();
