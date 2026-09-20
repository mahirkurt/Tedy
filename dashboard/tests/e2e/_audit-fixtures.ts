import type { Page } from '@playwright/test'

export const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

// Mirrors output/health.json as actually served on 2026-08-31: two sections the
// portal refused outright, two simply empty.
export const LIVE_HEALTH = {
  timestamp: '2026-08-31T10:32:04', success: true, scrape_errors: [],
  duration_seconds: 122,
  validation_warnings: [
    'odevlerim: veri yok - portalda kayıt yok (boş tablo)',
    'ders_programi: veri yok - modul_kapali: Haftalık Ders Programı: Akademi Modülü kısa bir süre erişime kapalıdır.',
  ],
  unavailable: {
    ders_programi: { reason: 'modul_kapali', detail: 'Haftalık Ders Programı: Akademi Modülü kısa bir süre erişime kapalıdır.' },
    takvim: { reason: 'yetkisiz', detail: 'Akademik Takvim: portal bu sayfaya yetki vermiyor' },
  },
}

const d = (day: number, h = 23, m = 59) =>
  `${String(day).padStart(2, '0')}.09.2026 ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`

export const FULL: Record<string, unknown> = {
  health: { ...LIVE_HEALTH, validation_warnings: [], unavailable: {} },
  homework: {
    summary: '', homework: [
      { 'Ders Adı': 'Matematik', 'Ödev Başlığı': 'Kesirlerde toplama — sayfa 165, 1-12 arası',
        'Ödev Son Teslim Tarihi': d(2), 'Ödev Durumu': '', first_seen: '2026-08-28T09:00' },
      { 'Ders Adı': 'Türkçe', 'Ödev Başlığı': 'Okuma günlüğü',
        'Ödev Son Teslim Tarihi': d(5), 'Ödev Durumu': '', first_seen: '2026-08-27T09:00' },
      { 'Ders Adı': 'Fen Bilimleri', 'Ödev Başlığı': 'Kuvvet ve hareket çalışma kâğıdı',
        'Ödev Son Teslim Tarihi': d(12), 'Ödev Durumu': '', first_seen: '2026-08-26T09:00' },
      { 'Ders Adı': 'Sosyal Bilgiler', 'Ödev Başlığı': 'Harita çalışması',
        'Ödev Son Teslim Tarihi': d(1), 'Ödev Durumu': 'Yaptı', first_seen: '2026-08-20T09:00' },
      { 'Ders Adı': 'İngilizce', 'Ödev Başlığı': 'Unit 2 kelime testi',
        'Ödev Son Teslim Tarihi': d(1), 'Ödev Durumu': 'Yapmadı', first_seen: '2026-08-19T09:00' },
    ],
  },
  exams: { exams: [
    { ders: 'Matematik', tarih: d(8, 10, 0), tur: 'Yazılı' },
    { ders: 'Fen Bilimleri', tarih: d(15, 10, 0), tur: 'Yazılı' },
  ] },
  schedule: {
    weeks: [], today: null,
    latest: { week_label: '31 Ağustos – 4 Eylül', schedule: {
      headers: ['Saat', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma'],
      rows: [
        ['08:30', 'Matematik', 'Türkçe', 'Fen Bilimleri', 'Matematik', 'Görsel Sanatlar'],
        ['09:30', 'Türkçe', 'Matematik', 'İngilizce', 'Sosyal Bilgiler', 'Beden Eğitimi'],
        ['10:30', 'İngilizce', 'Fen Bilimleri', 'Matematik', 'Türkçe', 'Müzik'],
        ['11:30', 'Sosyal Bilgiler', 'Din Kültürü', 'Türkçe', 'Bilişim', 'Matematik'],
      ] } },
  },
  content: {
    'Matematik': { text: 'Kesirlerde toplama ve çıkarma işlendi. Payda eşitleme üzerinde duruldu.', cards: [], items: [] },
    'Türkçe': { text: 'Betimleyici anlatım. Okuma günlüğü örnekleri paylaşıldı.', cards: [], items: [] },
    'Fen Bilimleri': { text: 'Kuvvet ve hareket ünitesine giriş yapıldı.', cards: [], items: [] },
  },
  grades: { grades: [
    { ders: 'Matematik', sinav: '1. Yazılı', puan: '88' },
    { ders: 'Türkçe', sinav: '1. Yazılı', puan: '92' },
    { ders: 'Fen Bilimleri', sinav: '1. Yazılı', puan: '76' },
  ] },
  'calendar/unified': { events: [
    { baslik: 'Veli toplantısı', tarih: d(10, 18, 0), tur: 'etkinlik' },
    { baslik: 'Gezi — Bilim Merkezi', tarih: d(18, 9, 0), tur: 'etkinlik' },
  ] },
  teams: { activities: [{ ad: 'Satranç Kulübü', gun: 'Çarşamba', saat: '15:30' }], ogep: [] },
  announcements: { announcements: [
    { baslik: 'Okul fotoğrafı çekimi', tarih: '2026-09-03', icerik: '3 Eylül Perşembe günü sınıf fotoğrafları çekilecek.' },
  ] },
  enrichment: {},
  'progress/ec': {}, 'progress/a3k': {}, sebit: {},
  'private-lessons': { lessons: [] },
  // Ders İçerikleri reads this too. Without it an unrouted request reaches
  // the real server, and a test that empties /api/content still sees the
  // portal's 36 weeks of cards.
  'content/weeks': { weeks: {}, current: '' },
}

export async function mock(page: Page, data: Record<string, unknown>) {
  // The stream endpoint is real backend code and would reach Gemini.
  await page.route('**/api/assistant/stream', r => r.abort())
  for (const [ep, body] of Object.entries(data)) {
    await page.route(`**/api/${ep}`, r => r.fulfill(json(body)))
  }
  // Everything else falls through to the local test server. A blanket
  // `{}` here is wrong: /api/auth/me and /api/books have required shapes,
  // and returning an empty object for them crashes the app outright.
}

// The shapes the API actually returns today: every section empty but
// well-formed, with health naming the two the portal refused.
export const LIVE: Record<string, unknown> = {
  health: LIVE_HEALTH,
  schedule: { weeks: [], latest: null, today: null },
  homework: { summary: '', homework: [] },
  exams: { exams: [] },
  grades: { grades: [] },
  'calendar/unified': { events: [] },
  teams: { activities: [], ogep: [] },
  announcements: { announcements: [] },
  content: FULL.content,
  enrichment: {},
  'progress/ec': {}, 'progress/a3k': {}, sebit: {},
  'private-lessons': { lessons: [] },
  // Ders İçerikleri reads this too. Without it an unrouted request reaches
  // the real server, and a test that empties /api/content still sees the
  // portal's 36 weeks of cards.
  'content/weeks': { weeks: {}, current: '' },
}
