/* ════════════════════════════════════════════════════════════════════
 * Ashley Mobile — Service Worker
 *
 * Estrategia de cache:
 *   - App shell (HTML/CSS/JS): cache-first (offline-friendly)
 *   - API calls: network-only (no cachear datos dinámicos)
 *   - Imágenes: cache-first con fallback red
 *
 * El SW permite que el PWA se "instale" y abra offline mostrando la
 * última UI vista. Los mensajes nuevos requieren red al PC del user.
 * ════════════════════════════════════════════════════════════════════ */

// v0.18.2-r10 — bumpear CACHE_VERSION al cambiar app.js / app.css.
// Sin bump, los users que ya instalaron una versión anterior siguen
// recibiendo el shell cacheado del SW viejo aunque actualicen el APK.
// Síntoma: bugs supuestamente fixeados (dedupe, avatar, scroll) NO
// aparecen para users en update — están corriendo código viejo.
const CACHE_VERSION = 'ashley-mobile-v0182-r13';
const APP_SHELL = [
  '/mobile/index.html',
  '/mobile/app.css',
  '/mobile/app.js',
  '/mobile/manifest.json',
  '/ashley_pfp.jpg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // API calls: network-only (no cachear chat messages, status, etc.)
  if (url.pathname.startsWith('/api/')) {
    return; // dejar que el browser haga el fetch normal sin SW interception
  }

  // App shell + assets: cache-first
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        // Solo cachear respuestas válidas y same-origin
        if (
          response &&
          response.status === 200 &&
          response.type === 'basic' &&
          (url.pathname.startsWith('/mobile/') ||
           url.pathname === '/ashley_pfp.jpg' ||
           url.pathname.endsWith('.jpg') ||
           url.pathname.endsWith('.png') ||
           url.pathname.endsWith('.css') ||
           url.pathname.endsWith('.js'))
        ) {
          const clone = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // Fallback: si pidió la home, devuelve index.html cacheado
        if (event.request.mode === 'navigate') {
          return caches.match('/mobile/index.html');
        }
        return new Response('offline', { status: 503 });
      });
    })
  );
});
