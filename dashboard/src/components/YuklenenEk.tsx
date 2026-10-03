import { useId, useState } from 'react'
import { Button, Select, SelectItem } from '@carbon/react'
import type { HomeworkItem } from '../types'

export interface Yukleme { id: string; ad: string; tur: string }

export default function YuklenenEk({ ek, odevler, saltOkunur, disabled }: {
  ek: Yukleme; odevler: HomeworkItem[]; saltOkunur: boolean; disabled: boolean
}) {
  const id = useId()
  const [acik, setAcik] = useState(false)
  const [anahtar, setAnahtar] = useState('')
  const [durum, setDurum] = useState<'hazir' | 'bekliyor' | 'baglandi'>('hazir')
  const [hata, setHata] = useState('')
  async function bagla() {
    if (!anahtar || disabled || saltOkunur || durum !== 'hazir') return
    setDurum('bekliyor'); setHata('')
    try {
      const res = await fetch(`/api/assistant/uploads/${ek.id}/odeve-bagla`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anahtar }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Belge ödeve bağlanamadı.')
      setDurum('baglandi'); setAcik(false)
      window.dispatchEvent(new CustomEvent('tedy:homework-updated'))
    } catch (e) { setHata(e instanceof Error ? e.message : 'Belge ödeve bağlanamadı.'); setDurum('hazir') }
  }
  return <div className="ac-yuklenen-ek">
    <a href={`/api/assistant/uploads/${ek.id}`} target="_blank" rel="noreferrer">
      {ek.tur === 'gorsel' && <img src={`/api/assistant/uploads/${ek.id}`} alt="Yüklenen görsel" />}{ek.ad}
    </a>
    {!saltOkunur && ek.tur !== 'gorsel' && ek.tur !== 'bilinmiyor' && <Button kind="ghost" size="sm"
      disabled={disabled || durum !== 'hazir'} onClick={() => setAcik(!acik)} aria-expanded={acik}>
      {durum === 'baglandi' ? 'Ödeve bağlandı' : durum === 'bekliyor' ? 'Bağlanıyor…' : 'Bu ödeve bağla'}
    </Button>}
    {acik && <>
      <Select id={`${id}-odev`} labelText="Belgenin ödevi" value={anahtar} disabled={durum === 'bekliyor'}
        onChange={e => setAnahtar(e.target.value)}>
        <SelectItem value="" text="Ödev seç" />
        {odevler.map(hw => <SelectItem key={hw.homework_key} value={hw.homework_key!}
          text={`${hw.normalized_course || hw['Ders Adı']} — ${hw['Ödev Başlığı']}`} />)}
      </Select>
      <Button size="sm" disabled={!anahtar || durum !== 'hazir' || disabled} onClick={() => void bagla()}>Bağla</Button>
    </>}
    {hata && <p role="alert">{hata}</p>}
  </div>
}
