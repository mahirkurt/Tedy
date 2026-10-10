import { Fragment } from 'react'
import { rakamParcala } from '../../utils/bugun'
import './patterns.scss'

/**
 * A sentence whose figures are set in Plex Mono with tabular digits and whose
 * words stay in Plex Sans (`.tedy-time` wraps only the figure — talimatname
 * [3.3-5], debt B36). Only for strings the page composes ("Sonra: Fen 11:20",
 * "4 ders kaldı"); a title's "2. HAFTA" is a name, not a figure.
 */
export function Rakamli({ metin }: { metin: string }) {
  return (
    <>
      {rakamParcala(metin).map((p, i) => p.rakam
        ? <span key={i} className="tedy-time">{p.metin}</span>
        : <Fragment key={i}>{p.metin}</Fragment>)}
    </>
  )
}
