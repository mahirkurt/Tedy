import { useId, useState } from 'react'
import { Button, TextArea, TextInput } from '@carbon/react'

export interface OdevOnerisi {
  ek_id: string
  photo_hash?: string
  adaylar: { ders: string; baslik: string; teslim: string; aciklama: string; eksik: string[] }[]
}

/** Extraction never writes a homework row; this explicit action confirms edited fields. */
export default function OdevOnayKarti({ oneri, saltOkunur = false }: { oneri: OdevOnerisi; saltOkunur?: boolean }) {
  const id = useId()
  const [adaylar, setAdaylar] = useState(oneri.adaylar)
  const [bekliyor, setBekliyor] = useState(false)
  const [sonuc, setSonuc] = useState<number | null>(null)
  const [hata, setHata] = useState<string | null>(null)
  function degistir(index: number, alan: 'ders' | 'baslik' | 'teslim' | 'aciklama', value: string) {
    setAdaylar(prev => prev.map((a, i) => i === index ? { ...a, [alan]: value } : a))
  }
  async function kaydet() {
    if (bekliyor || sonuc !== null || saltOkunur) return
    setBekliyor(true); setHata(null)
    const body = new FormData()
    body.append('stage', 'commit')
    body.append('source_type', 'ted')
    body.append('photo_hash', oneri.photo_hash || '')
    body.append('homework', JSON.stringify(adaylar.map(a => ({
      'Ders Adı': a.ders.trim(), 'Ödev Başlığı': a.baslik.trim(),
      'Ödev Son Teslim Tarihi': a.teslim.trim(), detail: { description: a.aciklama.trim() },
      eksik_birakilan: a.teslim.trim() ? [] : ['teslim'],
    }))))
    try {
      const res = await fetch('/api/homework/photo', { method: 'POST', credentials: 'include', body })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Ödev eklenemedi.')
      const eklenen = Number(data.added_count || 0)
      if (!eklenen) { setHata('Bu iş zaten listede. Yeni bir şey eklenmedi.'); return }
      setSonuc(eklenen)
      window.dispatchEvent(new CustomEvent('tedy:homework-updated'))
    } catch (e) { setHata(e instanceof Error ? e.message : 'Ödev eklenemedi.') }
    finally { setBekliyor(false) }
  }
  return <section className="ac-odev-onayi" aria-label="Ödev önerisi">
    <h3>Ödevleri kontrol et</h3>
    {sonuc === null ? <>
      {adaylar.map((a, index) => <fieldset key={index} disabled={bekliyor || saltOkunur}>
        <legend>Ödev {index + 1}</legend>
        <TextInput id={`${id}-${index}-ders`} labelText="Ders" value={a.ders}
          onChange={e => degistir(index, 'ders', e.target.value)} />
        <TextInput id={`${id}-${index}-baslik`} labelText="Başlık" value={a.baslik}
          onChange={e => degistir(index, 'baslik', e.target.value)} />
        <TextInput id={`${id}-${index}-teslim`} labelText="Teslim" placeholder="gg.aa.yyyy"
          helperText="Fotoğrafta yoksa boş bırakabilirsin." value={a.teslim}
          onChange={e => degistir(index, 'teslim', e.target.value)} />
        <TextArea id={`${id}-${index}-aciklama`} labelText="Açıklama" rows={2} value={a.aciklama}
          onChange={e => degistir(index, 'aciklama', e.target.value)} />
      </fieldset>)}
      {hata && <p role="alert">{hata}</p>}
      <Button size="sm" disabled={bekliyor || saltOkunur || !adaylar.length || adaylar.some(a => !a.baslik.trim() || !a.ders.trim())}
        onClick={() => void kaydet()}>{bekliyor ? 'Ekleniyor…' : 'Ödevlere ekle'}</Button>
    </> : <p role="status">{sonuc} ödev eklendi</p>}
  </section>
}
