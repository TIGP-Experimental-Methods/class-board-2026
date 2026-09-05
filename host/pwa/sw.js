// Service worker: cache the app shell so the page opens instantly and works
// while the board is rebooting. Network first, cache as fallback, so a
// re-flashed web app is picked up on the next load.
const CACHE = 'instrument-v1';
const SHELL = ['./', 'index.html', 'style.css', 'app.js', 'manifest.webmanifest', 'icon.svg',
  'panels/base.js', 'panels/b1.js', 'panels/b2.js', 'panels/b3.js', 'panels/b4.js', 'panels/b5.js',
  'panels/template.js', 'panels/alarms.js'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return res;
    }).catch(() => caches.match(e.request))
  );
});
