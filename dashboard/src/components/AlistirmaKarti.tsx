import { useId, useRef, useState } from 'react'
import { Button, RadioButton, RadioButtonGroup, TextInput } from '@carbon/react'
import './AlistirmaKarti.scss'

export interface Alistirma {
  id: string
  baslik: string
  ders: string
  konu: string
  kazanim_kodu: string | null
  zorluk: 'kolay' | 'orta' | 'zor'
  sorular: {
    tur: 'coktan_secmeli' | 'dogru_yanlis' | 'kisa_cevap'
    soru: string
    secenekler?: string[]
  }[]
}

interface Sonuc {
  dogru: boolean
  aciklama: string
  yanlis_analizi?: { baslik: string }
}

export default function AlistirmaKarti({ alistirma, saltOkunur = false, disabled = false, onYanlislar }: {
  alistirma: Alistirma
  saltOkunur?: boolean
  disabled?: boolean
  onYanlislar: (metin: string) => void
}) {
  const id = useId()
  const [sira, setSira] = useState(0)
  const [cevap, setCevap] = useState('')
  const [sonuclar, setSonuclar] = useState<Sonuc[]>([])
  const [bekliyor, setBekliyor] = useState(false)
  const [hata, setHata] = useState('')
  const gonderiliyor = useRef(false)
  const tamam = sonuclar.length === alistirma.sorular.length
  const soru = alistirma.sorular[sira]
  const sonuc = sonuclar[sira]
  const kapali = saltOkunur || disabled || bekliyor || Boolean(sonuc)

  async function gonder() {
    if (kapali || gonderiliyor.current || !cevap.trim()) return
    gonderiliyor.current = true
    setBekliyor(true)
    setHata('')
    try {
      const response = await fetch(`/api/assistant/alistirmalar/${alistirma.id}/cevap`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sira: sira + 1, cevap }),
      })
      if (!response.ok) {
        setHata(response.status === 403 ? 'Bu sohbet salt okunur.' : response.status === 404 ? 'Alıştırma bulunamadı.' : 'Cevap alınamadı.')
        return
      }
      const veri: Sonuc = await response.json()
      if (typeof veri.dogru !== 'boolean' || typeof veri.aciklama !== 'string') {
        setHata('Cevap alınamadı.')
        return
      }
      setSonuclar(onceki => [...onceki, veri])
    } catch {
      setHata('Cevap alınamadı.')
    } finally {
      gonderiliyor.current = false
      setBekliyor(false)
    }
  }

  function sonraki() {
    setSira(sira + 1)
    setCevap('')
    setHata('')
  }

  const yanlislar = alistirma.sorular.filter((_, i) => sonuclar[i] && !sonuclar[i].dogru)
  return <section className="ac-alistirma" aria-labelledby={`${id}-baslik`}>
    <h3 id={`${id}-baslik`}>{alistirma.baslik}</h3>
    {saltOkunur && <p>Bu sohbet salt okunur.</p>}
    {soru && <>
      <p className="ac-alistirma__sira">Soru {sira + 1}/{alistirma.sorular.length}</p>
      <p id={`${id}-soru`} className="ac-alistirma__soru">{soru.soru}</p>
      <form onSubmit={event => { event.preventDefault(); void gonder() }}>
        {soru.tur === 'coktan_secmeli' && soru.secenekler
          ? <RadioButtonGroup name={`${id}-secenek`} legendText="Cevabın" valueSelected={cevap}
            disabled={kapali} onChange={value => setCevap(String(value ?? ''))}>
            {soru.secenekler.map((secenek, i) => <RadioButton key={i}
              id={`${id}-secenek-${i}`} value={secenek} labelText={secenek} />)}
          </RadioButtonGroup>
          : <TextInput id={`${id}-cevap`} labelText="Cevabın" value={cevap}
            aria-describedby={`${id}-soru`} disabled={kapali}
            onChange={event => setCevap(event.target.value)} />}
        {!sonuc && <Button type="submit" disabled={kapali || !cevap.trim()}>
          {bekliyor ? 'Cevap gönderiliyor' : 'Cevabı gönder'}
        </Button>}
      </form>
      {hata && <p role="alert">{hata}</p>}
      {sonuc && <div className="ac-alistirma__sonuc" role="status">
        <p><strong>{sonuc.dogru ? 'Doğru' : 'Yanlış'}</strong></p>
        {!sonuc.dogru && sonuc.yanlis_analizi?.baslik && <p>{sonuc.yanlis_analizi.baslik}</p>}
        <p>{sonuc.aciklama}</p>
      </div>}
      {sonuc && !tamam && <Button kind="tertiary" onClick={sonraki}>Sonraki soru</Button>}
    </>}
    {tamam && <div className="ac-alistirma__puan" aria-live="polite">
      <p><strong>Puan</strong> · {sonuclar.filter(s => s.dogru).length}/{alistirma.sorular.length}</p>
      {yanlislar.length > 0 && <Button kind="tertiary" disabled={saltOkunur || disabled}
        onClick={() => onYanlislar(yanlislar.map(s => s.soru).join('\n'))}>Yanlışlarımı anlat</Button>}
    </div>}
  </section>
}
