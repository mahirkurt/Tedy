import { Dropdown } from '@carbon/react'
import type { Ogretmen } from '../types'
import type { SubjectFamily } from '../theme/subjects'
import SubjectLabel from '../components/SubjectLabel'
import { GENEL } from '../hooks/useOgretmen'
import { useAsistanDurumu } from './asistanDeposu.ts'

interface Secenek { id: string; ad: string; aile: SubjectFamily | null }

/** Kimlik: odak ve testler seçimi bu düğmeden bulur (ogretmenSec seçimden sonra odağı buraya verir). */
export const OGRETMEN_SECIMI_ID = 'asistan-ogretmen'

// Carbon'un ok simgesinin adı İngilizce varsayılandı ("Open menu"); okura Türkçesi gider (D4).
const CEVIRI: Record<string, string> = { 'open.menu': 'Listeyi aç', 'close.menu': 'Listeyi kapat' }
const cevir = (id: string) => CEVIRI[id] ?? id

const Ad = ({ s }: { s: Secenek }) => (s.aile ? <SubjectLabel course={null} family={s.aile}>{s.ad}</SubjectLabel> : <>{s.ad}</>)

/**
 * Öğretmen seçimi tek kontrol: Carbon Dropdown (lg, 48 px), satır içi etiket "Öğretmen"; seçenekler ders işaretiyle
 * (SubjectLabel — renk tek başına taşımaz, ad yanındadır, İ8). Sohbet başlığının altındaki satırda durur
 * (HEADER_BOTTOM_ELEMENT); telefonda tek satır.
 */
export default function OgretmenSecimi({ liste, secili, onSec, hata }: {
  liste: Ogretmen[]; secili: string; onSec: (id: string) => void; hata?: string | null
}) {
  const kilitli = useAsistanDurumu(d => d.saltOkunur || d.yukleniyor)
  const secenekler: Secenek[] = [
    { id: GENEL, ad: 'Genel', aile: null },
    ...liste.map(o => ({ id: o.id, ad: o.kisa_ad, aile: o.renk_ailesi })),
  ]
  const seciliOge = secenekler.find(s => s.id === secili) ?? secenekler[0]
  return <div className="asistan__ogretmen">
    <Dropdown<Secenek> id={OGRETMEN_SECIMI_ID} type="inline" size="lg" titleText="Öğretmen" label="Öğretmen seç"
      items={secenekler} selectedItem={seciliOge} itemToString={s => s?.ad ?? ''}
      itemToElement={s => <Ad s={s} />} renderSelectedItem={s => <Ad s={s} />}
      translateWithId={cevir} readOnly={kilitli} onChange={({ selectedItem }) => { if (selectedItem && selectedItem.id !== secili) onSec(selectedItem.id) }} />
    {hata && <p className="asistan__ogretmen-hata" role="status">{hata}</p>}
  </div>
}
