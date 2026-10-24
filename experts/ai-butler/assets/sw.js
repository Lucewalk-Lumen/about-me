/* Teacher Workbench Service Worker — v1.1.4 (local-only) */
var CACHE = 'wb-local-v1-1-4';
var ASSETS = [
  'teacher-workbench.html',
  'manifest.webmanifest',
  'icon-192.png',
  'icon-512.png',
  'icon-maskable-512.png',
  'icon.svg',
  'apple-touch-icon.png'
];
self.addEventListener('install', function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){ return Promise.all(ASSETS.map(function(a){ return c.add(a).catch(function(){}); })); }).then(function(){ return self.skipWaiting(); }));
});
self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(keys){ return Promise.all(keys.filter(function(k){ return k !== CACHE; }).map(function(k){ return caches.delete(k); })); }).then(function(){ return self.clients.claim(); }));
});
self.addEventListener('fetch', function(e){
  if(e.request.method !== 'GET') return;
  var url = new URL(e.request.url); if(url.origin !== location.origin) return;
  var path = url.pathname;
  var isHTML = path.endsWith('.html') || path.endsWith('/') || path === '/' || path.indexOf('.') < 0;
  if(isHTML){ e.respondWith(fetch(e.request).then(function(res){ if(res && res.status===200){ var copy=res.clone(); caches.open(CACHE).then(function(c){ c.put(e.request, copy); }); } return res; }).catch(function(){ return caches.match(e.request).then(function(h){ return h || caches.match('teacher-workbench.html'); }); })); return; }
  e.respondWith(caches.match(e.request).then(function(hit){ return hit || fetch(e.request).then(function(res){ if(res && res.status===200){ var copy=res.clone(); caches.open(CACHE).then(function(c){ c.put(e.request, copy); }); } return res; }).catch(function(){ return caches.match('teacher-workbench.html'); }); }));
});