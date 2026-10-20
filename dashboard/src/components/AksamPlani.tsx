import { useEffect, useRef, useState } from 'react'
import {
  Accordion, AccordionItem, Button, InlineLoading, InlineNotification, NumberInput, Toggle,
} from '@carbon/react'
import { ArrowRight, Checkmark } from '@carbon/icons-react'
import { Rakamli } from './patterns/Rakamli'
import SubjectLabel from './SubjectLabel'
import { subjectClass } from '../utils/subject'
import {
  blokSatiri, odevAdi, odevTahminDk, plandaOlmayanMetni, sigmayanMetni, sonParcaMi, tahminMetni,
  yarinaKaldiMetni, type KartDurumu, type PlanHatasi, type PlanYaniti,
} from '../utils/aksamPlani'
import type { PlanSonucu } from '../hooks/useAksamPlani'
import './AksamPlani.scss'

export interface AksamPlaniIslemleri {
  basla: (id: string) => Promise<PlanSonucu>
  bitti: (id: string, tamamlandi?: boolean) => Promise<PlanSonucu>
  simdiDegil: (id: string) => Promise<PlanSonucu>
  sureDuzelt: (anahtar: string, dk: number) => Promise<PlanSonucu>
  aksamYok: (aktif: boolean) => Promise<PlanSonucu>
}

type Islem = 'basla' | 'bitti' | 'evet' | 'biraz' | 'simdi-degil' | 'sure' | 'aksam-yok'

const ISLEM_METNI: Record<Islem, string> = {
  basla: 'Başlatılıyor…', bitti: 'Kaydediliyor…', evet: 'Kaydediliyor…', biraz: 'Kaydediliyor…',
  'simdi-degil': 'Erteleniyor…', sure: 'Kaydediliyor…', 'aksam-yok': 'Kaydediliyor…',
}

/**
 * Tonight's study plan on Bugün (spec 2026-10-19 §6.7, §6.8).
 *
 * From 17:00 it is the page's one thing (İ1): the view's one subject panel,
 * NextThing's own (İ8.3), whose title — the step itself — is the page's largest
 * text (P1). Before 17:00 it is one quiet line under the lesson card. "Başla"
 * starts the block, "Bitti" ends it, and the next one waits behind a short
 * break; the clock in the plan is only a forecast, the touches move it.
 *
 * A duration is always "tahmin" (İ3, D4); no points, streaks or badges; the
 * family's calm sentence ("17:15'e kadar başlamazsan ailene haber gider.") sits
 * on the card in the helper tone. A refused touch says the server's sentence
 * in a Carbon inline notification, never the HTTP text (D3, D4).
 */
export function AksamPlani({ plan, kart, aile, islemler }: {
  plan: PlanYaniti
  kart: KartDurumu
  /** A family member is looking (not Işık): only they may turn tonight's plan off. */
  aile: boolean
  islemler: AksamPlaniIslemleri
}) {
  const [islem, setIslem] = useState<Islem | null>(null)
  const [hata, setHata] = useState<PlanHatasi | null>(null)
  const [soru, setSoru] = useState<string | null>(null)
  // Both belong to one block: when the card steps on, they are simply not this block's any more.
  const [duzeltilen, setDuzeltilen] = useState<string | null>(null)
  const [dakika, setDakika] = useState(20)
  const basliRef = useRef<HTMLHeadingElement>(null)
  const satirRef = useRef<HTMLParagraphElement>(null)
  const blok = kart.blok
  // One touch at a time: a double click in the same frame, before React re-renders the button away,
  // must post once (a state flag would still read "free" in that frame).
  const mesgul = useRef(false)
  // Focus follows the reader's own touch only: a successful one counts here, a poll never does.
  const [odakIstegi, setOdakIstegi] = useState(0)
  const islenenOdak = useRef(0)

  const duzelt = blok != null && duzeltilen === blok.id

  // After a touch the button pressed is usually gone (Başla becomes Bitti, the card steps on, the
  // evening ends): focus lands on the card's title, or on the quiet "Bugünlük bu kadar" line, so the
  // keyboard is not left on nothing (D2). A minute's poll changes the card without moving focus.
  useEffect(() => {
    if (odakIstegi === islenenOdak.current) return
    islenenOdak.current = odakIstegi
    if (kart.tur === 'bitti') satirRef.current?.focus()
    else basliRef.current?.focus()
  }, [odakIstegi, kart.tur])

  async function calistir(ad: Islem, f: () => Promise<PlanSonucu>) {
    if (mesgul.current) return false
    mesgul.current = true
    setIslem(ad)
    setHata(null)
    try {
      const s = await f()
      if (!s.ok) setHata(s.hata)
      else if (ad !== 'aksam-yok') setOdakIstegi(n => n + 1)
      return s.ok
    } finally {
      mesgul.current = false
      setIslem(null)
    }
  }

  const bitirmeyeBas = () => {
    if (!blok) return
    // Only the homework's last part asks whether the whole homework is done (§6.8).
    if (sonParcaMi(blok)) {
      setSoru(blok.id)
      return
    }
    calistir('bitti', () => islemler.bitti(blok.id))
  }

  const tahminiAc = () => {
    if (!blok?.odev_anahtari) return
    setDakika(odevTahminDk(plan, blok.odev_anahtari))
    setDuzeltilen(blok.id)
  }
  const dakikaGecerli = Number.isInteger(dakika) && dakika >= 5 && dakika <= 120

  const yukleniyor = islem && (
    <InlineLoading className="aksam-plani__yukleniyor" description={ISLEM_METNI[islem]}
      iconDescription={ISLEM_METNI[islem]} status="active" />
  )

  const bildirim = hata && (
    <InlineNotification
      className="aksam-plani__bildirim"
      kind={hata.tur === 'hata' ? 'error' : 'warning'}
      lowContrast
      hideCloseButton
      role={hata.tur === 'hata' ? 'alert' : 'status'}
      statusIconDescription={hata.tur === 'hata' ? 'Hata' : 'Uyarı'}
      title={hata.baslik}
      subtitle={hata.alt}
    />
  )

  const satirlar = (
    <>
      {plan.tasinan.length > 0 && <p className="aksam-plani__satir">{yarinaKaldiMetni(plan.tasinan)}</p>}
      {plan.sigmayan.length > 0 && <p className="aksam-plani__satir">{sigmayanMetni(plan.sigmayan)}</p>}
      {plan.planda_olmayan > 0 && (
        <p className="aksam-plani__satir"><Rakamli metin={plandaOlmayanMetni(plan.planda_olmayan)} /></p>
      )}
    </>
  )

  const aksamYokAnahtari = aile && (
    <Toggle
      id="aksam-plani-yok"
      className="aksam-plani__yok"
      labelText="Bu akşam plan yok"
      labelA="Hayır"
      labelB="Evet"
      toggled={plan.aksam_yok}
      disabled={islem !== null}
      onToggle={aktif => { calistir('aksam-yok', () => islemler.aksamYok(aktif)) }}
    />
  )

  const tamami = plan.bloklar.length > 0 && (
    <Accordion className="aksam-plani__tamami" size="lg">
      <AccordionItem title="Bu akşamın tamamı">
        <p className="aksam-plani__not">Saatler tahmindir; sıradaki iş, bir önceki bitince başlar.</p>
        <ol className="aksam-plani__liste">
          {plan.bloklar.map(b => {
            const s = blokSatiri(b)
            return (
              <li key={b.id} className={['aksam-plani__liste-satir', b.durum === 'bitti' && 'aksam-plani__liste-satir--bitti']
                .filter(Boolean).join(' ')}>
                <span className="aksam-plani__liste-saat tedy-time">{s.saat}</span>
                <span className="aksam-plani__liste-ad">
                  {b.tur === 'calisma' ? <SubjectLabel course={b.ders}>{s.ad}</SubjectLabel> : s.ad}
                </span>
                {s.sure && <span className="aksam-plani__liste-sure"><Rakamli metin={s.sure} /></span>}
                {s.durum && <span className="aksam-plani__liste-durum">{s.durum}</span>}
              </li>
            )
          })}
        </ol>
      </AccordionItem>
    </Accordion>
  )

  // The family can turn tonight off and back on; with the plan off, only that switch is left here. A
  // holiday closes it too (the switch stays off): one quiet line says so.
  if (kart.tur === 'kapali') {
    if (!aksamYokAnahtari && plan.aksam_yok) return null
    return (
      <div className="aksam-plani__ek">
        {!plan.aksam_yok && <p className="aksam-plani__satir aksam-plani__tatil">{kart.baslik}</p>}
        {aksamYokAnahtari}
        {bildirim}
      </div>
    )
  }

  // Before 17:00, once the evening is over, and on an evening with no work block left but something
  // moved, too big or left out: one quiet line, not a second panel (İ1, İ6), and the lines that say what.
  if (kart.tur === 'onizleme' || kart.tur === 'bitti' || kart.tur === 'bos') {
    return (
      <>
        <section className={`aksam-plani aksam-plani--sessiz aksam-plani--${kart.tur}`} aria-label="Akşam planı">
          <p className="aksam-plani__baslik aksam-plani__baslik--sessiz" tabIndex={-1} ref={satirRef}>
            <Rakamli metin={kart.baslik} />
          </p>
          {kart.alt && <p className="aksam-plani__alt">{kart.alt}</p>}
          {plan.haber_metni && <p className="aksam-plani__haber"><Rakamli metin={plan.haber_metni} /></p>}
        </section>
        <div className="aksam-plani__ek">
          {satirlar}
          {tamami}
          {aksamYokAnahtari}
          {bildirim}
        </div>
      </>
    )
  }

  if (!blok) return null
  const ders = kart.tur === 'mola' ? null : blok.ders
  const sonParcaSorusu = soru === blok.id
  const ertelendi = blok.durum === 'ertelendi'

  return (
    <>
      <section
        className={['aksam-plani', ders ? subjectClass(ders) : 'aksam-plani--notr', `aksam-plani--${kart.tur}`].join(' ')}
        aria-labelledby="aksam-plani-baslik"
      >
        <div className="aksam-plani__govde">
          {kart.ust && <span className="aksam-plani__ust"><Rakamli metin={kart.ust} /></span>}
          <h2 id="aksam-plani-baslik" className="aksam-plani__baslik" tabIndex={-1} ref={basliRef}>
            <Rakamli metin={kart.baslik} />
          </h2>
          {kart.tur !== 'mola' && (
            <p className="aksam-plani__odev">
              <SubjectLabel course={blok.ders}>{odevAdi(blok)}</SubjectLabel>
              {blok.parca_sayisi > 1 && (
                <span className="aksam-plani__parca">
                  <Rakamli metin={` · ${blok.parca + 1}. parça / ${blok.parca_sayisi}`} />
                </span>
              )}
            </p>
          )}

          {kart.tur !== 'mola' && !duzelt && (
            <Button kind="ghost" size="lg" className="aksam-plani__tahmin" onClick={tahminiAc}
              disabled={!blok.odev_anahtari || islem !== null}>
              {/* One flex item: the button is a flex box, and loose text nodes lost their spaces ("tahmin25dk"). */}
              <span><span className="cds--visually-hidden">Süreyi düzelt: </span><Rakamli metin={tahminMetni(blok.tahmin_dk)} /></span>
            </Button>
          )}
          {duzelt && blok.odev_anahtari && (
            <form className="aksam-plani__duzelt" onSubmit={async e => {
              e.preventDefault()
              if (!dakikaGecerli || !blok.odev_anahtari) return
              if (await calistir('sure', () => islemler.sureDuzelt(blok.odev_anahtari!, dakika))) setDuzeltilen(null)
            }}>
              <NumberInput
                id="aksam-plani-sure"
                size="lg"
                label="Ödevin tamamı için tahmin (dakika)"
                helperText="5 ile 120 arasında"
                min={5}
                max={120}
                step={5}
                value={dakika}
                invalid={!dakikaGecerli}
                invalidText="5 ile 120 arasında bir dakika yaz."
                onChange={(_e, { value }) => setDakika(Number(value))}
              />
              {islem === 'sure' ? yukleniyor : (
                <span className="aksam-plani__duzelt-eylem">
                  <Button kind="tertiary" size="lg" type="submit" disabled={!dakikaGecerli || islem !== null}>Kaydet</Button>
                  <Button kind="ghost" size="lg" onClick={() => setDuzeltilen(null)}>Vazgeç</Button>
                </span>
              )}
            </form>
          )}

          {kart.alt && <p className="aksam-plani__alt"><Rakamli metin={kart.alt} /></p>}
          {plan.haber_metni && <p className="aksam-plani__haber"><Rakamli metin={plan.haber_metni} /></p>}

          {sonParcaSorusu && (
            <fieldset className="aksam-plani__soru">
              <legend className="aksam-plani__soru-metni">Ödevin tamamı bitti mi?</legend>
              {islem === 'evet' || islem === 'biraz' ? yukleniyor : (
                <span className="aksam-plani__soru-eylem">
                  <Button kind="primary" size="lg" renderIcon={Checkmark}
                    onClick={() => calistir('evet', () => islemler.bitti(blok.id, true))}>Evet</Button>
                  <Button kind="tertiary" size="lg"
                    onClick={() => calistir('biraz', () => islemler.bitti(blok.id, false))}>Biraz kaldı</Button>
                </span>
              )}
            </fieldset>
          )}
          {bildirim}
        </div>

        {!sonParcaSorusu && (
          <div className="aksam-plani__eylem">
            {islem && islem !== 'sure' && islem !== 'aksam-yok' ? yukleniyor : (
              <>
                {kart.tur === 'calisma' && (
                  <Button kind="primary" size="lg" renderIcon={Checkmark} onClick={bitirmeyeBas}>Bitti</Button>
                )}
                {kart.tur === 'bekliyor' && (
                  <Button kind="primary" size="lg" renderIcon={ArrowRight}
                    onClick={() => calistir('basla', () => islemler.basla(blok.id))}>Başla</Button>
                )}
                {kart.tur === 'mola' && (
                  <Button kind="ghost" size="lg"
                    onClick={() => calistir('basla', () => islemler.basla(blok.id))}>Moladan dön, başla</Button>
                )}
                {kart.tur === 'bekliyor' && (ertelendi
                  ? <p className="aksam-plani__ertelendi">{aile ? 'Bu blok bir kez ertelendi.' : 'Bu bloğu bir kez erteledin.'}</p>
                  : (
                    <Button kind="ghost" size="lg"
                      onClick={() => calistir('simdi-degil', () => islemler.simdiDegil(blok.id))}>Şimdi değil</Button>
                  ))}
              </>
            )}
          </div>
        )}
      </section>

      <div className="aksam-plani__ek">
        {satirlar}
        {tamami}
        {aksamYokAnahtari}
      </div>
    </>
  )
}
