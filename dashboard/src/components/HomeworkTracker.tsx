import { useState, useEffect, useMemo, useRef, useId, type ReactNode } from 'react'
import {
  Tag, ComposedModal, ModalHeader, ModalBody, ModalFooter, Button, InlineLoading, Callout, ContainedList,
  ContainedListItem, InlineNotification, SkeletonPlaceholder, SkeletonText,
} from '@carbon/react'
import {
  Chat, CheckmarkFilled, CheckmarkOutline, ChevronDown, ChevronUp, CloseFilled, Document, Incomplete, WarningFilled,
} from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { HomeworkDocument, HomeworkItem } from '../types'
import { parseDeadline, formatTurkishDate, getHomeworkStatus, kisaTeslim } from '../utils/formatters'
import { isleriGrupla, normalizeStatus, sinavZamani, teslimMetni } from '../utils/isler'
import { apiHataCumlesi } from '../utils/apiHatasi'
import SubjectLabel from './SubjectLabel'
import { NextThing } from './NextThing'
import { Rakamli } from './patterns/Rakamli'
import './patterns/patterns.scss'
import './HomeworkTracker.scss'
import { useNavigate } from 'react-router-dom'
import { acikOgeAc, asistanaSor } from '../asistan/sayfaBaglami'
import type { ExamsApiResponse, ModuleCard } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import { EkBaglantisi } from './patterns/EkBaglantisi'
import { SinavEtiketi, IncelenmediNotu } from './SinavKarti'
import { uygulamaIcindeAc } from '../utils/gezinme'
import { useFocusMode } from '../contexts/focusMode'
import YuklemeAlani from './YuklemeAlani'
import { yaptimIsaretle, yaptimGeriAl } from '../utils/odevYaptim'
import { YaptinSatiri, type GeriAlDurumu } from './patterns/YaptinSatiri'

// İşler (yenileme 2026-10-15, spec docs/superpowers/specs/2026-10-15-isler-yenileme-design.md): one named
// thing, then the rest of the owed work, the exams ahead and the settled history — each a Carbon on-page
// contained list of 48px rows, on the page itself (no card around cards). A row is one control that opens the
// work; its one action ("Yaptım", "Geri al", "Modülü aç") sits beside it.

const dersAdi = (hw: HomeworkItem) => String(hw.normalized_course || hw['Ders Adı'] || '').trim()
const odevAdi = (hw: HomeworkItem) =>
  [dersAdi(hw), String(hw['Ödev Başlığı'] || '').trim()].filter(Boolean).join(' — ')
const eylemAnahtari = (hw: HomeworkItem) =>
  hw.homework_key || `${hw['Ders Adı']}|${hw['Ödev Başlığı']}|${hw['Ödev Son Teslim Tarihi']}`
/** When the work is due, as a Date (null when the portal's text does not parse). */
const teslimi = (hw: HomeworkItem) => { return parseDeadline(hw['Ödev Son Teslim Tarihi']) }

type Bolum = 'sonra' | 'yapilan' | 'tamamlanan' | 'yapilmayan'

export default function HomeworkTracker() {
  const { data: hwData, refresh: refreshHomework, loading, iskelet, hataTuru } =
    useApi<{ summary: string; homework: HomeworkItem[] }>('/api/homework', { summary: '', homework: [] })
  const { data: enrichmentData } = useApi<Record<string, { course: string; title: string; note: string; type: string }>>(
    '/api/enrichment', {}
  )

  const [selectedHw, setSelectedHw] = useState<HomeworkItem | null>(null)
  // The control a window was opened from; focus goes back to it when the window closes ([3.8-8]).
  const acanRef = useRef<HTMLElement | null>(null)
  const gezin = useNavigate()
  // The page's minute clock, moved on every minute so "Bugün", the groups and the exam tags follow the time;
  // nothing calls Date.now() during render (C16).
  const [simdiMs, setSimdiMs] = useState(() => Date.now())
  const { focusMode } = useFocusMode()
  // The rest of the owed work opens; everything settled starts closed (İ7, S34).
  const [collapsed, setCollapsed] = useState<Record<Bolum, boolean>>({
    sonra: false, yapilan: true, tamamlanan: true, yapilmayan: true,
  })
  const [markingKey, setMarkingKey] = useState<string | null>(null)
  // The row whose "Yaptım" could not be stored: said under that row, never in silence (D3).
  const [markErrorKey, setMarkErrorKey] = useState<string | null>(null)
  // "Yaptım" inside the homework window: saving there, and its failure said there.
  const [pencereKaydediyor, setPencereKaydediyor] = useState(false)
  const [pencereHatasi, setPencereHatasi] = useState(false)
  // B63 (S40): the work "Yaptım" just recorded, with "Geri al" on the same line; and the row whose undo is in
  // flight or failed in "Yapılan".
  const [sonYapilan, setSonYapilan] = useState<HomeworkItem | null>(null)
  const [sonGeriAl, setSonGeriAl] = useState<GeriAlDurumu>('bos')
  const [geriAlinanKey, setGeriAlinanKey] = useState<string | null>(null)
  const [geriAlHataKey, setGeriAlHataKey] = useState<string | null>(null)
  const [docBusy, setDocBusy] = useState(false)
  const [docError, setDocError] = useState('')
  // B23 (S40): the document to remove. The homework window turns in place into a danger confirmation.
  const [silinecekBelge, setSilinecekBelge] = useState<HomeworkDocument | null>(null)
  const modalRef = useRef<HTMLDivElement>(null)
  // Carbon's Escape listener keeps the onClose of the render it was registered in, so onClose reads the live
  // state through refs — otherwise Escape on the confirmation closed the whole homework window.
  const onayRef = useRef<{ belge: HomeworkDocument | null; mesgul: boolean }>({ belge: null, mesgul: false })
  useEffect(() => { onayRef.current = { belge: silinecekBelge, mesgul: docBusy || pencereKaydediyor } },
    [silinecekBelge, docBusy, pencereKaydediyor])
  useEffect(() => {
    if (!silinecekBelge) return
    // Onay açılırken ilk odak "Vazgeç"te (Carbon tehlike modalı); pencere zaten açık olduğu için elle verilir.
    const kare = requestAnimationFrame(() => {
      modalRef.current?.querySelector<HTMLButtonElement>('.cds--modal-footer .cds--btn--secondary')?.focus()
    })
    return () => cancelAnimationFrame(kare)
  }, [silinecekBelge])
  useEffect(() => {
    const t = setInterval(() => setSimdiMs(Date.now()), 60000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    setSelectedHw(prev => {
      if (!prev?.homework_key) return prev
      return (hwData.homework || []).find(hw => hw.homework_key === prev.homework_key) ?? prev
    })
  }, [hwData])

  // Asistan başlatıcısı açık ödevi sayfa bağlamına ekler (sayfaBaglami.ts). İlkel bağımlılıklar: ödev listesi
  // yenilenince (yeni nesne) yeniden kayıt olmaz, okurun kapattığı bağlam çipi geri gelmez.
  const acikOdev = selectedHw?.homework_key
  const acikOdevEtiketi = selectedHw ? `${selectedHw.normalized_course || selectedHw['Ders Adı']} — ${selectedHw['Ödev Başlığı']}` : ''
  useEffect(() => (acikOdev ? acikOgeAc({ tur: 'odev', id: acikOdev, etiket: acikOdevEtiketi }) : undefined),
    [acikOdev, acikOdevEtiketi])

  function pencereyiAc(hw: HomeworkItem, acan?: HTMLElement | null) {
    acanRef.current = acan ?? (document.activeElement as HTMLElement | null)
    setPencereHatasi(false)
    setSelectedHw(hw)
  }

  function pencereyiKapat(odagiGeriVer = true) {
    setSelectedHw(null)
    setPencereHatasi(false)
    const acan = acanRef.current
    acanRef.current = null
    if (odagiGeriVer && acan) requestAnimationFrame(() => { if (acan.isConnected) acan.focus() })
  }

  // "Asistana sor" (B78): the window closes, the homework becomes the next question's context and the panel
  // opens — with no launcher (phone, focus mode) the Asistan page opens instead.
  function odeviAsistanaSor(hw: HomeworkItem) {
    if (!hw.homework_key) return
    const karsilandi = asistanaSor({ tur: 'odev', id: hw.homework_key,
      etiket: `${hw.normalized_course || hw['Ders Adı']} — ${hw['Ödev Başlığı']}` })
    pencereyiKapat(false)
    if (!karsilandi) gezin('/asistan?sayfa=isler')
  }

  async function addDocument(file: File) {
    const key = selectedHw?.homework_key
    if (!key) {
      setDocError('Bu ödevin kimliği yok.')
      return
    }
    setDocBusy(true)
    setDocError('')
    try {
      const body = new FormData()
      body.append('dosya', file)
      const upload = await fetch('/api/assistant/uploads', {
        method: 'POST',
        credentials: 'include',
        body,
      })
      const ek = await upload.json()
      if (!upload.ok) throw new Error(ek.error || 'Belge yüklenemedi.')
      const res = await fetch(`/api/assistant/uploads/${ek.id}/odeve-bagla`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anahtar: key }),
      })
      const payload = await res.json()
      if (!res.ok) throw new Error(payload.error || 'Belge ödeve bağlanamadı.')
      const documents = Array.isArray(payload?.documents) ? payload.documents as HomeworkDocument[] : []
      if (documents.length) setSelectedHw(prev => prev ? { ...prev, documents } : prev)
      refreshHomework()
    } catch (err) {
      setDocError(err instanceof Error ? err.message : 'Belge eklenemedi.')
    } finally {
      setDocBusy(false)
    }
  }

  async function removeDocument(id: string) {
    setDocBusy(true)
    setDocError('')
    try {
      const res = await fetch(`/api/homework/documents/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      })
      // Sunucunun ham hata metni okura gitmez (D4); başarısız silme doğru fiille söylenir (S40).
      if (!res.ok) throw new Error('Belge silinemedi.')
      setSelectedHw(prev => prev
        ? { ...prev, documents: (prev.documents || []).filter(doc => doc.id !== id) }
        : prev)
      refreshHomework()
    } catch {
      setDocError('Belge silinemedi.')
    } finally {
      setDocBusy(false)
      setSilinecekBelge(null)
    }
  }

  const simdi = useMemo(() => new Date(simdiMs), [simdiMs])
  const { siradaki, sonra, yapilan, tamamlanan, yapilmayan } = useMemo(
    () => isleriGrupla(hwData.homework || [], simdiMs), [hwData.homework, simdiMs])
  // The work "Yaptım" can still be pressed on: the next thing and the rest of the active list.
  const aktifAnahtarlar = useMemo(
    () => new Set([siradaki, ...sonra].filter(Boolean).map(hw => eylemAnahtari(hw!))),
    [siradaki, sonra])

  // Exams share this surface because they are the same thing to Işık: work she owes with a date on it. Only
  // the ones still ahead — the settled ones are history and belong on the exam page (İ7).
  const { data: examData, hataTuru: sinavHatasi } = useApi<ExamsApiResponse>('/api/exams',
    { exams: [], stats: { upcoming: 0, past: 0, averageGrade: null } })
  const upcomingExams = useMemo(
    () => examData.exams.filter(e => e.status === 'upcoming'),
    [examData.exams])
  const navigate = useNavigate()

  // A published module linked to an exam is offered where the exam already is (spec §4.3 step 9).
  const { data: moduleData } = useApi<{ moduller: ModuleCard[] }>('/api/modules', { moduller: [] })
  const moduleByExam = useMemo(() => {
    const rows = Array.isArray(moduleData.moduller) ? moduleData.moduller : []
    return new Map(rows.filter(m => m.ted_link?.kind === 'exam').map(m => [m.ted_link!.id, m]))
  }, [moduleData.moduller])

  // A working state, not a dimmer: focus closes the lists and leaves the one named thing, with the counts
  // still visible so nothing feels lost (§5).
  const isCollapsed = (key: Bolum) => focusMode || collapsed[key]
  const toggleSection = (key: Bolum) => setCollapsed(prev => ({ ...prev, [key]: !prev[key] }))

  const handleMarkDone = async (hw: HomeworkItem) => {
    const key = eylemAnahtari(hw)
    setMarkingKey(key)
    setMarkErrorKey(null)
    try {
      if (await yaptimIsaretle(hw)) {
        setSonYapilan(hw)
        setSonGeriAl('bos')
        refreshHomework()
      } else setMarkErrorKey(key)
    } finally {
      setMarkingKey(null)
    }
  }

  // "Yaptım" in the window: on success the window closes and the "Yaptın: … · Geri al" line takes the focus
  // (B40); on failure the window stays and says so (D3).
  const pencerdeYaptim = async () => {
    if (!selectedHw || pencereKaydediyor) return
    const hw = selectedHw
    setPencereKaydediyor(true)
    setPencereHatasi(false)
    try {
      if (await yaptimIsaretle(hw)) {
        pencereyiKapat(false)
        setSonYapilan(hw)
        setSonGeriAl('bos')
        refreshHomework()
      } else setPencereHatasi(true)
    } finally {
      setPencereKaydediyor(false)
    }
  }

  // "Geri al" (S40, B63): the mark goes and the work is active again. The line under the next thing and a row
  // in "Yapılan" use the same call.
  const sonuGeriAl = async () => {
    if (!sonYapilan) return
    setSonGeriAl('aliniyor')
    if (await yaptimGeriAl(sonYapilan)) {
      setSonYapilan(null)
      setSonGeriAl('bos')
      refreshHomework()
    } else setSonGeriAl('hata')
  }

  const satiriGeriAl = async (hw: HomeworkItem) => {
    const key = eylemAnahtari(hw)
    setGeriAlinanKey(key)
    setGeriAlHataKey(null)
    try {
      if (await yaptimGeriAl(hw)) {
        if (sonYapilan && eylemAnahtari(sonYapilan) === key) setSonYapilan(null)
        refreshHomework()
      } else setGeriAlHataKey(key)
    } finally {
      setGeriAlinanKey(null)
    }
  }

  const satirlar = (items: HomeworkItem[], eylem: 'yaptim' | 'geri-al' | null, kararGoster: boolean) =>
    items.flatMap(hw => {
      const key = eylemAnahtari(hw)
      const satir = (
        <IsSatiri key={key} hw={hw} simdi={simdi} onOpen={pencereyiAc} karar={kararGoster ? kararEtiketi(hw) : null}
          eylem={eylem === 'yaptim'
            ? adId => markingKey === key
              ? <InlineLoading className="isler-satir__kaydediliyor" description="Kaydediliyor…"
                  iconDescription="Kaydediliyor" status="active" />
              : <Button kind="ghost" size="lg" aria-describedby={adId} onClick={() => void handleMarkDone(hw)}>Yaptım</Button>
            : eylem === 'geri-al' && hw.student_marked_done
              ? () => geriAlinanKey === key
                ? <InlineLoading className="isler-satir__kaydediliyor" description="Geri alınıyor…"
                    iconDescription="Geri alınıyor" status="active" />
                // B63: a settled row's action is a correction, not a next step — ghost; its name carries the
                // homework so a list of them is told apart.
                : <Button kind="ghost" size="lg" aria-label={`Geri al: ${hw['Ödev Başlığı']}`}
                    onClick={() => void satiriGeriAl(hw)}>Geri al</Button>
              : undefined} />
      )
      const hata = (eylem === 'yaptim' && markErrorKey === key && 'Kaydedilemedi. Bağlantını kontrol edip yeniden dene.')
        || (eylem === 'geri-al' && geriAlHataKey === key && 'Geri alınamadı. Bağlantını kontrol edip yeniden dene.')
      return hata
        ? [satir, <li key={`${key}-hata`} className="homework-item__error isler-satir__hata"><p role="alert">{hata}</p></li>]
        : [satir]
    })

  const bolum = (key: Bolum, baslik: string, items: HomeworkItem[], eylem: 'yaptim' | 'geri-al' | null,
    kararGoster = false) => items.length === 0 ? null : (
      <IsBolumu key={key} id={`isler-${key}`} sinif={key} baslik={baslik} sayi={items.length}
        acik={!isCollapsed(key)} onToggle={() => toggleSection(key)}>
        {satirlar(items, eylem, kararGoster)}
      </IsBolumu>
    )

  const hata = hataTuru ? apiHataCumlesi(hataTuru, 'Ödevler') : null
  const siradakiTeslim = siradaki ? teslimi(siradaki) : null

  return (
    <>
    <div className="isler" aria-busy={iskelet || undefined}>
      {/* The page heading lives on the shell. A second visible "İşler" here was the same word twice. */}
      {hata && (
        <InlineNotification className="isler__hata" kind="error" role="alert" lowContrast hideCloseButton
          statusIconDescription="Hata" title={hata.baslik} subtitle={hata.ayrinti} />
      )}

      {iskelet && <IslerIskeleti />}

      {!loading && (
        <>
          {/* The page names one step before it lists anything (İ1), and names it once: the list below is the
              rest. "Başla" opens the work itself; "Yaptım" waits inside it. */}
          {siradaki ? (
            <NextThing
              eyebrow="Sıradaki"
              // The normalised name, as the list prints it: the raw one put "İkinci Yabancı Dil (Fransızca)" over
              // rows saying "Fransızca" (İ9). Portal titles keep their own casing ([3.3-6]).
              title={odevAdi(siradaki) || 'Ödev'}
              course={dersAdi(siradaki) || undefined}
              due={siradakiTeslim ? `Teslim ${kisaTeslim(siradakiTeslim, simdi)}` : undefined}
              stepMinutes={10}
              actionLabel="Başla"
              onAction={() => pencereyiAc(siradaki)}
            />
          ) : !hata && (
            <EmptyLine>Şu an teslim bekleyen bir işin yok.</EmptyLine>
          )}

          {sonYapilan && (
            <YaptinSatiri className="isler-yaptin" ad={odevAdi(sonYapilan)} durum={sonGeriAl} onGeriAl={sonuGeriAl} />
          )}

          {/* "Ayrıca": Bugün's word for the same thing — the owed work beyond the card (İ9). */}
          {bolum('sonra', 'Ayrıca', sonra, 'yaptim')}

          {!focusMode && upcomingExams.length > 0 && (
            <div className="isler-sinavlar">
              <ContainedList className="isler-liste exams-ahead" kind="on-page" size="lg"
                // A section's name is title case (S38, revised 2026-10-19); its count is "Başlık (n)".
                label={<h2 className="isler-baslik__metin">Yaklaşan Sınavlar <Sayi n={upcomingExams.length} /></h2>}
                // A page to go to, in the list's own action slot: a ghost button with an href (Bugün's "+N iş
                // daha"). A plain click stays in the app; a new-tab click is the browser's (C13).
                action={<Button kind="ghost" size="lg" href="/sinavlar"
                  onClick={e => {
                    if (!uygulamaIcindeAc(e, '/sinavlar')) return
                    e.preventDefault()
                    navigate('/sinavlar')
                  }}>Tüm sınavlar</Button>}>
                {upcomingExams.map(e => {
                  // A timed exam reads like a deadline; an all-day one is its day alone, a week-only or undated
                  // one as the exam page says it ("28 Eyl haftası", "Tarih belirsiz"; C11, C20).
                  const zaman = sinavZamani(e, simdi)
                  const modul = moduleByExam.get(e.id)
                  return (
                    <ContainedListItem key={e.id} className="exams-ahead__row isler-satir"
                      action={modul ? (
                        <Button kind="ghost" size="lg" onClick={() => navigate(`/moduller/${modul.slug}/v${modul.version}`)}>
                          Modülü aç
                        </Button>
                      ) : undefined}>
                      <span className="isler-satir__ic">
                        {/* Live titles often carry the course already ("Özdebir … GİS · İzleme Sınavı"); saying it
                            twice is not information. The mark leads the row either way. */}
                        {!(e.title || '').startsWith(e.course) ? (
                          <span className="isler-satir__ad">
                            <span className="exams-ahead__course">
                              <SubjectLabel course={e.course} family={e.courseFamily} />
                            </span>{' '}
                            <span className="exams-ahead__title">{e.title}</span>
                          </span>
                        ) : (
                          <span className="isler-satir__ad exams-ahead__title">
                            <SubjectLabel course={e.course} family={e.courseFamily}>{e.title}</SubjectLabel>
                          </span>
                        )}
                        {/* "Yeni"/"Değişti" for an exam found or moved in the last 48 hours: grey, in words. */}
                        <SinavEtiketi exam={e} nowMs={simdiMs} />
                        {zaman && <Teslim teslim={zaman} className="exams-ahead__when" />}
                      </span>
                    </ContainedListItem>
                  )
                })}
              </ContainedList>
              <IncelenmediNotu tespit={examData.tespit} />
            </div>
          )}
          {/* Even with nothing ahead the list can be incomplete: say so. */}
          {!focusMode && upcomingExams.length === 0 && <IncelenmediNotu tespit={examData.tespit} />}
          {!focusMode && sinavHatasi && upcomingExams.length === 0 && (
            <p className="tedy-empty" role="status">Yaklaşan sınavlar şu an alınamadı.</p>
          )}

          {!focusMode && bolum('yapilan', 'Yapılan', yapilan, 'geri-al')}
          {!focusMode && bolum('tamamlanan', 'Tamamlandı', tamamlanan, null)}
          {!focusMode && bolum('yapilmayan', 'Yapılmayan', yapilmayan, null, true)}
        </>
      )}
    </div>

    {/* Mounted only while open: a closed ComposedModal keeps its ModalHeader in the document outline. */}
    {selectedHw && (
      <ComposedModal ref={modalRef} open size={silinecekBelge ? 'xs' : 'md'} danger={!!silinecekBelge}
        // First focus stays on "Kapat", as before the window had a footer: a window that opens on "Yaptım" turns
        // one stray Enter into a recorded mark (Carbon: a passive-first window focuses its close control).
        selectorPrimaryFocus=".cds--modal-close"
        onClose={() => {
          // Onay açıkken Escape ve kapatma onayı kapatır, ödev penceresini değil.
          if (onayRef.current.belge) {
            if (!onayRef.current.mesgul) setSilinecekBelge(null)
            return false
          }
          if (onayRef.current.mesgul) return false
          pencereyiKapat()
        }}>
        {/* Carbon wires closeModal only into direct ModalHeader/ModalFooter children (Children.toArray +
            cloneElement), so the two states swap each part in place rather than a Fragment. */}
        {silinecekBelge
          ? <ModalHeader title="Bu belge silinsin mi?" iconDescription="Kapat" />
          : <ModalHeader
              title={selectedHw['Ödev Başlığı'] || ''}
              label={selectedHw.normalized_course || selectedHw['Ders Adı'] || ''}
              iconDescription="Kapat"
            />}
        {silinecekBelge
          ? <ModalBody>
              <p>“{silinecekBelge.name}” bu ödevden silinir; asistan onu artık okuyamaz. Bu geri alınamaz.</p>
            </ModalBody>
          : <ModalBody>
              <HomeworkModalBody
                hw={selectedHw}
                simdi={simdi}
                enrichmentData={enrichmentData}
                docBusy={docBusy}
                docError={docError}
                onPickDocument={file => void addDocument(file)}
                onRemoveDocument={doc => { setDocError(''); setSilinecekBelge(doc) }}
              />
              {selectedHw.homework_key && <Button className="homework-modal__asistan" kind="tertiary" size="lg" renderIcon={Chat}
                onClick={() => odeviAsistanaSor(selectedHw)}>Asistana sor</Button>}
              {pencereHatasi && (
                <InlineNotification className="homework-modal__hata" kind="error" role="alert" lowContrast hideCloseButton
                  statusIconDescription="Hata" title="Kaydedilemedi" subtitle="Bağlantını kontrol edip yeniden dene." />
              )}
            </ModalBody>}
        {silinecekBelge ? (
          <ModalFooter danger primaryButtonText="Belgeyi sil" secondaryButtonText="Vazgeç"
            loadingStatus={docBusy ? 'active' : 'inactive'} loadingDescription="Siliniyor…"
            onRequestClose={() => { if (!docBusy) setSilinecekBelge(null) }}
            loadingIconDescription="Siliniyor"
            onRequestSubmit={() => { if (!docBusy) void removeDocument(silinecekBelge.id) }}>{null}</ModalFooter>
        ) : aktifAnahtarlar.has(eylemAnahtari(selectedHw)) ? (
          // The window "Başla" opened is where the work ends: "Yaptım" is its one action (İ9: Başla → Yaptım,
          // as Bugün's box). A transient surface may carry its own primary (Carbon, talimatname §4.2).
          <ModalFooter primaryButtonText="Yaptım"
            loadingStatus={pencereKaydediyor ? 'active' : 'inactive'} loadingDescription="Kaydediliyor…"
            loadingIconDescription="Kaydediliyor"
            onRequestSubmit={() => void pencerdeYaptim()}>{null}</ModalFooter>
        ) : null}
      </ComposedModal>
    )}
    </>
  )
}

/* ── Parts ────────────────────────────────────────────────────────────────── */

/** A count in a section heading: "Ayrıca (2)" is said as "Ayrıca 2" and drawn as a chip. */
function Sayi({ n }: { n: number }) {
  return <span className="hw-section__count"><span className="tedy-time">{n}</span></span>
}

/** A day and a time; red with an icon and the word "Bugün" only when it is due today (§2.7, S4). */
function Teslim({ teslim, className = '' }: { teslim: { metin: string; bugun: boolean }; className?: string }) {
  return (
    <span className={['isler-satir__teslim', teslim.bugun && 'isler-satir__teslim--bugun', className]
      .filter(Boolean).join(' ')}>
      {teslim.bugun && <WarningFilled size={16} aria-hidden="true" />}
      <Rakamli metin={teslim.metin} />
    </span>
  )
}

/**
 * A titled group of rows. The heading is a real h2 holding the toggle ("Başlık (n) ⌄", surface designs §2.5),
 * drawn like Carbon's on-page list header; the rows are a Carbon on-page contained list, lg (48px).
 */
function IsBolumu({ id, sinif, baslik, sayi, acik, onToggle, children }: {
  id: string; sinif: string; baslik: string; sayi: number; acik: boolean; onToggle: () => void; children: ReactNode
}) {
  return (
    <section className={`isler-bolum isler-bolum--${sinif}`}>
      <h2 className="isler-baslik">
        <button type="button" className="isler-baslik__dugme" aria-expanded={acik} aria-controls={id} onClick={onToggle}>
          <span className="isler-baslik__metin">{baslik} <Sayi n={sayi} /></span>
          {acik ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
        </button>
      </h2>
      <div id={id} hidden={!acik}>
        {acik && (
          <ContainedList className={`isler-liste isler-liste--${sinif}`} kind="on-page" size="lg">
            {children}
          </ContainedList>
        )}
      </div>
    </section>
  )
}

/** The teacher's verdict, where a group holds more than one kind (Yapılmayan: "Yapmadı", "Eksik"). */
function kararEtiketi(hw: HomeworkItem): ReactNode {
  const durum = normalizeStatus(hw['Ödev Durumu'])
  if (durum !== 'Yapmadı' && durum !== 'Eksik') return null
  const status = getHomeworkStatus(durum)
  // [3.2-8]: a status tag is red or grey; warm-gray belongs to the Din ve değerler family. S4/B16: each carries
  // its icon as a child (Carbon draws renderIcon only from md up, K4-13) — Carbon's "incomplete" for Eksik.
  return (
    <Tag type={status.type === 'red' ? 'red' : 'gray'} size="sm" className="isler-satir__karar">
      {status.type === 'red' ? <CloseFilled size={16} /> : <Incomplete size={16} />} {status.label}
    </Tag>
  )
}

/**
 * One row: the subject mark and the work's name, its verdict where one tells rows apart, and when it is due.
 * The whole row is Carbon's clickable item — one button that opens the work (B46) — and its one action
 * sits beside it, described by the row's name.
 */
function IsSatiri({ hw, simdi, onOpen, eylem, karar }: {
  hw: HomeworkItem
  simdi: Date
  onOpen: (hw: HomeworkItem) => void
  eylem?: (adId: string) => ReactNode
  karar: ReactNode
}) {
  const adId = useId()
  const t = teslimi(hw)
  const teslim = t ? teslimMetni(t, simdi) : null
  return (
    <ContainedListItem className="homework-item isler-satir" onClick={() => onOpen(hw)}
      action={eylem?.(adId)}>
      <span className="isler-satir__ic">
        <span className="isler-satir__ad" id={adId}>
          <SubjectLabel course={dersAdi(hw)}>{odevAdi(hw)}</SubjectLabel>
        </span>
        {karar}
        {teslim && <Teslim teslim={teslim} />}
      </span>
    </ContainedListItem>
  )
}

/** The page's shape while the first answer is late (S36, B48): the panel, then rows. */
function IslerIskeleti() {
  return (
    <div className="isler-iskelet">
      <SkeletonPlaceholder className="isler-iskelet__kart" />
      <SkeletonText heading width="20%" />
      <SkeletonText paragraph lineCount={3} />
    </div>
  )
}

/* ── HomeworkModalBody ───────────────────────────────────────────────────── */

function HomeworkModalBody({
  hw, simdi, enrichmentData, docBusy, docError, onPickDocument, onRemoveDocument,
}: {
  hw: HomeworkItem
  simdi: Date
  enrichmentData: Record<string, { course: string; title: string; note: string; type: string }>
  docBusy: boolean
  docError: string
  onPickDocument: (file: File) => void
  onRemoveDocument: (doc: HomeworkDocument) => void
}) {
  const deadline = teslimi(hw)
  const teslim = deadline ? teslimMetni(deadline, simdi) : null
  const status = hw.student_marked_done
    ? { label: 'Yapılan', type: 'gray' as const }
    : getHomeworkStatus(hw['Ödev Durumu'])

  const enrichKey = `${hw.normalized_course || hw['Ders Adı']}|${hw['Ödev Başlığı']}`
  const enrichNote = enrichmentData?.[enrichKey]?.note

  const descParagraphs = hw.detail?.description
    ? hw.detail.description.split('\n').filter(l => l.trim())
    : []

  return (
    <div className="homework-modal__body">
      <div className="homework-modal__meta">
        <Tag type={status.type === 'warm-gray' ? 'gray' : status.type} size="md">
          {status.type === 'green' && <CheckmarkFilled size={16} />}
          {status.type === 'red' && <CloseFilled size={16} />}
          {hw.student_marked_done && <CheckmarkOutline size={16} />}
          {' '}{status.label}
        </Tag>
        {hw['Ödev Kaynağı'] && (
          <span className="homework-modal__source">{hw['Ödev Kaynağı']}</span>
        )}
      </div>

      {/* When it is due, in the list's own words; the full date beside it for the record. */}
      {teslim && (
        <div className="homework-modal__deadline-row">
          <span className="homework-modal__deadline-label">Son teslim</span>
          <Teslim teslim={teslim} />
          <span className="homework-modal__deadline-value">
            <Rakamli metin={formatTurkishDate(hw['Ödev Son Teslim Tarihi'])} />
          </span>
        </div>
      )}

      {formatTurkishDate(hw.first_seen) && (
        <div className="homework-modal__deadline-row">
          <span className="homework-modal__deadline-label">İlk görülme</span>
          <span className="homework-modal__deadline-value">
            <Rakamli metin={formatTurkishDate(hw.first_seen)} />
          </span>
        </div>
      )}

      {descParagraphs.length > 0 && (
        <div className="homework-modal__description">
          {descParagraphs.map((para, i) => (
            <p key={i} className="homework-modal__description-para">{para}</p>
          ))}
        </div>
      )}

      <div className="homework-modal__attachments">
        <h3 className="homework-modal__attachments-title">Ekler</h3>
        <ul className="homework-modal__attachment-list">
          {(hw.detail?.attachments || []).map((ek, i) => (
            <li key={ek.id ?? `${i}-${ek.url}`}><EkBaglantisi ek={ek} /></li>
          ))}
        </ul>
        {(hw.documents || []).map(doc => (
          <div key={doc.id} className="homework-modal__doc">
            <a href={`/api/homework/documents/${doc.id}`} className="homework-modal__attachment-link">
              <Document size={16} /> {doc.name}
            </a>
            {doc.error && <p className="homework-modal__doc-error" role="alert">{doc.error}</p>}
            {/* B23: silme önce sorar; düğmenin adı nesneyi taşır (birden çok belgede her "Kaldır" ayırt edilir). */}
            <Button kind="ghost" size="sm" disabled={docBusy} aria-label={`Kaldır: ${doc.name}`}
              onClick={() => onRemoveDocument(doc)}>
              Kaldır
            </Button>
          </div>
        ))}
        <YuklemeAlani belge disabled={docBusy} onDosyalar={files => { if (files[0]) onPickDocument(files[0]) }} />
        <p className="homework-modal__doc-hint">
          Eklenen belge yalnız bu ödev sorulurken asistana açılır.
        </p>
        {docError && <p className="homework-modal__doc-error" role="alert">{docError}</p>}
      </div>

      {enrichNote && (
        // B41/B32: kaldırılmış ürün adı ve emoji yok; not yapay zekânın yazdığını söyler, Carbon'un bilgi Callout'unda.
        <Callout className="homework-modal__enrichment" kind="info" lowContrast title="Yapay zekâ notu">
          <span className="homework-modal__enrichment-text">{enrichNote}</span>
        </Callout>
      )}
    </div>
  )
}
