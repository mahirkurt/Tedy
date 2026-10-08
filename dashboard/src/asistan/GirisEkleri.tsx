import { Button, Select, SelectItem } from '@carbon/react'
import { Close } from '@carbon/icons-react'
import YuklemeAlani from '../components/YuklemeAlani'
import { useApi } from '../hooks/useApi'
import type { HomeworkItem } from '../types'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { cipKaldir, dosyalariEkle, odeveBagla } from './ekler.ts'
import { acikOdevler } from './odevler.ts'

const TUR: Record<string, string> = { gorsel: 'Görsel', pdf: 'PDF', docx: 'Word', txt: 'Metin' }

export default function GirisEkleri() {
  const cipler = useAsistanDurumu(d => d.cipler)
  const odevKey = useAsistanDurumu(d => d.odevKey)
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const { data } = useApi<{ homework: HomeworkItem[] }>('/api/homework', { homework: [] })
  if (salt) return <p className="ac__aile-notu">Bu sohbet salt okunur.</p>
  return <div className="asistan__giris-ekleri">
    {cipler.length > 0 && <ul className="ac__ekler">{cipler.map(c => <li key={c.yerel} className="ac__ek">
      {c.id && c.tur === 'gorsel' && <img className="ac__ek-onizleme" src={`/api/assistant/uploads/${c.id}`} alt="Yüklenen görsel" />}
      <span>{c.ad}</span>{c.tur && TUR[c.tur] ? <span>{TUR[c.tur]}</span> : null}{c.yukleniyor ? <span>Yükleniyor</span> : null}
      {c.id && c.tur !== 'gorsel' && <Button kind="ghost" size="sm" disabled={yukleniyor || !odevKey || c.baglaniyor || c.baglandi}
        onClick={() => void odeveBagla(c.yerel)}>{c.baglandi ? 'Ödeve bağlandı' : c.baglaniyor ? 'Bağlanıyor…' : 'Bu ödeve bağla'}</Button>}
      {c.hata ? <p role="alert" className="ac__ek-hata">{c.hata}</p> : null}
      <button type="button" className="ac__ek-kaldir" aria-label={`Kaldır: ${c.ad}`} disabled={yukleniyor}
        onClick={() => cipKaldir(c.yerel)}><Close size={16} aria-hidden /></button>
    </li>)}</ul>}
    <div className="asistan__giris-satir">
      <YuklemeAlani onDosyalar={dosyalariEkle} disabled={yukleniyor} />
      <Select id="ac-odev" className="ac__odev" labelText="Ödev" value={odevKey} disabled={yukleniyor}
        onChange={e => asistanDeposu.ayarla({ odevKey: e.target.value })}>
        <SelectItem value="" text="Seçilmedi — genel soru" />
        {acikOdevler(data.homework).map(hw => {
          const ad = `${hw.normalized_course || hw['Ders Adı']} — ${hw['Ödev Başlığı']}`
          return <SelectItem key={hw.homework_key} value={hw.homework_key || ''} text={ad.length > 80 ? `${ad.slice(0, 79)}…` : ad} />
        })}
      </Select>
    </div>
  </div>
}
