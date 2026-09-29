(() => {
  const BASE = "/";
  let deferredPrompt = null;

  if (!document.querySelector('link[rel="manifest"]')) {
    const link = document.createElement("link");
    link.rel = "manifest";
    link.href = BASE + "manifest.webmanifest";
    document.head.appendChild(link);
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register(BASE + "sw.js", { scope: BASE }).catch(() => {});
    });
  }

  function isStandalone() {
    return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  }

  function refreshButtons() {
    document.querySelectorAll("[data-pwa-install]").forEach(button => {
      if (isStandalone()) {
        button.hidden = true;
        return;
      }
      button.hidden = !(deferredPrompt || /iphone|ipad|ipod/i.test(navigator.userAgent));
    });
    document.querySelectorAll("[data-pwa-status]").forEach(node => {
      node.textContent = isStandalone() ? "앱으로 실행 중" : deferredPrompt ? "설치 가능" : "브라우저에서 사용 중";
    });
  }

  window.addEventListener("beforeinstallprompt", event => {
    event.preventDefault();
    deferredPrompt = event;
    refreshButtons();
  });

  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    refreshButtons();
    window.commURankTrack?.("pwa_installed", { source_page: location.pathname });
  });

  async function install() {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice.catch(() => null);
      if (choice?.outcome === "accepted") {
        window.commURankTrack?.("pwa_install_accept", { source_page: location.pathname });
      }
      deferredPrompt = null;
      refreshButtons();
      return;
    }

    if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
      alert("iPhone/iPad에서는 Safari의 공유 버튼을 누른 뒤 ‘홈 화면에 추가’를 선택하세요.");
    }
  }

  window.commURankInstall = install;

  document.addEventListener("click", event => {
    const button = event.target.closest("[data-pwa-install]");
    if (!button) return;
    install();
  });

  refreshButtons();
})();