import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'

/** Only overflowing content belongs in the keyboard's scrolling order. */
function useKaydirmaOdagi<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const olc = () => {
      el.tabIndex = el.scrollWidth > el.clientWidth ? 0 : -1
    }
    const boyut = new ResizeObserver(olc)
    const izle = () => {
      boyut.disconnect()
      boyut.observe(el)
      for (const child of el.children) boyut.observe(child)
      olc()
    }
    const icerik = new MutationObserver(izle)
    icerik.observe(el, { childList: true, subtree: true, characterData: true })
    izle()
    return () => { boyut.disconnect(); icerik.disconnect() }
  }, [])
  return ref
}

export default function Kaydirilabilir({ children, className, satirIci = false, etiket }: {
  children: ReactNode; className: string; satirIci?: boolean; etiket?: string
}) {
  const ref = useKaydirmaOdagi<HTMLDivElement & HTMLSpanElement>()
  const Kap = satirIci ? 'span' : 'div'
  return <Kap ref={ref} className={className} role={etiket ? 'region' : undefined}
    aria-label={etiket}>{children}</Kap>
}
