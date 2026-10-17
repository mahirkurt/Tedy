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
  // `json()` may parse to null or a bare value ("null", "42"): the payload is then empty, not a crash.
  if (!veri || typeof veri !== 'object' || Array.isArray(veri)) veri = {}
  event.waitUntil(self.registration.showNotification(veri.baslik || 'TEDY', {
    body: veri.govde || '',
    tag: veri.etiket || 'tedy',
    renotify: true,
    icon: '/tedy-192.png',
    // Android draws the badge from its alpha channel alone: a white silhouette on a clear ground.
    badge: '/tedy-rozet-96.png',
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
      if (new URL(p.url).origin !== self.location.origin || !('focus' in p)) continue
      try {
        await p.focus()
        // Denetlenmeyen pencerede navigate() reddedilir; o zaman yeni pencere açılır.
        if (p.url !== hedef && 'navigate' in p) await p.navigate(hedef)
        return
      } catch {
        break // pencere kullanılamadı: aşağıda yeni pencere açılır
      }
    }
    await self.clients.openWindow(hedef)
  })())
})

// The push service replaced or expired the subscription (spec 2026-10-16 §7, final review):
// subscribe again with the server's key and tell the server, or this device silently stops
// receiving. The session cookie goes with the request (same origin). Failures are dropped:
// the dashboard re-posts its subscription on the next opening.
function anahtarBaytlari(b64url) {
  const b64 = (b64url + '='.repeat((4 - (b64url.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  return Uint8Array.from(atob(b64), c => c.charCodeAt(0))
}

function cihazAdi(ua) {
  if (/iPhone|iPad|iPod/.test(ua)) return 'iPhone'
  if (/Android/.test(ua)) return 'Android'
  if (/Macintosh/.test(ua)) return 'Mac'
  if (/Windows/.test(ua)) return 'Windows'
  return 'Tarayıcı'
}

self.addEventListener('pushsubscriptionchange', event => {
  event.waitUntil((async () => {
    const yanit = await fetch('/api/bildirim/anahtar', { credentials: 'same-origin' })
    if (!yanit.ok) return
    const { anahtar } = await yanit.json()
    if (!anahtar) return
    const abonelik = await self.registration.pushManager.subscribe({
      userVisibleOnly: true, applicationServerKey: anahtarBaytlari(anahtar),
    })
    await fetch('/api/bildirim/abonelik', {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...abonelik.toJSON(), cihaz: cihazAdi((self.navigator && self.navigator.userAgent) || '') }),
    })
  })().catch(() => {}))
})
