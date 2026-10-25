import { InlineNotification } from '@carbon/react'

/** Uyarı satırları (metinler `belge.hazirlikUyarilari`'ndan): ekranda InlineNotification, kâğıtta çerçeveli paragraf (K11). */
export default function Uyarilar({ metinler, kip }: { metinler: string[]; kip: 'ekran' | 'baski' }) {
  if (metinler.length === 0) return null
  if (kip === 'baski') return <>{metinler.map(m => <p key={m} className="kilavuz-uyari">{m}</p>)}</>
  return (
    <>
      {metinler.map(m => (
        <InlineNotification key={m} kind={m.startsWith('Kitap bölümleri henüz') ? 'info' : 'warning'} lowContrast
          hideCloseButton statusIconDescription={m.startsWith('Kitap bölümleri henüz') ? 'Bilgi' : 'Uyarı'} title={m} />
      ))}
    </>
  )
}
