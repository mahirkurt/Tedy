import type { MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { uygulamaIcindeAc } from '../utils/gezinme'

/** Uygulama içi bir adresin tıklama işleyicisi: düz sol tık yerinde açılır (react-router); yeni sekme/pencere
 *  (Ctrl/Cmd/Shift/Alt, orta tık), `target` ve uygulama dışı adresler tarayıcıya kalır (C13). `IcBaglanti` ve
 *  bağlantı olarak çizilen düğmeler (`<Button href>`) ortak kullanır. */
export function useIcGezinme(href: string | null) {
  const gezin = useNavigate()
  return (e: MouseEvent<HTMLElement>) => {
    if (!href || !uygulamaIcindeAc(e, href, e.currentTarget.getAttribute('target'))) return
    e.preventDefault()
    gezin(href)
  }
}
