{{- $css := resources.Get "css/style.css" | resources.ExecuteAsTemplate "assets/style.css" . | fingerprint -}}
{{- $js := resources.Get "js/app.js" | js.Build (dict "targetPath" "assets/app.js" "target" "es2020") | fingerprint -}}
{{- $poster := resources.Get "images/pickleball-poster.webp" | fingerprint -}}
{{- $community := resources.Get "images/pickleball-community.webp" | fingerprint -}}
{{- $font := resources.Get "fonts/Anton-Regular.ttf" | fingerprint -}}
{{- $version := printf "%s%s%s%s%s%s%s" $css.Data.Integrity $js.Data.Integrity $poster.Data.Integrity $community.Data.Integrity $font.Data.Integrity (readFile "layouts/home.html") .Site.Params.edition | sha256 -}}
const PREFIX = 'pickleball-shell:' + self.registration.scope + '::';
const CACHE = PREFIX + {{ $version | jsonify | safeJS }};
const SHELL = [{{ "" | relURL | jsonify | safeJS }}, {{ $css.RelPermalink | jsonify | safeJS }}, {{ $js.RelPermalink | jsonify | safeJS }}, {{ "icon.svg" | relURL | jsonify | safeJS }}, {{ $poster.RelPermalink | jsonify | safeJS }}, {{ $community.RelPermalink | jsonify | safeJS }}, {{ $font.RelPermalink | jsonify | safeJS }}];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL.map(path => new Request(path, { cache: 'reload' })))));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith(PREFIX) && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || !url.href.startsWith(self.registration.scope)) return;
  if (request.mode === 'navigate') {
    // Serve this worker's matching HTML and hashed assets as one version.
    // Updates install independently and activate after old tabs are closed.
    event.respondWith(caches.open(CACHE).then(cache => cache.match(SHELL[0])).then(cached => cached || fetch(request)));
  } else if (SHELL.some(path => new URL(path,self.location).href === url.href)) {
    event.respondWith(caches.open(CACHE).then(cache => cache.match(request)).then(cached => cached || fetch(request)));
  }
});
