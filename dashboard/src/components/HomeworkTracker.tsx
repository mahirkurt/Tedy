import { useState, useEffect, useMemo, useRef } from 'react'
import { Tag, Tile, ComposedModal, ModalHeader, ModalBody, ModalFooter, Button, InlineLoading, Link, Callout, Layer } from '@carbon/react'
import { Timer, CheckmarkFilled, CheckmarkOutline, CloseFilled, ChevronDown, ChevronUp, Document, Chat } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { HomeworkDocument, HomeworkItem } from '../types'
import { parseDeadline, formatTurkishDate, getHomeworkStatus } from '../utils/formatters'
import { countdownTagType, getCountdown } from '../utils/countdown'
import SubjectLabel from './SubjectLabel'
import { NextThing } from './NextThing'
import { describeDaysAhead } from './patterns/time'
import './patterns/patterns.scss'
import { useNavigate } from 'react-router-dom'
import { acikOgeAc, asistanaSor } from '../asistan/sayfaBaglami'
import type { ExamItem, ModuleCard } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import { EkBaglantisi } from './patterns/EkBaglantisi'
import { useFocusMode } from '../contexts/focusMode'
import YuklemeAlani from './YuklemeAlani'
import { yaptimIsaretle, yaptimGeriAl } from '../utils/odevYaptim'
import { YaptinSatiri, type GeriAlDurumu } from './patterns/YaptinSatiri'

const odevAdi = (hw: HomeworkItem) =>
  [hw.normalized_course || hw['Ders Adı'], hw['Ödev Başlığı']].filter(Boolean).join(' — ')
const eylemAnahtari = (hw: HomeworkItem) =>
  hw.homework_key || `${hw['Ders Adı']}|${hw['Ödev Başlığı']}|${hw['Ödev Son Teslim Tarihi']}`

type HomeworkGroupKey = 'aktif' | 'yapilan' | 'tamamlanan' | 'yapilmayan'

function normalizeStatus(value: string): 'Yaptı' | 'Yapmadı' | 'Eksik' | 'Değerlendirilmemiş' | string {
  const raw = (value || '').trim().toLocaleLowerCase('tr-TR')
  if (['yaptı', 'yapti', 'tamamlandı', 'tamamlandi', 'done'].includes(raw)) return 'Yaptı'
  if (['yapmadı', 'yapmadi', 'missing', 'incomplete'].includes(raw)) return 'Yapmadı'
  if (raw === 'eksik') return 'Eksik'
  if (['değerlendirilmemiş', 'degerlendirilmemis', 'bekliyor', 'pending'].includes(raw)) return 'Değerlendirilmemiş'
  return value
}

function isTeacherResolvedStatus(status: string): boolean {
  const n = normalizeStatus(status)
  return n === 'Yaptı' || n === 'Yapmadı' || n === 'Eksik'
}

export default function HomeworkTracker() {
  const { data: hwData, refresh: refreshHomework } = useApi<{ summary: string; homework: HomeworkItem[] }>(
    '/api/homework', { summary: '', homework: [] }
  )
  const { data: enrichmentData } = useApi<Record<string, { course: string; title: string; note: string; type: string }>>(
    '/api/enrichment', {}
  )

  const [selectedHw, setSelectedHw] = useState<HomeworkItem | null>(null)
  const gezin = useNavigate()
  // "Asistana sor" (B78): ödev penceresi açıkken asistan paneli onun altındadır (B61); pencere kapanır, ödev sonraki
  // sorunun bağlamı olarak sabitlenir ve panel açılır — başlatıcı yoksa (telefon, odak kipi) Asistan sayfasına gidilir.
  function odeviAsistanaSor(hw: HomeworkItem) {
    if (!hw.homework_key) return
    const karsilandi = asistanaSor({ tur: 'odev', id: hw.homework_key,
      etiket: `${hw.normalized_course || hw['Ders Adı']} — ${hw['Ödev Başlığı']}` })
    setSelectedHw(null)
    if (!karsilandi) gezin('/asistan?sayfa=isler')
  }
  const [, setTick] = useState(0)
  const { focusMode } = useFocusMode()
  const [collapsed, setCollapsed] = useState<Record<HomeworkGroupKey, boolean>>({
    aktif: false,
    // Sections that need action open; everything settled starts closed (İ7).
    // With this open, twelve finished items filled the screen while nothing
    // was due.
    yapilan: true,
    tamamlanan: true,
    yapilmayan: true,
  })
  const [markingKey, setMarkingKey] = useState<string | null>(null)
  // The row whose "Yaptım" could not be stored. It used to fail in silence —
  // the button simply came back, and nothing said the mark was not kept (D3).
  const [markErrorKey, setMarkErrorKey] = useState<string | null>(null)
  // B63 (S40): the work "Yaptım" just recorded, said under the active list
  // with "Geri al" on the same line, as on Bugün; and the row whose undo is
  // in flight or failed in "Yapılan", where every mark of Işık's own can be
  // taken back later too.
  const [sonYapilan, setSonYapilan] = useState<HomeworkItem | null>(null)
  const [sonGeriAl, setSonGeriAl] = useState<GeriAlDurumu>('bos')
  const [geriAlinanKey, setGeriAlinanKey] = useState<string | null>(null)
  const [geriAlHataKey, setGeriAlHataKey] = useState<string | null>(null)
  const [docBusy, setDocBusy] = useState(false)
  const [docError, setDocError] = useState('')
  // B23 (S40): silinecek belge. Ödev penceresi aynı yerde tehlike onayına döner; pencerenin üstüne ikinci bir
  // pencere açılmaz.
  const [silinecekBelge, setSilinecekBelge] = useState<HomeworkDocument | null>(null)
  const modalRef = useRef<HTMLDivElement>(null)
  // Carbon's Escape listener keeps the onClose of the render it was registered in, so onClose reads the live
  // state through refs — otherwise Escape on the confirmation closed the whole homework window.
  const onayRef = useRef<{ belge: HomeworkDocument | null; mesgul: boolean }>({ belge: null, mesgul: false })
  useEffect(() => { onayRef.current = { belge: silinecekBelge, mesgul: docBusy } }, [silinecekBelge, docBusy])
  useEffect(() => {
    if (!silinecekBelge) return
    // Onay açılırken ilk odak "Vazgeç"te (Carbon tehlike modalı); pencere zaten açık olduğu için elle verilir.
    const kare = requestAnimationFrame(() => {
      modalRef.current?.querySelector<HTMLButtonElement>('.cds--modal-footer .cds--btn--secondary')?.focus()
    })
    return () => cancelAnimationFrame(kare)
  }, [silinecekBelge])
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 60000)
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

  const grouped = useMemo(() => {
    const aktif: HomeworkItem[] = []
    const yapilan: HomeworkItem[] = []
    const tamamlanan: HomeworkItem[] = []
    const yapilmayan: HomeworkItem[] = []

    for (const hw of (hwData.homework || [])) {
      const normalized = normalizeStatus(hw["Ödev Durumu"])
      const teacherResolved = isTeacherResolvedStatus(normalized)

      if (normalized === 'Yaptı') {
        tamamlanan.push(hw)
        continue
      }

      if (normalized === 'Yapmadı' || normalized === 'Eksik') {
        yapilmayan.push(hw)
        continue
      }

      if (hw.student_marked_done && !teacherResolved) {
        yapilan.push(hw)
        continue
      }

      const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
      const countdown = getCountdown(deadline)
      if (countdown.urgency !== 'expired') {
        aktif.push(hw)
      } else {
        yapilmayan.push(hw)
      }
    }

    // Two orders, because the groups answer two different questions.
    // Work still to do is sorted nearest-deadline-first: the thing due
    // tomorrow has to be reachable without scrolling past four things due
    // next month (İ2, İ3). Everything settled is history, and history reads
    // newest-first.
    const byDeadline = (dir: 1 | -1) => (a: HomeworkItem, b: HomeworkItem) => {
      const at = parseDeadline(a["Ödev Son Teslim Tarihi"])?.getTime()
      const bt = parseDeadline(b["Ödev Son Teslim Tarihi"])?.getTime()
      // A row with no readable deadline sinks in both orders rather than
      // sorting as 1970 (nearest) or as the far future (least urgent).
      if (at === undefined && bt === undefined) return 0
      if (at === undefined) return 1
      if (bt === undefined) return -1
      return (at - bt) * dir
    }
    aktif.sort(byDeadline(1))
    for (const past of [yapilan, tamamlanan, yapilmayan]) past.sort(byDeadline(-1))

    return { aktif, yapilan, tamamlanan, yapilmayan }
  }, [hwData.homework])

  const { aktif, yapilan, tamamlanan, yapilmayan } = grouped

  // The list now leads with the nearest deadline, so its head is the one
  // named step (İ1). This used to scan for the minimum because the list was
  // ordered the other way round.
  const nextHw = aktif[0] ?? null

  // Exams share this surface because they are the same thing to Işık: work she
  // owes with a date on it. Only the ones still ahead — the settled ones are
  // history and belong on the exam page (İ7).
  const { data: examData } = useApi<{ exams: ExamItem[] }>('/api/exams', { exams: [] })
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


  // A working state, not a dimmer: focus closes the lists and leaves the one
  // named thing, with the counts still visible so nothing feels lost (§5).
  const isCollapsed = (key: HomeworkGroupKey) => focusMode || collapsed[key]

  const toggleSection = (key: HomeworkGroupKey) => {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }))
  }

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

  // "Geri al" (S40, B63): the mark goes and the work is active again. The
  // line under the list and a row in "Yapılan" use the same call.
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

  const renderAccordionSection = ({
    keyName,
    title,
    items,
    showDoneAction,
    showUndoAction,
  }: {
    keyName: HomeworkGroupKey
    title: string
    items: HomeworkItem[]
    showDoneAction?: boolean
    showUndoAction?: boolean
  }) => {
    if (items.length === 0) return null
    return (
      <div className="hw-section" key={keyName}>
        <button
          className="hw-section__header hw-section__header--toggle"
          onClick={() => toggleSection(keyName)}
          aria-expanded={!isCollapsed(keyName)}
          type="button"
        >
          {/* Neutral like "Aktif Ödevler": a settled group's label was painted
              blue, green or red, putting history in colour above the work
              still owed (İ7), and red is kept for urgency. */}
          <span className="hw-section__label">{title}</span>
          <span className="hw-section__count">{items.length}</span>
          {isCollapsed(keyName) ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </button>
        {!isCollapsed(keyName) && (
          <div className="stack-sm">
            {items.map((hw, i) => {
              const actionKey = hw.homework_key || `${hw["Ders Adı"]}|${hw["Ödev Başlığı"]}|${hw["Ödev Son Teslim Tarihi"]}`
              const isMarking = markingKey === actionKey
              return (
                <HomeworkCard
                  key={`${keyName}-${i}`}
                  hw={hw}
                  onOpen={setSelectedHw}
                  showDoneAction={showDoneAction}
                  onDone={showDoneAction ? handleMarkDone : undefined}
                  doneLoading={isMarking}
                  doneError={markErrorKey === actionKey}
                  onUndo={showUndoAction && hw.student_marked_done ? satiriGeriAl : undefined}
                  undoLoading={geriAlinanKey === actionKey}
                  undoError={geriAlHataKey === actionKey}
                />
              )
            })}
          </div>
        )}
      </div>
    )
  }

  return (
    <>
    <div className="dashboard-card">
      {/* The page heading lives on the shell. A second visible "İşler" here
          was the same word twice in the outline. */}

      {/* The page names one step before it lists anything (İ1). "Başla" opens
          the work itself, so the verb keeps its meaning through the flow. */}
      {/* One layer up from the card it sits in (B31): Carbon's contextual tokens, not a hand-paired colour. */}
      {nextHw && (
        <Layer>
        <NextThing
          eyebrow="Sıradaki"
          // The normalised name, as the list below prints it: the raw one put
          // "İkinci Yabancı Dil (Fransızca)" over rows saying "Fransızca" (İ9).
          title={[
            String(nextHw.normalized_course || nextHw["Ders Adı"] || '').trim(),
            String(nextHw["Ödev Başlığı"] || '').trim(),
          ].filter(Boolean).join(' — ') || 'Ödev'}
          course={String(nextHw.normalized_course || nextHw["Ders Adı"] || '').trim() || undefined}
          stepMinutes={10}
          actionLabel="Başla"
          onAction={() => setSelectedHw(nextHw)}
        />
        </Layer>
      )}

      {aktif.length === 0 && (
        <EmptyLine>Şu an teslim bekleyen bir işin yok.</EmptyLine>
      )}

      {sonYapilan && (
        <YaptinSatiri className="isler-yaptin" ad={odevAdi(sonYapilan)} durum={sonGeriAl} onGeriAl={sonuGeriAl} />
      )}

      {renderAccordionSection({
        keyName: 'aktif',
        title: 'Aktif ödevler',
        items: aktif,
        showDoneAction: true,
      })}

      {!focusMode && upcomingExams.length > 0 && (
        <div className="hw-section exams-ahead">
          <div className="hw-section__header">
            <span className="hw-section__label">Yaklaşan sınavlar</span>
            <span className="hw-section__count">{upcomingExams.length}</span>
          </div>
          {!focusMode && <ul className="exams-ahead__list">
            {upcomingExams.map(e => {
              const when = e.date ? new Date(e.date) : null
              return (
                <li key={e.id} className="exams-ahead__row">
                  {/* Live titles often carry the course already ("Özdebir …
                      GİS · İzleme Sınavı"); saying it twice is not information. */}
                  {/* The mark leads the row: on the course when it is printed,
                      on the title when the title already names it. */}
                  {!(e.title || '').startsWith(e.course) ? (
                    <>
                      <span className="exams-ahead__course">
                        <SubjectLabel course={e.course} family={e.courseFamily} />
                      </span>
                      <span className="exams-ahead__title">{e.title}</span>
                    </>
                  ) : (
                    <span className="exams-ahead__title">
                      <SubjectLabel course={e.course} family={e.courseFamily}>{e.title}</SubjectLabel>
                    </span>
                  )}
                  {when && (
                    <span className="exams-ahead__when tedy-time">
                      {describeDaysAhead(when)}
                    </span>
                  )}
                  {moduleByExam.has(e.id) && (
                    <Button kind="ghost" size="sm" className="exams-ahead__module"
                      onClick={() => {
                        const m = moduleByExam.get(e.id)!
                        navigate(`/moduller/${m.slug}/v${m.version}`)
                      }}>
                      Modülü aç
                    </Button>
                  )}
                </li>
              )
            })}
          </ul>}
          {/* A link, not a ghost button: it goes to a page, and the button's
              padding set its text 16px off the list's edge. */}
          {!focusMode && (
            <Link
              href="/sinavlar"
              className="exams-ahead__all"
              onClick={e => { e.preventDefault(); navigate('/sinavlar') }}
            >
              Tüm sınavlar
            </Link>
          )}
        </div>
      )}

      {!focusMode && renderAccordionSection({
        keyName: 'yapilan',
        title: 'Yapılan',
        items: yapilan,
        showUndoAction: true,
      })}

      {!focusMode && renderAccordionSection({
        keyName: 'tamamlanan',
        title: 'Tamamlandı',
        items: tamamlanan,
      })}

      {!focusMode && renderAccordionSection({
        keyName: 'yapilmayan',
        title: 'Yapılmayan',
        items: yapilmayan,
      })}
    </div>

    {/* Mounted only while open: a closed ComposedModal keeps its
        ModalHeader in the document outline. */}
    {selectedHw && (
      <ComposedModal ref={modalRef} open size={silinecekBelge ? 'xs' : 'md'} danger={!!silinecekBelge}
        onClose={() => {
          // Onay açıkken Escape ve kapatma onayı kapatır, ödev penceresini değil.
          if (onayRef.current.belge) {
            if (!onayRef.current.mesgul) setSilinecekBelge(null)
            return false
          }
          setSelectedHw(null)
        }}>
        {/* Carbon wires closeModal only into direct ModalHeader/ModalFooter children (Children.toArray +
            cloneElement), so the two states swap each part in place rather than a Fragment. */}
        {silinecekBelge
          ? <ModalHeader title="Bu belge silinsin mi?" iconDescription="Kapat" />
          : <ModalHeader
              title={selectedHw["Ödev Başlığı"] || ''}
              label={selectedHw.normalized_course || selectedHw["Ders Adı"] || ''}
              iconDescription="Kapat"
            />}
        {silinecekBelge
          ? <ModalBody>
              <p>“{silinecekBelge.name}” bu ödevden silinir; asistan onu artık okuyamaz. Bu geri alınamaz.</p>
            </ModalBody>
          : <ModalBody>
              <HomeworkModalBody
                hw={selectedHw}
                enrichmentData={enrichmentData}
                docBusy={docBusy}
                docError={docError}
                onPickDocument={file => void addDocument(file)}
                onRemoveDocument={doc => { setDocError(''); setSilinecekBelge(doc) }}
              />
              {selectedHw.homework_key && <Button className="homework-modal__asistan" kind="tertiary" size="lg" renderIcon={Chat}
                onClick={() => odeviAsistanaSor(selectedHw)}>Asistana sor</Button>}
            </ModalBody>}
        {silinecekBelge && (
          <ModalFooter danger primaryButtonText="Belgeyi sil" secondaryButtonText="Vazgeç"
            loadingStatus={docBusy ? 'active' : 'inactive'} loadingDescription="Siliniyor…"
            onRequestClose={() => { if (!docBusy) setSilinecekBelge(null) }}
            loadingIconDescription="Siliniyor"
            onRequestSubmit={() => { if (!docBusy) void removeDocument(silinecekBelge.id) }}>{null}</ModalFooter>
        )}
      </ComposedModal>
    )}
    </>
  )
}

/* ── HomeworkCard ────────────────────────────────────────────────────────── */

function HomeworkCard({
  hw,
  onOpen,
  showDoneAction,
  onDone,
  doneLoading,
  doneError,
  onUndo,
  undoLoading,
  undoError,
}: {
  hw: HomeworkItem
  onOpen: (hw: HomeworkItem) => void
  showDoneAction?: boolean
  onDone?: (hw: HomeworkItem) => void
  doneLoading?: boolean
  doneError?: boolean
  onUndo?: (hw: HomeworkItem) => void
  undoLoading?: boolean
  undoError?: boolean
}) {
  const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
  const countdown = getCountdown(deadline)

  const status = hw.student_marked_done
    ? { label: 'Yapılan', type: 'gray' as const }
    : getHomeworkStatus(hw["Ödev Durumu"])

  // Determine left border class
  let borderClass = ''
  if (hw.student_marked_done) borderClass = 'homework-item--border-info'
  else if (hw["Ödev Durumu"] === 'Yaptı') borderClass = 'homework-item--border-success'
  else if (hw["Ödev Durumu"] === 'Yapmadı' || hw["Ödev Durumu"] === 'Eksik') borderClass = 'homework-item--border-error'
  else if (countdown.urgency === 'expired') borderClass = 'homework-item--border-gray'
  else borderClass = 'homework-item--border-info'

  return (
    <Tile
      // The row opens its homework, except where a click lands on the row's own action ("Yaptım").
      onClick={e => { if (!(e.target as HTMLElement).closest('.homework-item__action')) onOpen(hw) }}
      className={['homework-item', 'dashboard-list-tile', 'homework-item--clickable', borderClass].join(' ')}
    >
      <div className="homework-item__row">
        <div className="homework-item__main">
          <div className="homework-item__course">
            <SubjectLabel course={hw.normalized_course || hw["Ders Adı"]} />
            {(hw.student_marked_done || (hw["Ödev Durumu"] && hw["Ödev Durumu"] !== 'Değerlendirilmemiş')) && (
              <Tag
                type={status.type}
                size="sm"
                className="homework-item__status-badge"
              >
                {/* B21 (S4): Işık'ın kendi işareti gri + ikon; mavi bir ders ailesi gibi okunuyordu. */}
                {status.type === 'green'
                  ? <CheckmarkFilled size={12} />
                  : status.type === 'red'
                    ? <CloseFilled size={12} />
                    : hw.student_marked_done ? <CheckmarkOutline size={12} /> : null}
                {' '}{status.label}
              </Tag>
            )}
          </div>
          {/* B46 (D2): the row opens by keyboard too — the title is a real button (a clickable Tile would nest the
              "Yaptım" button inside another control). The Tile keeps its click for the pointer. */}
          <button type="button" className="homework-item__title homework-item__open"
            onClick={e => { e.stopPropagation(); onOpen(hw) }}>{hw["Ödev Başlığı"]}</button>
          <div className="homework-item__deadline">
            Teslim: {formatTurkishDate(hw["Ödev Son Teslim Tarihi"])}
          </div>
          {formatTurkishDate(hw.first_seen) && (
            <div className="homework-item__first-seen">
              İlk görülme: {formatTurkishDate(hw.first_seen)}
            </div>
          )}
        </div>
        <div className="homework-item__countdown">
          {countdown.urgency !== 'expired' && (
            <div className={countdown.urgency === 'critical' || countdown.urgency === 'urgent' ? 'tag-urgent' : ''}>
              <Tag type={countdownTagType(countdown.urgency)} size="sm">
                <Timer size={12} /> {countdown.text}
              </Tag>
            </div>
          )}
          {countdown.urgency === 'expired' && !hw.student_marked_done && (
            <Tag type="warm-gray" size="sm">Süresi doldu</Tag>
          )}

          {showDoneAction && onDone && (
            <div className="homework-item__action">
              {doneLoading ? (
                <InlineLoading description="Kaydediliyor…" iconDescription="Kaydediliyor" status="active" />
              ) : (
                <Button
                  size="sm"
                  // Tertiary, not primary: the page already has one primary
                  // action in the card at the top, and a screen with several
                  // equally loud buttons is a screen with several decisions (İ1).
                  kind="tertiary"
                  onClick={() => onDone(hw)}
                >
                  Yaptım
                </Button>
              )}
              {doneError && (
                <span className="homework-item__error" role="alert">
                  Kaydedilemedi. Bağlantını kontrol edip yeniden dene.
                </span>
              )}
            </div>
          )}

          {/* B63 (S40): Işık's own "Yaptım" is taken back on its own row. Ghost,
              because a settled row's action is a correction, not a next step (İ1).
              The name carries the homework so a list of them is told apart. */}
          {onUndo && (
            <div className="homework-item__action">
              {undoLoading ? (
                <InlineLoading description="Geri alınıyor…" iconDescription="Geri alınıyor" status="active" />
              ) : (
                <Button size="sm" kind="ghost" aria-label={`Geri al: ${hw["Ödev Başlığı"]}`}
                  onClick={() => onUndo(hw)}>
                  Geri al
                </Button>
              )}
              {undoError && (
                <span className="homework-item__error" role="alert">
                  Geri alınamadı. Bağlantını kontrol edip yeniden dene.
                </span>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="hw-countdown-bar">
        <div
          className={`hw-countdown-bar__fill hw-countdown-bar__fill--${countdown.urgency}`}
          style={{ width: `${countdown.fraction * 100}%` }}
        />
      </div>
    </Tile>
  )
}

/* ── HomeworkModalBody ───────────────────────────────────────────────────── */

function HomeworkModalBody({
  hw, enrichmentData, docBusy, docError, onPickDocument, onRemoveDocument,
}: {
  hw: HomeworkItem
  enrichmentData: Record<string, { course: string; title: string; note: string; type: string }>
  docBusy: boolean
  docError: string
  onPickDocument: (file: File) => void
  onRemoveDocument: (doc: HomeworkDocument) => void
}) {
  const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
  const countdown = getCountdown(deadline)
  const status = hw.student_marked_done
    ? { label: 'Yapılan', type: 'gray' as const }
    : getHomeworkStatus(hw["Ödev Durumu"])

  const enrichKey = `${hw.normalized_course || hw["Ders Adı"]}|${hw["Ödev Başlığı"]}`
  const enrichNote = enrichmentData?.[enrichKey]?.note

  const descParagraphs = hw.detail?.description
    ? hw.detail.description.split('\n').filter(l => l.trim())
    : []

  return (
    <div className="homework-modal__body">
      {/* Status + Meta row */}
      <div className="homework-modal__meta">
        <Tag type={status.type} size="md">
          {status.type === 'green' && <CheckmarkFilled size={14} />}
          {status.type === 'red' && <CloseFilled size={14} />}
          {hw.student_marked_done && <CheckmarkOutline size={14} />}
          {' '}{status.label}
        </Tag>
        {hw["Ödev Kaynağı"] && (
          <span className="homework-modal__source">{hw["Ödev Kaynağı"]}</span>
        )}
      </div>

      {/* Deadline */}
      <div className="homework-modal__deadline-row">
        <span className="homework-modal__deadline-label">Son teslim:</span>
        <span className="homework-modal__deadline-value">
          {formatTurkishDate(hw["Ödev Son Teslim Tarihi"])}
        </span>
        {countdown.urgency !== 'expired' ? (
          <Tag
            type={countdownTagType(countdown.urgency)}
            size="sm"
          >
            <Timer size={12} /> {countdown.text}
          </Tag>
        ) : (
          <Tag type="warm-gray" size="sm">Süresi doldu</Tag>
        )}
      </div>

      {/* First seen */}
      {hw.first_seen && (
        <div className="homework-modal__deadline-row">
          <span className="homework-modal__deadline-label">İlk görülme:</span>
          <span className="homework-modal__deadline-value">
            {formatTurkishDate(hw.first_seen)}
          </span>
        </div>
      )}

      {/* Description */}
      {descParagraphs.length > 0 && (
        <div className="homework-modal__description">
          {descParagraphs.map((para, i) => (
            <p key={i} className="homework-modal__description-para">{para}</p>
          ))}
        </div>
      )}

      <div className="homework-modal__attachments">
        <h5 className="homework-modal__attachments-title">Ekler</h5>
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
