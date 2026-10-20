/**
 * Turkish title case for a heading that is a name (a page, a card, a module, a module's section):
 * every word starts with a capital letter, except the conjunctions and question particles that
 * Turkish keeps lower case inside a title (TDK: "ve, ile, ya, veya, de, da, ki" and "mı/mi/mu/mü").
 * A heading that is a sentence or an instruction ("Bu bölüm açılamadı") is not passed through this.
 *
 * Only a first letter is ever raised, never lowered: "MAT.7.1.1", "UTC+3" and "TEDY" stay as
 * written, and the rest of each word is untouched ("Türkiye'nin" keeps its suffix). Letters go
 * through the Turkish locale, so "i" becomes "İ", not "I".
 *
 * The module template carries the same rule in JavaScript (`basliga` in module-template.html);
 * `tests/baslik.test.ts` and `tests/test_modul_baslik_duzeni.py` pin that the two agree.
 */
const KUCUK_KALIR = new Set(['ve', 'ile', 'ya', 'veya', 'de', 'da', 'ki', 'mı', 'mi', 'mu', 'mü'])

const HARF = /\p{L}/u

export function basliga(metin: string): string {
  let ilk = true
  return metin.split(/(\s+)/).map(parca => {
    if (!parca || /^\s+$/.test(parca)) return parca
    const cekirdek = parca.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '').toLocaleLowerCase('tr')
    const buyut = ilk || !KUCUK_KALIR.has(cekirdek)
    ilk = false
    if (!buyut) return parca
    const i = parca.search(HARF)
    if (i < 0) return parca
    const harf = parca[i]
    return harf === harf.toLocaleLowerCase('tr')
      ? parca.slice(0, i) + harf.toLocaleUpperCase('tr') + parca.slice(i + 1)
      : parca
  }).join('')
}
