import { useState } from 'react'
import { Button, InlineLoading, InlineNotification, SkeletonText, TimePicker } from '@carbon/react'
import { Time } from '@carbon/icons-react'
import { useOdakPenceresi } from '../hooks/useOdakPenceresi'
import {
  clockOf, pencereGecerli, pencereGovdesi, saattenDakika, type OdakPenceresi,
} from '../utils/bugun'

type Alan = 'okulBitisi' | 'odakSonu' | 'yatma'

const ALANLAR: { alan: Alan; id: string; etiket: string }[] = [
  { alan: 'okulBitisi', id: 'odak-son-zil', etiket: 'Son zil' },
  { alan: 'odakSonu', id: 'odak-pencere-sonu', etiket: 'Odak penceresinin sonu' },
  { alan: 'yatma', id: 'odak-yatma', etiket: 'Yatma saati' },
]

const BICIM_HATASI = 'Saati SS:DD biçiminde yaz (örneğin 15:45).'
const SIRA_HATASI = 'Saatler sırayla olmalı: son zil, odak penceresinin sonu, sonra yatma saati.'

/**
 * The household's focus window on Profil (anayasa §2, talimatname B29): the
 * window is a parameter kept in `output/`, so changing it is a setting, not a
 * rebuild. Bugün reads it for the card's voice ("Okuldan sonra", "Şimdi",
 * "Bu akşam") and for the Day Strip.
 */
export default function OdakPenceresiAyari() {
  const { pencere, loading, iskelet, refresh } = useOdakPenceresi()
  return (
    <div className="dashboard-card">
      <h2 className="dashboard-card__title" id="odak-penceresi-baslik">
        <Time size={20} />
        Odak penceresi
      </h2>
      {loading
        ? (iskelet ? <SkeletonText paragraph lineCount={3} /> : null)
        : <Form ilk={pencere} onKaydedildi={refresh} />}
    </div>
  )
}

function Form({ ilk, onKaydedildi }: { ilk: OdakPenceresi; onKaydedildi: () => void }) {
  const [degerler, setDegerler] = useState<Record<Alan, string>>({
    okulBitisi: clockOf(ilk.okulBitisi), odakSonu: clockOf(ilk.odakSonu), yatma: clockOf(ilk.yatma),
  })
  const [hatalar, setHatalar] = useState<Partial<Record<Alan, string>>>({})
  const [kaydediliyor, setKaydediliyor] = useState(false)
  const [sonuc, setSonuc] = useState<{ tur: 'basari' | 'hata'; metin: string } | null>(null)

  async function kaydet(e: React.FormEvent) {
    e.preventDefault()
    setSonuc(null)
    const dk: Partial<Record<Alan, number>> = {}
    const yeniHatalar: Partial<Record<Alan, string>> = {}
    for (const { alan } of ALANLAR) {
      const d = saattenDakika(degerler[alan])
      if (d === null) yeniHatalar[alan] = BICIM_HATASI
      else dk[alan] = d
    }
    if (Object.keys(yeniHatalar).length === 0) {
      const p = dk as OdakPenceresi
      if (!pencereGecerli(p)) yeniHatalar[p.okulBitisi > p.odakSonu ? 'odakSonu' : 'yatma'] = SIRA_HATASI
    }
    setHatalar(yeniHatalar)
    if (Object.keys(yeniHatalar).length) return

    setKaydediliyor(true)
    try {
      const res = await fetch('/api/odak-penceresi', {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pencereGovdesi(dk as OdakPenceresi)),
      })
      if (!res.ok) throw new Error('kaydedilemedi')
      onKaydedildi()
      setSonuc({ tur: 'basari', metin: 'Odak penceresi kaydedildi. Bugün bu saatlerle konuşur.' })
    } catch {
      setSonuc({ tur: 'hata', metin: 'Odak penceresi kaydedilemedi. Bağlantını kontrol edip yeniden dene.' })
    } finally {
      setKaydediliyor(false)
    }
  }

  return (
    <form className="odak-penceresi-formu" onSubmit={kaydet} noValidate aria-labelledby="odak-penceresi-baslik">
      <p className="odak-penceresi-formu__aciklama">
        Son zilden pencerenin sonuna kadar Bugün tek bir zor iş önerir; sonrasında kısa işler.
        Yatma saatinden sonra işi yarına bırakır.
      </p>
      {ALANLAR.map(({ alan, id, etiket }) => (
        <TimePicker
          key={alan}
          id={id}
          labelText={etiket}
          placeholder="ss:dd"
          maxLength={5}
          size="md"
          value={degerler[alan]}
          onChange={e => setDegerler(v => ({ ...v, [alan]: e.target.value }))}
          invalid={Boolean(hatalar[alan])}
          invalidText={hatalar[alan]}
        />
      ))}
      {kaydediliyor
        ? <InlineLoading description="Kaydediliyor…" iconDescription="Kaydediliyor" status="active" />
        : <Button kind="tertiary" size="md" type="submit">Pencereyi kaydet</Button>}
      {sonuc && (
        <InlineNotification lowContrast hideCloseButton
          kind={sonuc.tur === 'basari' ? 'success' : 'error'} role={sonuc.tur === 'basari' ? 'status' : 'alert'}
          statusIconDescription={sonuc.tur === 'basari' ? 'Başarılı' : 'Hata'} title={sonuc.metin} />
      )}
    </form>
  )
}
