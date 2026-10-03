// Kleine Schritte – legt die App beim ersten Öffnen aufs Gerät, damit sie ohne Netz läuft.
// Nach jeder Änderung an den Dateien die Versionsnummer hier erhöhen, sonst zeigt das Handy die alte Fassung.
const CACHE = 'kleine-schritte-20261003-persist';
const FILES = [
 "./",
 "index.html",
 "manifest.webmanifest",
 "icons/icon-192.png",
 "icons/icon-512.png",
 "icons/apple-touch-icon.png",
 "vendor/jspdf.umd.min.js",
 "fonts/bitter-700.woff2",
 "fonts/bitter-800.woff2",
 "fonts/figtree-400.woff2",
 "fonts/figtree-400-italic.woff2",
 "fonts/figtree-700.woff2",
 "fonts/patrick-hand-400.woff2"
];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if(e.request.method !== 'GET' || new URL(e.request.url).origin !== self.location.origin) return;
  e.respondWith(caches.match(e.request, {ignoreSearch:true}).then(hit => hit || fetch(e.request).then(res => {
    if(res.ok){ const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
    return res;
  }).catch(() => caches.match('index.html'))));
});
