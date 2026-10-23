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
    return `
      <div class="public-status-row">
        <div>
          <strong>${safe(row?.source || "커뮤니티")}</strong>
          <span>인기글 ${fmt(count)}건 반영</span>
        </div>
      </div>`;
  }

  async function load() {
    try {
      const response = await fetch("/data/latest.json?ts=" + Date.now(), {cache:"no-store"});
      if (!response.ok) throw new Error("data unavailable");
      const data = await response.json();
      const sources = Array.isArray(data.sources) ? data.sources : [];
      const available = sources.filter(s => Number(s.count) > 0).length;
      const age = ageMinutes(data.collected_at);

      document.querySelector("#statusFreshness").textContent = data.collected_at ? "최근 반영" : "-";
      document.querySelector("#statusFreshnessSub").textContent = data.collected_at
        ? new Date(data.collected_at).toLocaleString("ko-KR",{year:"numeric",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"})
        : "집계 기준 시각 없음";

      document.querySelector("#statusAvailable").textContent = available + "/" + sources.length;
      document.querySelector("#statusAvailableSub").textContent = "커뮤니티별 공개 인기글";
      document.querySelector("#statusPosts").textContent = fmt(data.rankings?.realtime?.length || 0);
      document.querySelector("#statusRising").textContent = fmt(data.rankings?.rising?.length || 0);
      document.querySelector("#publicSourceStatus").innerHTML = sources.length
        ? sources.map(stateRow).join("")
        : '<div class="empty">현재 반영된 커뮤니티가 없습니다.</div>';

    } catch {
      document.querySelector("#statusFreshness").textContent = "-";
      document.querySelector("#statusFreshnessSub").textContent = "집계 정보";
      document.querySelector("#publicSourceStatus").innerHTML =
        '<div class="empty">현재 표시할 집계 정보가 없습니다.</div>';
    }
  }

  document.querySelector("#themeToggle").addEventListener("click", ()=>{
    document.body.classList.toggle("dark");
    localStorage.setItem("commurank-theme", document.body.classList.contains("dark") ? "dark" : "light");
  });
  if (localStorage.getItem("commurank-theme") === "dark") document.body.classList.add("dark");

  load();
})();
