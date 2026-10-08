/** Taşan formül ve tablolar klavyeyle kaydırılabilsin, taşmayanlar sekme sırasına girmesin
 *  (eski Kaydirilabilir bileşeninin kuralı; axe scrollable-region-focusable). Carbon eklenti çıktısını
 *  light DOM'a koyduğu için kökteki MutationObserver bu öğeleri görür. */
const SECICI = '.ac-formul--blok, .ac-md__table-wrap, cds-aichat-table, table'

export function kaydirmaOdaginiYonet(kok: HTMLElement): () => void {
  const ayarla = () => {
    kok.querySelectorAll<HTMLElement>(SECICI).forEach(el => {
      const tasiyor = el.scrollWidth > el.clientWidth + 1
      if (tasiyor && !el.hasAttribute('tabindex')) {
        el.setAttribute('tabindex', '0'); el.setAttribute('role', 'region')
        el.setAttribute('aria-label', el.classList.contains('ac-formul--blok') ? 'Formül' : 'Tablo')
      } else if (!tasiyor && el.getAttribute('tabindex') === '0') {
        el.removeAttribute('tabindex'); el.removeAttribute('role'); el.removeAttribute('aria-label')
      }
    })
  }
  const gozlem = new MutationObserver(() => requestAnimationFrame(ayarla))
  gozlem.observe(kok, { childList: true, subtree: true })
  const boyut = new ResizeObserver(ayarla)
  boyut.observe(kok)
  ayarla()
  return () => { gozlem.disconnect(); boyut.disconnect() }
}
