import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, InlineNotification } from '@carbon/react'
import {
  BANA_GECTI_METNI, BILDIRIM_DEGISTI, bildirimDurumu, bildirimiAc, bildirimiBanaGecir, bildirimiKapat, BildirimHatasi,
  denemeBilgisi, denemeGonder, DURUM_METNI, hataMetni, ortamiOku, SUNUCU_SILINEMEDI_METNI,
} from '../utils/bildirim'
import type { BildirimDurumu, Bilgi } from '../utils/bildirim'
import './SinavUyarilari.scss'

const IKON_ACIKLAMASI: Record<Bilgi['tur'], string> = { success: 'Başarılı', error: 'Hata', warning: 'Uyarı' }

// "Sınav uyarıları" (spec §8): bu cihazda aç/kapat, deneme, durum. Durum metinle
// söylenir; renk tek başına anlam taşımaz.
export default function SinavUyarilari() {
  const [durum, setDurum] = useState<BildirimDurumu | null>(null)
  const [mesgul, setMesgul] = useState(false)
  const [bilgi, setBilgi] = useState<Bilgi | null>(null)

  const durumRef = useRef<HTMLParagraphElement>(null)
  // Tıklanan düğme durum değişince kaldırılır; odak gövdeye düşmesin diye bir
  // eylemden sonra durum satırına taşınır (açılışta değil).
  const odakBekliyor = useRef(false)

  // Never rejects: a browser that cannot read its own registration must not lock the buttons or
  // leave an unhandled rejection. The last known state stays; with none, the card says "kapalı".
  const yenile = useCallback(async () => {
    try {
      setDurum(bildirimDurumu(await ortamiOku()))
    } catch {
      setDurum(d => d ?? 'kapali')
    }
  }, [])
  useEffect(() => { void yenile() }, [yenile])

  // The permission can change outside the card — the browser's site settings, another tab — and the
  // silent re-registration may answer after the first reading. Coming back to the tab re-reads too.
  useEffect(() => {
    let iptal = false
    let izinDurumu: PermissionStatus | null = null
    const degisti = () => { void yenile() }
    const gorunur = () => { if (document.visibilityState === 'visible') void yenile() }
    navigator.permissions?.query({ name: 'notifications' as PermissionName })
      .then(d => {
        if (iptal) return
        izinDurumu = d
        d.addEventListener('change', degisti)
      })
      .catch(() => { /* izin sorgusu yok: sekmeye dönüş yine yeniler */ })
    document.addEventListener('visibilitychange', gorunur)
    window.addEventListener(BILDIRIM_DEGISTI, degisti)
    return () => {
      iptal = true
      izinDurumu?.removeEventListener('change', degisti)
      document.removeEventListener('visibilitychange', gorunur)
      window.removeEventListener(BILDIRIM_DEGISTI, degisti)
    }
  }, [yenile])

  useEffect(() => {
    if (odakBekliyor.current && !mesgul) {
      odakBekliyor.current = false
      durumRef.current?.focus()
    }
  }, [durum, mesgul, bilgi])

  const yap = async (is: () => Promise<Bilgi | void>) => {
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
        {durum === 'baska-sahip' && (
          <Button size="sm" kind="primary" disabled={mesgul}
            onClick={() => yap(async () => { await bildirimiBanaGecir(); return { tur: 'success', metin: BANA_GECTI_METNI } })}>
            Bu cihazda bana geçir
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
            <Button size="sm" kind="ghost" disabled={mesgul}
              onClick={() => yap(async () => {
                if ((await bildirimiKapat()) === 'sunucu-silinemedi') return { tur: 'warning', metin: SUNUCU_SILINEMEDI_METNI }
              })}>
              Bu cihazda kapat
            </Button>
          </>
        )}
      </div>
      {bilgi && (
        <InlineNotification lowContrast hideCloseButton kind={bilgi.tur} title={bilgi.metin}
          statusIconDescription={IKON_ACIKLAMASI[bilgi.tur]}
          className="sinav-uyarilari__bilgi" />
      )}
    </section>
  )
}
