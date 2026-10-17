// TEDY servis çalışanı — yalnız bildirim (spec 2026-10-16 §7). Çevrimdışı
// önbellek yapmaz: fetch olayı dinlenmez, sayfa ağdan gelir.
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()))

self.addEventListener('push', event => {
  let veri = {}
  try {
    veri = event.data ? event.data.json() : {}
  } catch {
    veri = { govde: event.data ? event.data.text() : '' }
  }
  event.waitUntil(self.registration.showNotification(veri.baslik || 'TEDY', {
    body: veri.govde || '',
    tag: veri.etiket || 'tedy',
    renotify: true,
    icon: '/tedy-192.png',
    badge: '/tedy-192.png',
    data: { url: veri.url || '/sinavlar' },
  }))
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  const hedef = new URL((event.notification.data && event.notification.data.url) || '/sinavlar',
    self.location.origin).href
  event.waitUntil((async () => {
    const pencereler = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    for (const p of pencereler) {
      if (new URL(p.url).origin === self.location.origin && 'focus' in p) {
        await p.focus()
        if ('navigate' in p) await p.navigate(hedef)
        return
      }
    }
    await self.clients.openWindow(hedef)
  })())
})
