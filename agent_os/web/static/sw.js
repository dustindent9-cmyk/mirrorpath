// Dallas Service Worker — caches static assets for fast load & offline shell
const CACHE = "dallas-v1"
const STATIC = [
  "/",
  "/static/index.html",
  "/static/manifest.json",
  "/static/icon-192.svg",
  "/static/icon-512.svg",
]

// Install: cache static shell
self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  )
})

// Activate: remove old caches
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
})

// Fetch: cache-first for static, network-first for API
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url)

  // Always go to network for API calls
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ error: "You are offline. Dallas needs a connection to think." }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        })
      )
    )
    return
  }

  // Cache-first for GET static assets only
  if (e.request.method !== "GET") return

  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached
      return fetch(e.request).then(res => {
        if (res && res.status === 200 && res.type === "basic") {
          const clone = res.clone()
          e.waitUntil(caches.open(CACHE).then(c => c.put(e.request, clone)))
        }
        return res
      })
    })
  )
})
