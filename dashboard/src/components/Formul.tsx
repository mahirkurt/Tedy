import { useEffect, useRef, useState } from 'react'
import Kaydirilabilir from './Kaydirilabilir'

type Katex = typeof import('katex')
let yukleniyor: Promise<Katex> | null = null

function katexYukle(): Promise<Katex> {
  // Math and its fonts stay out of the initial page bundle.
  yukleniyor ??= Promise.all([import('katex'), import('katex/dist/katex.min.css')])
    .then(([modul]) => modul)
  return yukleniyor
}

function Cizim({ tex, blok }: { tex: string; blok: boolean }) {
  const ref = useRef<HTMLSpanElement>(null)
  const [cizildi, setCizildi] = useState(false)

  useEffect(() => {
    let iptal = false
    katexYukle().then(katex => {
      if (iptal || !ref.current) return
      try {
        katex.render(tex, ref.current, {
          displayMode: blok, throwOnError: true, output: 'htmlAndMathml',
          trust: false, strict: 'ignore', maxSize: 10, maxExpand: 100,
        })
        setCizildi(true)
      } catch {
        ref.current.replaceChildren()
        setCizildi(false)
      }
    }).catch(() => {
      if (!iptal) setCizildi(false)
    })
    return () => { iptal = true }
  }, [tex, blok])

  return (
    <Kaydirilabilir satirIci={!blok} className={`ac-formul${blok ? ' ac-formul--blok' : ''}`}>
      <span ref={ref} />
      {!cizildi && <code className="ac-formul__kaynak">{tex}</code>}
    </Kaydirilabilir>
  )
}

export default function Formul({ tex, blok }: { tex: string; blok: boolean }) {
  // A streaming update must never display the preceding formula as its result.
  return <Cizim key={`${blok}:${tex}`} tex={tex} blok={blok} />
}
