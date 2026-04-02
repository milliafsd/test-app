const CACHE_NAME = 'streamlit-cache-v1';
const urlsToCache = [
  '/',
  'https://test-app-ld2gsfe9r3iaqx57r8njuq.streamlit.app/'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
