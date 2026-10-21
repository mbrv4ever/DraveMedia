// DraveMedia (statische site) - cachet de schil, laat media streamen.
var CACHE = "dravemedia-site-v1";

self.addEventListener("install", function(e){
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(["./"]).catch(function(){}); }));
});

self.addEventListener("activate", function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){ return k !== CACHE; })
                             .map(function(k){ return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

function isMedia(p){
  return /\.(mp3|m4a|aac|flac|wav|ogg|opus|wma|mp4|webm|mkv|mov|avi|m4v|jpe?g|png|gif|webp|bmp|svg|heic|jfif)$/i.test(p);
}

self.addEventListener("fetch", function(e){
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.pathname.endsWith("/media.json") || isMedia(url.pathname) || req.headers.has("range")) {
    return;  // media + lijst: altijd vers / streamen
  }
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).then(function(resp){
        var copy = resp.clone();
        caches.open(CACHE).then(function(c){ c.put("./", copy); }).catch(function(){});
        return resp;
      }).catch(function(){ return caches.match("./"); })
    );
    return;
  }
  e.respondWith(
    caches.match(req).then(function(cached){
      var net = fetch(req).then(function(resp){
        var copy = resp.clone();
        caches.open(CACHE).then(function(c){ c.put(req, copy); }).catch(function(){});
        return resp;
      }).catch(function(){ return cached; });
      return cached || net;
    })
  );
});
