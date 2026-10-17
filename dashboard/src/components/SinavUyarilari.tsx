import { useCallback, useEffect, useState } from 'react'
import { Button, InlineNotification } from '@carbon/react'
import {
  bildirimDurumu, bildirimiAc, bildirimiKapat, BildirimHatasi, denemeGonder, DURUM_METNI, ortamiOku,
} from '../utils/bildirim'
import type { BildirimDurumu } from '../utils/bildirim'
import './SinavUyarilari.scss'

// "Sınav uyarıları" (spec §8): bu cihazda aç/kapat, deneme, durum. Durum metinle
// söylenir; renk tek başına anlam taşımaz.
export default function SinavUyarilari() {
  const [durum, setDurum] = useState<BildirimDurumu | null>(null)
  const [mesgul, setMesgul] = useState(false)
  const [bilgi, setBilgi] = useState<{ tur: 'success' | 'error'; metin: string } | null>(null)

  const yenile = useCallback(async () => setDurum(bildirimDurumu(await ortamiOku())), [])
  useEffect(() => { void yenile() }, [yenile])

  const yap = async (is: () => Promise<string | void>) => {
    setMesgul(true)
    setBilgi(null)
    try {
      const metin = await is()
      if (metin) setBilgi({ tur: 'success', metin })
    } catch (e) {
      const kod = e instanceof BildirimHatasi ? e.kod : ''
      setBilgi({ tur: 'error', metin: kod === 'reddedildi' ? DURUM_METNI.reddedildi : 'İşlem tamamlanamadı; biraz sonra yeniden denenebilir.' })
    } finally {
      await yenile()
      setMesgul(false)
    }
  }

  return (
    <section id="uyarilar" className="sinav-uyarilari" aria-labelledby="sinav-uyarilari-baslik">
      <h2 id="sinav-uyarilari-baslik" className="sinav-uyarilari__baslik">Sınav uyarıları</h2>
      <p className="sinav-uyarilari__durum" aria-live="polite">{durum ? DURUM_METNI[durum] : 'Denetleniyor…'}</p>
      <div className="sinav-uyarilari__dugmeler">
        {durum === 'kapali' && (
          <Button size="sm" kind="primary" disabled={mesgul} onClick={() => yap(async () => { await bildirimiAc() })}>
            Bu cihazda aç
          </Button>
        )}
        {durum === 'acik' && (
          <>
            <Button size="sm" kind="tertiary" disabled={mesgul}
              onClick={() => yap(async () => `Deneme bildirimi ${await denemeGonder()} cihaza gönderildi.`)}>
              Deneme bildirimi gönder
            </Button>
            <Button size="sm" kind="ghost" disabled={mesgul} onClick={() => yap(async () => { await bildirimiKapat() })}>
              Bu cihazda kapat
            </Button>
          </>
        )}
      </div>
      {bilgi && (
        <InlineNotification lowContrast hideCloseButton kind={bilgi.tur} title={bilgi.metin}
          className="sinav-uyarilari__bilgi" />
      )}
    </section>
  )
}
