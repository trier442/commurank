const CACHE_NAME = "commurank-shell-v3";
const SHELL = [
  "/",
  "/styles.css",
  "/favicon.svg",
  "/manifest.webmanifest",
  "/my/",
  "/issues/",
  "/briefing/",
  "/search/",
  "/post/",
  "/issue/",
  "/community/dcinside/",
  "/community/fmkorea/",
  "/community/theqoo/",
  "/community/ruliweb/",
  "/community/clien/",
  "/community/inven/",
  "/community/ppomppu/"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== location.origin || !url.pathname.startsWith("/")) return;

  if (url.pathname.includes("/data/") || url.pathname.endsWith(".json")) {
    const cacheKey = new Request(url.origin + url.pathname);
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(cacheKey, copy));
          return response;
        })
        .catch(() => caches.match(cacheKey))
    );
    return;
  }

  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then(cached => {
      const network = fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
          return response;
        })
        .catch(() => cached || caches.match("/"));
      return cached || network;
    })
  );
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const target = event.notification?.data?.url || "/my/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(clients => {
      for (const client of clients) {
        if ("focus" in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      return self.clients.openWindow(target);
    })
  );
});