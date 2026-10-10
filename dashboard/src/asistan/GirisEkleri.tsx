import { Button, IconButton, InlineLoading } from '@carbon/react'
import { Close } from '@carbon/icons-react'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { cipKaldir, odeveBagla } from './ekler.ts'

const TUR: Record<string, string> = { gorsel: 'Görsel', pdf: 'PDF', docx: 'Word', txt: 'Metin' }

/** Gönderilmeyi bekleyen ekler (yalnız varken çizilir; boşken giriş üstünde yer kaplamaz). Belge, seçili ödeve
 *  ("Ödeve bağla" eylemi) bağlanabilir. Salt okunur sohbette tek cümle. */
export default function GirisEkleri() {
  const cipler = useAsistanDurumu(d => d.cipler)
  const odevKey = useAsistanDurumu(d => d.odevKey)
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  if (salt) return <p className="asistan__salt-notu">Bu sohbet salt okunur.</p>
  if (!cipler.length) return null
  return <ul className="asistan__ekler" aria-label="Eklenecek dosyalar">{cipler.map(c => <li key={c.yerel} className="asistan__ek">
    {c.id && c.tur === 'gorsel' && <img className="asistan__ek-onizleme" src={`/api/assistant/uploads/${c.id}`} alt="Yüklenen görsel" />}
    <span className="asistan__ek-ad">{c.ad}</span>
    {c.tur && TUR[c.tur] ? <span className="asistan__ek-tur">{TUR[c.tur]}</span> : null}
    {c.yukleniyor ? <InlineLoading className="asistan__ek-yukleniyor" description="Yükleniyor…" iconDescription="Yükleniyor" /> : null}
    {c.id && c.tur !== 'gorsel' && <Button kind="ghost" size="lg" disabled={yukleniyor || !odevKey || c.baglaniyor || c.baglandi}
      onClick={() => void odeveBagla(c.yerel)}>{c.baglandi ? 'Ödeve bağlandı' : c.baglaniyor ? 'Bağlanıyor…' : 'Bu ödeve bağla'}</Button>}
    {c.hata ? <p role="alert" className="asistan__ek-hata">{c.hata}</p> : null}
    <IconButton kind="ghost" size="lg" align="top-end" label={`Kaldır: ${c.ad}`} disabled={yukleniyor}
      onClick={() => cipKaldir(c.yerel)}><Close /></IconButton>
  </li>)}</ul>
}
