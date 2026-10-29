const CACHE_NAME = 'ntub-mid-20261029c';
const PRECACHE_ASSETS = [
  '/static/css/app.css',
  '/static/css/course-workspace.css?v=20261029a',
  '/static/css/workspaces.css?v=20261029g',
  '/static/css/operation-dialog.css?v=20261029a',
  '/static/css/design-system.css?v=20261018d',
  '/static/js/navigation.js?v=20261029a',
  '/static/js/schedule-editor.js?v=20261029a',
  '/static/js/operation-dialog.js?v=20261029a',
  '/static/css/schedule-editor.css?v=20261029a',
  '/static/js/timetable-mobile.js?v=20261029a',
  '/static/icons/icon-192.png',
  '/static/img/timetable-icon.svg',
  '/static/icons/icon-512.png',
];
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('Pre-cache partial failure:', err);
      });
    })
  );
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => (key.startsWith('ntub-timetable-') || key.startsWith('ntub-mid-')) && key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/static/') && !url.pathname.endsWith('/manifest.json') && !url.pathname.endsWith('/sw.js')) {
    event.respondWith(
      fetch(request).then((response) => {
        if (response.ok && response.type === 'basic' && !response.redirected) {
          const copy = response.clone();
          event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.put(request, copy)));
        }
        return response;
      }).catch(async () => (await caches.match(request)) || Response.error())
    );
  }
});
