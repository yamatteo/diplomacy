// Service worker: shows the push notifications sent by the server (webapp/notify.py) and opens the game when one is
// tapped. Served at /sw.js so that its scope is the whole site. It does no caching: the site needs the network.
'use strict';

self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (event) { event.waitUntil(self.clients.claim()); });

self.addEventListener('push', function (event) {
  var data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (error) {
    data = {body: event.data ? event.data.text() : ''};
  }
  // Every push must show a notification (browsers penalise silent pushes), even if the payload is odd.
  event.waitUntil(self.registration.showNotification(data.title || 'Diplomacy', {
    body: data.body || '',
    tag: data.tag || undefined,           // same tag: replaces the previous notification instead of stacking
    renotify: Boolean(data.tag),
    icon: '/static/icon-192.png',
    badge: '/static/badge-96.png',
    data: {url: data.url || '/'}
  }));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = new URL((event.notification.data && event.notification.data.url) || '/', self.location.origin).href;
  event.waitUntil(self.clients.matchAll({type: 'window', includeUncontrolled: true}).then(function (windows) {
    for (var i = 0; i < windows.length; i++) {
      if (new URL(windows[i].url).origin === self.location.origin && 'focus' in windows[i]) {
        return windows[i].focus().then(function (client) { return client.navigate ? client.navigate(url) : client; });
      }
    }
    return self.clients.openWindow(url);
  }));
});
