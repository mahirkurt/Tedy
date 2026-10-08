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

/** Kapsayıcıdaki sohbet öğesinin gölge kökünü izler; React her yeniden çizimde özniteliği geri koyarsa yine taşır. */
export function carbonErisilebilirlikOnarimi(kapsayici: Element): () => void {
  let izleyici: MutationObserver | null = null
  const bagla = () => {
    const kok = kapsayici.querySelector('cds-aichat-react')?.shadowRoot
    if (!kok || izleyici) return
    izleyici = new MutationObserver(() => onar(kok))
    izleyici.observe(kok, { subtree: true, childList: true, attributes: true, attributeFilter: ['aria-expanded'] })
    onar(kok)
  }
  const dis = new MutationObserver(bagla)
  dis.observe(kapsayici, { subtree: true, childList: true })
  bagla()
  return () => { dis.disconnect(); izleyici?.disconnect() }
}
