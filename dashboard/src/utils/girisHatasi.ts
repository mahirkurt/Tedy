/**
 * The sign-in page's error sentence (B43, D3, D4). The server's `error` string is internal — "Invalid token: …",
 * "No credential provided" — and its one Turkish message was written without Turkish letters, so the page never
 * shows it; it says what happened from the status alone. `null` is no answer at all (the network).
 */
export function girisHatasi(durum: number | null): string {
  if (durum === null) return 'Bağlantı kurulamadı. İnternetini kontrol edip yeniden dene.'
  if (durum === 403) return 'Bu Google hesabıyla giriş yapılamaz. Ailenin tanımlı hesabıyla dene.'
  return 'Giriş yapılamadı. Yeniden dene.'
}
