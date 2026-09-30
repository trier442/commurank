(() => {
  const CONFIG_URL = "/ads-config.json";

  function loadAdSense(clientId) {
    if (document.querySelector('script[data-commurank-adsense]')) return;
    const script = document.createElement("script");
    script.async = true;
    script.crossOrigin = "anonymous";
    script.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=" + encodeURIComponent(clientId);
    script.setAttribute("data-commurank-adsense", "1");
    document.head.appendChild(script);
  }

  fetch(CONFIG_URL, { cache: "no-store" })
    .then(response => response.ok ? response.json() : null)
    .then(config => {
      if (!config?.enabled) return;
      const clientId = String(config.client_id || "").trim();
      if (!/^ca-pub-\d+$/.test(clientId)) return;
      loadAdSense(clientId);
    })
    .catch(() => {});
})();
