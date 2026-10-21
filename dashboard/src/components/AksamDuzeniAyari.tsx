import { useState } from 'react'
import {
  Button, Checkbox, CheckboxGroup, InlineLoading, InlineNotification, Layer, NumberInput, SkeletonText, TimePicker,
} from '@carbon/react'
import { Time } from '@carbon/icons-react'
import { useAksamDuzeni, type AileUyesi } from '../hooks/useAksamDuzeni'
import { useSession } from '../contexts/session'
import {
  clockOf, duzenGovdesi, duzenHatasi, saattenDakika, YEMEK_HATASI, YEMEK_SURESI_HATASI, type AksamDuzeni,
} from '../utils/bugun'

type SaatAlani = 'odeveHazir' | 'zorIsSonu' | 'hafifIsSonu' | 'yemek' | 'hazirlik' | 'yatma'
type Alan = SaatAlani | 'yemekDk'

const ALANLAR: { alan: SaatAlani; id: string; etiket: string }[] = [
  { alan: 'odeveHazir', id: 'aksam-odeve-hazir', etiket: 'Ödeve hazır olduğun saat' },
  { alan: 'zorIsSonu', id: 'aksam-zor-is-sonu', etiket: 'Zor işlerin sonu' },
  { alan: 'hafifIsSonu', id: 'aksam-hafif-is-sonu', etiket: 'Hafif işlerin sonu' },
  { alan: 'yemek', id: 'aksam-yemek', etiket: 'Yemek saati' },
  { alan: 'hazirlik', id: 'aksam-hazirlik', etiket: 'Hazırlık saati' },
  { alan: 'yatma', id: 'aksam-yatma', etiket: 'Yatma saati' },
]

const BICIM_HATASI = 'Saati SS:DD biçiminde yaz (örneğin 17:00).'

/** Which field a broken rule belongs to, so its sentence sits under it. The
 *  server keeps the last word; this only says the same thing sooner. */
function hataAlani(d: AksamDuzeni, hata: string): Alan {
  if (hata === YEMEK_SURESI_HATASI) return 'yemekDk'
  if (hata === YEMEK_HATASI) return 'yemek'
  if (d.okulBitisi > d.odeveHazir) return 'odeveHazir'
  if (d.odeveHazir >= d.zorIsSonu) return 'zorIsSonu'
  if (d.zorIsSonu > d.hafifIsSonu) return 'hafifIsSonu'
  if (d.hafifIsSonu > d.hazirlik) return 'hazirlik'
  return 'yatma'
}

/**
 * The household's evening on Profil (anayasa §2, talimatname B29): from the
 * hour Işık is ready for homework to bedtime, kept in `output/`, so changing it
 * is a setting, not a rebuild. Bugün reads it for the card's voice and for the
 * Day Strip; the evening plan reads it for what fits before dinner and bed.
 *
 * Only the family changes it (R28 I2): it decides when they are told Işık has
 * not started, so on her own account the card shows the values read-only —
 * Carbon's `readOnly`, not `disabled`, so they stay legible (B42) — with no save
 * button. The form appears only once the server's evening has been read: the
 * defaults must never stand in for the real setting, nor a save made from them
 * overwrite the family's "Haber alacaklar" (R28 I3); a failed read says so and
 * saving waits for the next good one.
 */
export default function AksamDuzeniAyari() {
  const { duzen, aileUyeleri, okundu, okunamadi, loading, iskelet, refresh } = useAksamDuzeni()
  const salt = useSession()?.student === true
  return (
    <div className="dashboard-card">
      <h2 className="dashboard-card__title" id="aksam-duzeni-baslik">
        <Time size={20} />
        Akşam Düzeni
      </h2>
      {loading
        ? (iskelet ? <div aria-busy="true"><SkeletonText paragraph lineCount={3} /></div> : null)
        : (
          <>
            {okunamadi && (
              <InlineNotification
                className="aksam-duzeni-formu__okunamadi"
                kind="error"
                lowContrast
                hideCloseButton
                role="alert"
                statusIconDescription="Hata"
                title="Akşam düzeni şu an okunamadı"
                subtitle={salt
                  ? 'Sayfa birkaç dakika içinde yeniden dener.'
                  : 'Kayıtlı ayarların üzerine yazılmasın diye kaydetme kapalı. Sayfa birkaç dakika içinde yeniden dener.'}
              />
            )}
            {/* One layer above the card, like every form set in a card (B31): Carbon's field-02 on layer-01. */}
            {okundu && (
              <Layer>
                <Form ilk={duzen} uyeler={aileUyeleri} salt={salt} kaydedilebilir={!okunamadi} onKaydedildi={refresh} />
              </Layer>
            )}
          </>
        )}
    </div>
  )
}

function Form({ ilk, uyeler, salt, kaydedilebilir, onKaydedildi }: {
  ilk: AksamDuzeni
  uyeler: AileUyesi[]
  /** Işık's own account: the values, read-only, and who sets them (R28 I2). */
  salt: boolean
  /** The latest read succeeded; a save made after a failed one could overwrite what it did not see. */
  kaydedilebilir: boolean
  onKaydedildi: () => void
}) {
  const [saatler, setSaatler] = useState<Record<SaatAlani, string>>({
    odeveHazir: clockOf(ilk.odeveHazir), zorIsSonu: clockOf(ilk.zorIsSonu), hafifIsSonu: clockOf(ilk.hafifIsSonu),
    yemek: clockOf(ilk.yemek), hazirlik: clockOf(ilk.hazirlik), yatma: clockOf(ilk.yatma),
  })
  const [yemekDk, setYemekDk] = useState<number>(ilk.yemekDk)
  const [haber, setHaber] = useState<string[]>(ilk.haberAlacaklar)
  const [hatalar, setHatalar] = useState<Partial<Record<Alan, string>>>({})
  const [kaydediliyor, setKaydediliyor] = useState(false)
  const [sonuc, setSonuc] = useState<{ tur: 'basari' | 'hata'; metin: string } | null>(null)

  async function kaydet(e: React.FormEvent) {
    e.preventDefault()
    if (salt || !kaydedilebilir) return
    setSonuc(null)
    const dk: Partial<Record<SaatAlani, number>> = {}
    const yeni: Partial<Record<Alan, string>> = {}
    for (const { alan } of ALANLAR) {
      const d = saattenDakika(saatler[alan])
      if (d === null) yeni[alan] = BICIM_HATASI
      else dk[alan] = d
    }
    if (Object.keys(yeni).length === 0) {
      const d: AksamDuzeni = { ...ilk, ...(dk as Record<SaatAlani, number>), yemekDk, haberAlacaklar: haber }
      const hata = duzenHatasi(d)
      if (hata) yeni[hataAlani(d, hata)] = hata
    }
    setHatalar(yeni)
    if (Object.keys(yeni).length) return

    // Fields this card does not show (the last bell, the two "tell us" waits) go back as they came.
    // The form exists only after a good read, so the list it holds is the server's own (R28 I3).
    const govde = duzenGovdesi({ ...ilk, ...(dk as Record<SaatAlani, number>), yemekDk, haberAlacaklar: haber }, true)
    setKaydediliyor(true)
    const SABIT = 'Akşam düzeni kaydedilemedi. Bağlantını kontrol edip yeniden dene.'
    try {
      const res = await fetch('/api/aksam-duzeni', {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(govde),
      })
      if (!res.ok) {
        // Only the server's own sentence (a string `error` on a refused save) reaches the reader;
        // a network failure, a non-JSON body or any other shape gets the fixed Turkish one (D3, D4).
        const g = await res.json().catch(() => null) as { error?: unknown } | null
        const cumle = typeof g?.error === 'string' && g.error.trim() ? g.error : SABIT
        setSonuc({ tur: 'hata', metin: cumle })
        return
      }
      onKaydedildi()
      setSonuc({ tur: 'basari', metin: 'Akşam düzeni kaydedildi. Bugün bu saatlerle konuşur.' })
    } catch {
      setSonuc({ tur: 'hata', metin: SABIT })
    } finally {
      setKaydediliyor(false)
    }
  }

  const haberDegisti = (email: string, secili: boolean) =>
    setHaber(onceki => (secili ? [...onceki.filter(e => e !== email), email] : onceki.filter(e => e !== email)))
  // The family chooses from the roster; Işık, who is not sent it, sees who is chosen.
  const kutular = salt ? haber : uyeler.map(u => u.email)

  return (
    <form className="aksam-duzeni-formu" onSubmit={kaydet} noValidate aria-labelledby="aksam-duzeni-baslik">
      <p className="aksam-duzeni-formu__aciklama">
        Bugün, ödeve hazır olduğun saatten zor işlerin sonuna kadar tek bir zor iş önerir; sonrasında hafif işler.
        Yemek ve hazırlık için yer ayırır, yatma saatinden sonra işi yarına bırakır.
      </p>
      {salt && <p className="aksam-duzeni-formu__salt">Bu saatleri ailen ayarlar.</p>}
      {ALANLAR.map(({ alan, id, etiket }) => (
        <TimePicker
          key={alan}
          id={id}
          labelText={etiket}
          placeholder="ss:dd"
          maxLength={5}
          size="md"
          value={saatler[alan]}
          readOnly={salt}
          onChange={e => setSaatler(v => ({ ...v, [alan]: e.target.value }))}
          invalid={Boolean(hatalar[alan])}
          invalidText={hatalar[alan]}
        />
      ))}
      <NumberInput
        id="aksam-yemek-dk"
        label="Yemek süresi (dakika)"
        min={10}
        max={60}
        step={5}
        size="md"
        value={yemekDk}
        readOnly={salt}
        onChange={(_e, { value }) => setYemekDk(Number(value))}
        invalid={Boolean(hatalar.yemekDk)}
        invalidText={hatalar.yemekDk}
      />
      {/* readOnly goes on each Checkbox, never the group: Carbon writes the group's `readOnly` (false
          too) as aria-readonly on its <fieldset>, which ARIA does not allow on a group (axe
          aria-allowed-attr, IBM aria_attribute_valid; measured 2026-10-20). */}
      <CheckboxGroup
        legendText="Haber alacaklar"
        helperText="Liste boşken TEDY kimseye haber vermez. Işık'ın bildirimleri yalnız onun hesabıyla açılmış cihazlara gider."
      >
        {kutular.map(email => (
          <Checkbox
            key={email}
            id={`aksam-haber-${email}`}
            labelText={email}
            checked={haber.includes(email)}
            readOnly={salt}
            onChange={(_e, { checked }) => haberDegisti(email, checked)}
          />
        ))}
      </CheckboxGroup>
      {!salt && (kaydediliyor
        ? <InlineLoading description="Kaydediliyor…" iconDescription="Kaydediliyor" status="active" />
        : <Button kind="tertiary" size="md" type="submit" disabled={!kaydedilebilir}>Akşam düzenini kaydet</Button>)}
      {sonuc && (
        <InlineNotification lowContrast hideCloseButton
          kind={sonuc.tur === 'basari' ? 'success' : 'error'} role={sonuc.tur === 'basari' ? 'status' : 'alert'}
          statusIconDescription={sonuc.tur === 'basari' ? 'Başarılı' : 'Hata'} title={sonuc.metin} />
      )}
    </form>
  )
}
