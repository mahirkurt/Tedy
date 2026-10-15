/**
 * The sign-in page's error notification (B43, D3, D4). The server's `error` string is internal — "Invalid token: …",
 * "No credential provided" — and its one Turkish message was written without Turkish letters, so the page never
 * shows it; it says what happened from the status alone. `null` is no answer at all (the network).
 *
 * 2026-10-15 (giriş sayfası yenilemesi): the title names the reason, the sentence says what to do — the
 * notification's title used to be a bare "Hata" over the sentence.
 */
export interface GirisBildirimi {
  baslik: string
  metin: string
}

export function girisBildirimi(durum: number | null): GirisBildirimi {
  if (durum === null) return { baslik: 'Bağlantı kurulamadı', metin: 'İnternetini kontrol edip yeniden dene.' }
  if (durum === 403) {
    return {
      baslik: 'Bu hesap tanımlı değil',
      metin: 'Bu Google hesabıyla giriş yapılamaz. Ailenin tanımlı hesabıyla dene.',
    }
  }
  return { baslik: 'Giriş yapılamadı', metin: 'Google girişi doğrulanamadı. Yeniden dene.' }
}
