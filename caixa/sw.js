// Guarda a "casca" do app para abrir rápido; os dados sempre vêm da internet.
const CACHE = 'caixa3d-v2';
const ARQS = ['./', 'index.html', 'estilo.css?v=1', 'app.js?v=2', 'manifest.webmanifest', 'icone-192.png', 'icone-512.png', '../os/config.js', '../os/pix.js', '../os/vendor/qrcode.js'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(ARQS)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => { const c = r.clone(); caches.open(CACHE).then(k => k.put(e.request, c)); return r; }).catch(() => caches.match(e.request)));
});
