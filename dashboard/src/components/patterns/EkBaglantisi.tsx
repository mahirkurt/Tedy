import { Document, Launch } from '@carbon/icons-react'
import type { PortalEki } from '../../types'
import './EkBaglantisi.scss'

// What to say when TEDY holds no copy. A plain link (a video, a folder) is not
// a failed download and says nothing (docs/frontend-design-principles.md D3:
// no silent failure — and no false alarm either).
const DURUM_SOZU: Record<string, string> = {
  bekliyor: 'Henüz indirilmedi — kaynağında aç',
  erisilemedi: 'İndirilemedi — kaynağında aç',
  cok_buyuk: 'İndirilemedi (çok büyük) — kaynağında aç',
  hata: 'İndirilemedi — kaynağında aç',
}

/**
 * One portal attachment. With a TEDY copy the name opens it and the original
 * stays one quiet step away ("Kaynağında aç"); without one the name opens the
 * original and the line says why there is no copy.
 */
export function EkBaglantisi({ ek }: { ek: PortalEki }) {
  if (ek.tedyUrl) {
    return (
      <span className="tedy-ek">
        <a className="tedy-ek__ana" href={ek.tedyUrl} target="_blank" rel="noopener">
          <Document size={16} aria-hidden="true" /> {ek.name}
        </a>
        <a
          className="tedy-ek__kaynak"
          href={ek.url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Kaynağında aç: ${ek.name}`}
        >
          Kaynağında aç
        </a>
      </span>
    )
  }
  const soz = ek.status && ek.status !== 'baglanti'
    ? (DURUM_SOZU[ek.status] ?? DURUM_SOZU.hata)
    : null
  return (
    <span className="tedy-ek">
      <a className="tedy-ek__ana" href={ek.url} target="_blank" rel="noopener noreferrer">
        {ek.status === 'baglanti' ? <Launch size={16} aria-hidden="true" /> : <Document size={16} aria-hidden="true" />}
        {' '}{ek.name}
      </a>
      {soz && <span className="tedy-ek__durum">{soz}</span>}
    </span>
  )
}
