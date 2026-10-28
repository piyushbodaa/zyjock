/* Zyjock offline support. Bump VERSION on every release that changes the shell. */
const VERSION = 'zyjock-v6-analytics';
const SHELL = [
  './', './index.html', './app.js', './domain.js', './expansion.js', './features.js',
  './analytics.js', './styles.css', './favicon.svg', './manifest.webmanifest', './icon-192.png', './icon-512.png',
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(VERSION).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;
  // The data manifest decides which chunks exist: prefer fresh, fall back to cache offline.
  if (request.url.includes('data.json')) {
    event.respondWith(
      fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(VERSION).then(cache => cache.put(request, copy));
        }
        return response;
      }).catch(() => caches.match(request)),
    );
    return;
  }
  // Everything else (shell, data chunks): cache-first, then network + store.
  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(VERSION).then(cache => cache.put(request, copy));
      }
      return response;
    })).catch(() => caches.match('./index.html')),
  );
});
