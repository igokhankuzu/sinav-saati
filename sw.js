// İlk ziyarette dosyaları saklar; sonra internet olmasa da uygulama açılır.
// Sayfayı güncelleyince SURUM'ü bir artır ki telefonlar yeni sürümü alsın.
const SURUM = "sinav-saati-v3";
const DOSYALAR = ["./", "index.html", "manifest.webmanifest", "simge-192.png", "simge-512.png", "apple-touch-icon.png"];

self.addEventListener("install", olay => {
  olay.waitUntil(caches.open(SURUM).then(depo => depo.addAll(DOSYALAR)));
  self.skipWaiting();
});

self.addEventListener("activate", olay => {
  olay.waitUntil(
    caches.keys().then(adlar => Promise.all(adlar.filter(ad => ad !== SURUM).map(ad => caches.delete(ad))))
  );
  self.clients.claim();
});

// Önce internetten dene (güncel sürüm), olmazsa saklanan kopyayı kullan.
self.addEventListener("fetch", olay => {
  if (olay.request.method !== "GET") return;
  olay.respondWith(
    fetch(olay.request)
      .then(yanit => {
        const kopya = yanit.clone();
        caches.open(SURUM).then(depo => depo.put(olay.request, kopya));
        return yanit;
      })
      .catch(() => caches.match(olay.request, { ignoreSearch: true }))
  );
});
