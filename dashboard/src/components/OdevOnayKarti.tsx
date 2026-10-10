import { useId, useState } from 'react'
import { AILabel, AILabelContent, Button, InlineLoading, TextArea, TextInput } from '@carbon/react'

export interface OdevOnerisi {
  ek_id: string
  photo_hash?: string
  adaylar: { ders: string; baslik: string; teslim: string; aciklama: string; eksik: string[] }[]
}

type Alan = 'ders' | 'baslik' | 'teslim' | 'aciklama'
const ALAN_ADI: Record<Alan, string> = { ders: 'Ders', baslik: 'Başlık', teslim: 'Teslim', aciklama: 'Açıklama' }

/** Alanın AI etiketi (§6.2, K6): alanı yapay zekâ fotoğraftan okudu; okur değiştirirse etiket "Yapay zekânın önerisine
 *  dön" düğmesine döner ve ilk değer geri gelir (Carbon'un revert kalıbı, B56). Değer boşsa (AI okuyamadı) etiket yok. */
function alanEtiketi(alan: Alan, oneri: string, deger: string, geriAl: () => void) {
  if (!oneri) return undefined
  return <AILabel kind="default" size="mini" aiText="AI" slugLabel="" aria-label={`${ALAN_ADI[alan]}: yapay zekâ hakkında bilgi`}
    revertActive={deger !== oneri} revertLabel="Yapay zekânın önerisine dön" onRevertClick={geriAl}>
    <AILabelContent>
      <p className="ac-odev-onayi__ai">Bu alanı yapay zekâ fotoğraftan okudu: “{oneri}”. Yanlışsa düzelt; kaydetmeden önce
        her alanı kontrol et.</p>
    </AILabelContent>
  </AILabel>
}

/** Extraction never writes a homework row; this explicit action confirms edited fields. Fields the model filled carry
 *  an AI label with revert (K6, B56). A read-only conversation shows the fields read-only and no save button; only the
 *  save in progress is a temporary state (B42). A missing required field is said on submit, not by a silent grey
 *  button (B56). */
export default function OdevOnayKarti({ oneri, saltOkunur = false }: { oneri: OdevOnerisi; saltOkunur?: boolean }) {
  const id = useId()
  const [adaylar, setAdaylar] = useState(oneri.adaylar)
  const [bekliyor, setBekliyor] = useState(false)
  const [denendi, setDenendi] = useState(false)
  const [sonuc, setSonuc] = useState<number | null>(null)
  const [hata, setHata] = useState<string | null>(null)
  function degistir(index: number, alan: Alan, value: string) {
    setAdaylar(prev => prev.map((a, i) => i === index ? { ...a, [alan]: value } : a))
  }
  const eksik = (a: { ders: string; baslik: string }) => !a.baslik.trim() || !a.ders.trim()
  async function kaydet() {
    if (bekliyor || sonuc !== null || saltOkunur) return
    setDenendi(true)
    if (!adaylar.length || adaylar.some(eksik)) return
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
  const alan = (index: number, ad: Alan) => {
    const a = adaylar[index]
    const ilk = oneri.adaylar[index]?.[ad] ?? ''
    const gerekli = ad === 'ders' || ad === 'baslik'
    const ortak = {
      id: `${id}-${index}-${ad}`, labelText: ALAN_ADI[ad], value: a[ad], readOnly: saltOkunur || bekliyor,
      decorator: alanEtiketi(ad, ilk, a[ad], () => degistir(index, ad, ilk)),
      invalid: gerekli && denendi && !a[ad].trim(), invalidText: `${ALAN_ADI[ad]} gerekli.`,
    }
    if (ad === 'aciklama') return <TextArea {...ortak} rows={2} onChange={e => degistir(index, ad, e.target.value)} />
    return <TextInput {...ortak} {...(ad === 'teslim' ? { helperText: 'Biçim gg.aa.yyyy (ör. 12.10.2026); fotoğrafta yoksa boş bırakabilirsin.' } : {})}
      onChange={e => degistir(index, ad, e.target.value)} />
  }
  return <section className="ac-odev-onayi" aria-label="Ödev önerisi">
    <h3>Ödevleri kontrol et</h3>
    {sonuc === null ? <>
      {adaylar.map((_, index) => <fieldset key={index}>
        <legend>Ödev {index + 1}</legend>
        {alan(index, 'ders')}
        {alan(index, 'baslik')}
        {alan(index, 'teslim')}
        {alan(index, 'aciklama')}
      </fieldset>)}
      {hata && <p role="alert">{hata}</p>}
      {saltOkunur ? null : bekliyor
        ? <InlineLoading description="Ekleniyor…" iconDescription="Ekleniyor" />
        : <Button kind="secondary" size="lg" onClick={() => void kaydet()}>Ödevlere ekle</Button>}
    </> : <p role="status">{sonuc} ödev eklendi</p>}
  </section>
}
