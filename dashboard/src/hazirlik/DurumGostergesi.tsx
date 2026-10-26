import { CheckmarkFilled, InformationFilled } from '@carbon/icons-react'
import { durumEtiketi } from './hazirlik'
import type { SinavDurumu } from './tipler'
import './DurumGostergesi.scss'

/** Kanun K4, talimatname §5.7: ikon + metin (+ renk). Yeşil kesin, mavi olası; ülke geneli ve geçti eylem istemez,
 *  düz gri metin. Tag değil: Tag'in mavisi derslere ayrılmış (§4.4.2). Metin durumu söylediği için ikon gizlidir. */
export default function DurumGostergesi({ durum }: { durum: SinavDurumu }) {
  const metin = durumEtiketi(durum)
  if (durum.tur === 'kesin') {
    return <span className="hazirlik-durum hazirlik-durum--kesin"><CheckmarkFilled size={16} aria-hidden="true" className="hazirlik-durum__ikon" />{metin}</span>
  }
  if (durum.tur === 'olasi') {
    return <span className="hazirlik-durum hazirlik-durum--olasi"><InformationFilled size={16} aria-hidden="true" className="hazirlik-durum__ikon" />{metin}</span>
  }
  return <span className="hazirlik-durum hazirlik-durum--notr">{metin}</span>
}
