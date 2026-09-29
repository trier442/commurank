(() => {
  if (document.querySelector('script[data-commurank-pwa]')) return;
  const s = document.createElement("script");
  s.src = "/pwa.js";
  s.defer = true;
  s.setAttribute("data-commurank-pwa", "1");
  document.head.appendChild(s);
})();

(() => {
  const CONFIG_URL = "/analytics-config.json";
  const RECENT_KEY = "commurank_recent_posts_v1";
  const queue = [];
  let ready = false;

  function cleanParams(params = {}) {
    const out = {};
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      out[key] = typeof value === "string" ? value.slice(0, 120) : value;
    }
    return out;
  }

  function send(name, params = {}) {
    const payload = cleanParams(params);
    if (!ready || typeof window.gtag !== "function") {
      queue.push([name, payload]);
      return;
    }
    window.gtag("event", name, payload);
  }

  window.commURankTrack = send;

  function rememberPost(anchor, href) {
    try {
      const resolved = new URL(href, location.href);
      const originalUrl = resolved.searchParams.get("url");
      if (!originalUrl) return;

      const row = anchor.closest(".rank-item, .search-result-card, .brief-list-row, .portal-feature-item, .portal-mini-item, .issue-rank-row");
      const sourceNode = row?.querySelector(".source, .portal-source");
      const source = (sourceNode?.textContent || document.body.dataset.source || "").trim();
      const title = (anchor.textContent || "").trim().slice(0, 180);

      const old = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
      const rows = Array.isArray(old) ? old.filter(item => item?.url !== originalUrl) : [];
      rows.unshift({ url: originalUrl, title, source, at: new Date().toISOString() });
      localStorage.setItem(RECENT_KEY, JSON.stringify(rows.slice(0, 20)));
    } catch {}
  }

  function destinationHost(href) {
    try { return new URL(href, location.href).hostname; }
    catch { return ""; }
  }

  document.addEventListener("click", event => {
    const anchor = event.target.closest("a[href]");
    const keywordButton = event.target.closest("[data-keyword]");

    if (keywordButton) {
      send("keyword_filter", { keyword: keywordButton.dataset.keyword || "" });
    }

    if (!anchor) return;
    const href = anchor.getAttribute("href") || "";

    if (href.includes("/post/?url=")) {
      rememberPost(anchor, href);
      send("post_analysis_open", { page_path: location.pathname });
    } else if (href.includes("/issue/?id=")) {
      send("issue_open", { page_path: location.pathname });
    } else if (href.includes("/community/")) {
      send("community_open", { source_page: location.pathname });
    } else if (href.includes("/issues/")) {
      send("issue_ranking_open", { source_page: location.pathname });
    } else if (href.includes("/briefing/")) {
      send("briefing_open", { source_page: location.pathname });
    }

    if (anchor.id === "originalLink" || anchor.classList.contains("primary-action")) {
      send("original_outbound_click", {
        destination_host: destinationHost(anchor.href),
        source_page: location.pathname
      });
    }
  }, { passive: true });

  document.addEventListener("change", event => {
    const el = event.target;
    if (!(el instanceof HTMLSelectElement)) return;
    if (el.id === "archiveSelect") {
      send("ranking_archive_select", { period: new URLSearchParams(location.search).get("period") || "realtime" });
    } else if (el.id === "issueArchiveSelect") {
      send("issue_archive_select", { period: new URLSearchParams(location.search).get("period") || "realtime" });
    } else if (el.id === "briefingArchive") {
      send("briefing_archive_select", { has_date: Boolean(el.value) });
    } else if (el.id === "sourceFilter" || el.id === "searchSource") {
      send("source_filter_change", { source_page: location.pathname });
    } else if (el.id === "searchSort") {
      send("search_sort_change", { source_page: location.pathname });
    }
  }, { passive: true });

  document.addEventListener("submit", event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const input = form.querySelector('input[type="search"], input[name="q"]');
    if (input && input.value.trim()) {
      send("search_submit", {
        query_length: input.value.trim().length,
        source_page: location.pathname
      });
    }
  });

  fetch(CONFIG_URL, { cache: "no-store" })
    .then(r => r.ok ? r.json() : null)
    .then(config => {
      if (!config?.enabled || !/^G-[A-Z0-9]+$/i.test(config.ga4_id || "")) return;

      window.dataLayer = window.dataLayer || [];
      window.gtag = function(){ window.dataLayer.push(arguments); };
      window.gtag("js", new Date());
      window.gtag("config", config.ga4_id, {
        send_page_view: true,
        anonymize_ip: true
      });

      const script = document.createElement("script");
      script.async = true;
      script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(config.ga4_id);
      document.head.appendChild(script);

      ready = true;
      while (queue.length) {
        const [name, params] = queue.shift();
        window.gtag("event", name, params);
      }
    })
    .catch(() => {});
})();