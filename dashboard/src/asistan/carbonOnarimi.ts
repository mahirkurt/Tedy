// Carbon AI Chat 1.22.0'ın atıf düğmesi ("Kaynaklar", conversational_search) iki erişilebilirlik kusuruyla gelir:
// aria-expanded rolsüz dış öğede durur (IBM aria_attribute_valid) ve ok ikonu etiketsizdir (svg_graphics_labelled).
// Görünüm Carbon'un kalır; durum, düğme rolündeki iç öğeye taşınır, ikon yardımcı teknolojiden gizlenir.
const ETIKET = 'cds-operational-tag'

type Guncellenen = Element & { updateComplete?: Promise<unknown> }

/** `kalan`: iç düğme henüz yoksa öğenin güncellemesi beklenip en çok bu kadar yeniden denenir. Bitmiş bir Lit
 *  öğesinin updateComplete'i hep çözülmüş gelir; sınırsız deneme sekmeyi donduran bir mikro görev döngüsüdür. */
export function onar(kok: ParentNode, kalan = 3): void {
  for (const etiket of kok.querySelectorAll<Guncellenen>(`${ETIKET}[aria-expanded]`)) {
    const dugme = etiket.shadowRoot?.querySelector('[role="button"]')
    if (!dugme) { if (kalan > 0) void etiket.updateComplete?.then(() => onar(kok, kalan - 1)); continue }
    dugme.setAttribute('aria-expanded', etiket.getAttribute('aria-expanded') ?? 'false')
    etiket.removeAttribute('aria-expanded')
  }
  for (const svg of kok.querySelectorAll(`${ETIKET} svg:not([aria-hidden])`)) svg.setAttribute('aria-hidden', 'true')
}

/** Telefonda dokunma hedefi (D3b, ≥ 44 px; B79): Carbon AI Chat'in kendi düğmeleri (gönder 32 px, başlık eylemleri
 *  40 px) gölge köklerde ve `::part` vermez (ölçüldü 2026-10-10, 1.22.0). Boylarını Carbon'un kendi yoğunluk
 *  değişkeni belirler: `.cds--btn` yüksekliği `clamp(max(var(--cds-layout-size-height-min), …), …)`; değişken
 *  `:host(cds-button)` / `:host(cds-icon-button)` içinde 0 px tanımlıdır, belgeden miras geçmez. Düğmeyi içeren
 *  gölge köke eklenen kural host'u dışarıdan hedefler ve `:host` kuralını yener; yalnız telefonda 3rem (48 px). */
export const DOKUNMA_KURALI = '@media (max-width: 671px) { cds-button, cds-icon-button { --cds-layout-size-height-min: 3rem; } }'

/** 4K (B28): `ted-theme.scss`'in ikon kuralı (`<svg width="16">` → 1rem) gölge köke ulaşmaz; Carbon AI Chat'in
 *  ikonları 3840 px'te 16 px kalıyordu. Aynı kural her gölge köke eklenir: sıfır özgüllük (`:where`), bileşenin
 *  kendi ikon boyu yine kazanır; kök yazı 16 px iken (≤ 1920 px) hiçbir şey değişmez. */
export const IKON_KURALI = [10, 12, 14, 16, 18, 20, 24, 32, 36]
  .map(n => `:where(svg[width='${n}'][height='${n}']) { width: ${n / 16}rem; height: ${n / 16}rem; }`).join('\n')

/** Azaltılmış hareket (B28'in görünüm kipi kısmı, K13): `ted-theme.scss`'in kuralı gölge köke ulaşmaz; sohbetin
 *  kendi geçişleri ve animasyonları da okurun tercihine uyar. Temanın kuralıyla aynı: süre 0 (`none` değil — giriş
 *  animasyonuyla görünür olan öğe bitiş durumunda kalsın). */
export const HAREKET_KURALI = '@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0s !important; animation-iteration-count: 1 !important; transition-duration: 0s !important; } }'

let dokunmaSayfasi: CSSStyleSheet | null = null
function dokunmaKurali(): CSSStyleSheet | null {
  if (dokunmaSayfasi) return dokunmaSayfasi
  try { dokunmaSayfasi = new CSSStyleSheet(); dokunmaSayfasi.replaceSync(`${DOKUNMA_KURALI}\n${IKON_KURALI}\n${HAREKET_KURALI}`) } catch { dokunmaSayfasi = null }
  return dokunmaSayfasi
}

/** Gölge kökün ve altındaki her gölge kökün stil sayfalarına kuralı bir kez ekler; eklenen kökleri döndürür. */
export function dokunmaHedefiniUygula(kok: ShadowRoot, gorulen: WeakSet<ShadowRoot>, kural: CSSStyleSheet | null = dokunmaKurali()): ShadowRoot[] {
  const yeni: ShadowRoot[] = []
  const gez = (k: ShadowRoot) => {
    if (!gorulen.has(k)) {
      gorulen.add(k)
      if (kural && !k.adoptedStyleSheets.includes(kural)) k.adoptedStyleSheets = [...k.adoptedStyleSheets, kural]
      yeni.push(k)
    }
    for (const el of k.querySelectorAll('*')) { const ic = (el as Element).shadowRoot; if (ic) gez(ic) }
  }
  gez(kok)
  return yeni
}

/** Kapsayıcıdaki sohbet öğesinin gölge kökünü izler; React her yeniden çizimde özniteliği geri koyarsa yine taşır.
 *  İç içe gölge kökler de izlenir: yeni çizilen Carbon düğmeleri dokunma kuralını alır. */
export function carbonErisilebilirlikOnarimi(kapsayici: Element): () => void {
  let izleyici: MutationObserver | null = null
  const icIzleyiciler: MutationObserver[] = []
  const gorulen = new WeakSet<ShadowRoot>()
  let bekleyen = 0
  const dokunma = (kok: ShadowRoot) => {
    for (const k of dokunmaHedefiniUygula(kok, gorulen)) {
      if (k === kok) continue
      const iz = new MutationObserver(() => planla(kok))
      iz.observe(k, { subtree: true, childList: true })
      icIzleyiciler.push(iz)
    }
  }
  // Lit öğeleri gölge köklerini bağlandıktan sonra çizer: tarama bir kare sonraya da planlanır.
  const planla = (kok: ShadowRoot) => {
    if (bekleyen) return
    bekleyen = requestAnimationFrame(() => { bekleyen = 0; dokunma(kok) })
  }
  const bagla = () => {
    const kok = kapsayici.querySelector('cds-aichat-react')?.shadowRoot
    if (!kok || izleyici) return
    izleyici = new MutationObserver(() => { onar(kok); planla(kok) })
    izleyici.observe(kok, { subtree: true, childList: true, attributes: true, attributeFilter: ['aria-expanded'] })
    onar(kok)
    dokunma(kok)
    planla(kok)
  }
  const dis = new MutationObserver(bagla)
  dis.observe(kapsayici, { subtree: true, childList: true })
  bagla()
  return () => {
    dis.disconnect(); izleyici?.disconnect(); icIzleyiciler.forEach(i => i.disconnect())
    if (bekleyen) cancelAnimationFrame(bekleyen)
  }
}
