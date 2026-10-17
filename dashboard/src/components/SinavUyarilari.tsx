import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, InlineNotification } from '@carbon/react'
import {
  bildirimDurumu, bildirimiAc, bildirimiKapat, BildirimHatasi, denemeBilgisi, denemeGonder, DURUM_METNI, hataMetni,
  ortamiOku,
} from '../utils/bildirim'
import type { BildirimDurumu } from '../utils/bildirim'
import './SinavUyarilari.scss'

// "Sınav uyarıları" (spec §8): bu cihazda aç/kapat, deneme, durum. Durum metinle
// söylenir; renk tek başına anlam taşımaz.
export default function SinavUyarilari() {
  const [durum, setDurum] = useState<BildirimDurumu | null>(null)
  const [mesgul, setMesgul] = useState(false)
  const [bilgi, setBilgi] = useState<{ tur: 'success' | 'error'; metin: string } | null>(null)

  const durumRef = useRef<HTMLParagraphElement>(null)
  // Tıklanan düğme durum değişince kaldırılır; odak gövdeye düşmesin diye bir
  // eylemden sonra durum satırına taşınır (açılışta değil).
  const odakBekliyor = useRef(false)

  const yenile = useCallback(async () => setDurum(bildirimDurumu(await ortamiOku())), [])
  useEffect(() => { void yenile() }, [yenile])
  useEffect(() => {
    if (odakBekliyor.current && !mesgul) {
      odakBekliyor.current = false
      durumRef.current?.focus()
    }
  }, [durum, mesgul, bilgi])

  const yap = async (is: () => Promise<{ tur: 'success' | 'error'; metin: string } | void>) => {
    setMesgul(true)
    setBilgi(null)
    odakBekliyor.current = true
    try {
      const sonuc = await is()
      if (sonuc) setBilgi(sonuc)
    } catch (e) {
      setBilgi({ tur: 'error', metin: hataMetni(e instanceof BildirimHatasi ? e.kod : '') })
    } finally {
      await yenile()
      setMesgul(false)
    }
  }

  return (
    <section id="uyarilar" className="sinav-uyarilari" aria-labelledby="sinav-uyarilari-baslik">
      <h2 id="sinav-uyarilari-baslik" className="sinav-uyarilari__baslik">Sınav uyarıları</h2>
      <p ref={durumRef} tabIndex={-1} className="sinav-uyarilari__durum" aria-live="polite">{durum ? DURUM_METNI[durum] : 'Denetleniyor…'}</p>
      <div className="sinav-uyarilari__dugmeler">
        {durum === 'kapali' && (
          <Button size="sm" kind="primary" disabled={mesgul} onClick={() => yap(async () => { await bildirimiAc() })}>
            Bu cihazda aç
          </Button>
        )}
        {(durum === 'acik' || durum === 'acik-bekliyor') && (
          <>
            {durum === 'acik' && (
              <Button size="sm" kind="tertiary" disabled={mesgul}
                onClick={() => yap(async () => denemeBilgisi(await denemeGonder()))}>
                Deneme bildirimi gönder
              </Button>
            )}
            <Button size="sm" kind="ghost" disabled={mesgul} onClick={() => yap(async () => { await bildirimiKapat() })}>
              Bu cihazda kapat
            </Button>
          </>
        )}
      </div>
      {bilgi && (
        <InlineNotification lowContrast hideCloseButton kind={bilgi.tur} title={bilgi.metin}
          statusIconDescription={bilgi.tur === 'success' ? 'Başarılı' : 'Hata'}
          className="sinav-uyarilari__bilgi" />
      )}
    </section>
  )
}
