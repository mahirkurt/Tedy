import { useState, useEffect, useMemo } from 'react'
import { Tag, Tile, ComposedModal, ModalHeader, ModalBody, Button, InlineLoading } from '@carbon/react'
import { Task, Timer, Document, CheckmarkFilled, CloseFilled, ChevronDown, ChevronUp } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { HomeworkItem } from '../types'
import { parseDeadline, formatTurkishDate, getHomeworkStatus } from '../utils/formatters'
import { getCountdown } from '../utils/countdown'
import { NextThing } from './NextThing'
import { describeDaysAhead } from './patterns/time'
import './patterns/patterns.scss'
import { useNavigate } from 'react-router-dom'
import type { ExamItem } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import { useFocusMode } from '../contexts/focusMode'

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
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 60000)
    return () => clearInterval(t)
  }, [])

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


  // A working state, not a dimmer: focus closes the lists and leaves the one
  // named thing, with the counts still visible so nothing feels lost (§5).
  const isCollapsed = (key: HomeworkGroupKey) => focusMode || collapsed[key]

  const toggleSection = (key: HomeworkGroupKey) => {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleMarkDone = async (hw: HomeworkItem) => {
    const fallbackKey = `${hw["Ders Adı"]}|${hw["Ödev Başlığı"]}|${hw["Ödev Son Teslim Tarihi"]}`
    const key = hw.homework_key || fallbackKey
    setMarkingKey(key)
    try {
      const res = await fetch('/api/homework/mark-done', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          homework_key: hw.homework_key,
          "Ders Adı": hw["Ders Adı"],
          "Ödev Başlığı": hw["Ödev Başlığı"],
          "Ödev Son Teslim Tarihi": hw["Ödev Son Teslim Tarihi"],
        }),
      })
      if (res.ok) {
        refreshHomework()
        window.dispatchEvent(new Event('tedy:homework-updated'))
      }
    } finally {
      setMarkingKey(null)
    }
  }

  const renderAccordionSection = ({
    keyName,
    title,
    labelClass,
    items,
    showDoneAction,
  }: {
    keyName: HomeworkGroupKey
    title: string
    labelClass?: string
    items: HomeworkItem[]
    showDoneAction?: boolean
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
          <span className={["hw-section__label", labelClass].filter(Boolean).join(' ')}>{title}</span>
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
      <h2 className="dashboard-card__title dashboard-card__title--tight">
        <Task size={20} />
        İşler
      </h2>

      {/* The page names one step before it lists anything (İ1). "Başla" opens
          the work itself, so the verb keeps its meaning through the flow. */}
      {nextHw && (
        <NextThing
          eyebrow="SIRADAKİ"
          title={[
            String(nextHw["Ders Adı"] || '').trim(),
            String(nextHw["Ödev Başlığı"] || '').trim(),
          ].filter(Boolean).join(' — ') || 'Ödev'}
          stepMinutes={10}
          actionLabel="Başla"
          onAction={() => setSelectedHw(nextHw)}
        />
      )}

      {renderAccordionSection({
        keyName: 'aktif',
        title: 'Aktif Ödevler',
        items: aktif,
        showDoneAction: true,
      })}

      {upcomingExams.length > 0 && (
        <div className="hw-section exams-ahead">
          <div className="hw-section__header">
            <span className="hw-section__label">Yaklaşan Sınavlar</span>
            <span className="hw-section__count">{upcomingExams.length}</span>
          </div>
          {!focusMode && <ul className="exams-ahead__list">
            {upcomingExams.map(e => {
              const when = e.date ? new Date(e.date) : null
              return (
                <li key={e.id} className="exams-ahead__row">
                  <span className="exams-ahead__course">{e.course}</span>
                  <span className="exams-ahead__title">{e.title}</span>
                  {when && (
                    <span className="exams-ahead__when tedy-time">
                      {describeDaysAhead(when)}
                    </span>
                  )}
                </li>
              )
            })}
          </ul>}
          {!focusMode && (
            <Button kind="ghost" size="sm" onClick={() => navigate('/sinavlar')}>
              Tüm sınavlar
            </Button>
          )}
        </div>
      )}

      {renderAccordionSection({
        keyName: 'yapilan',
        title: 'YAPILAN',
        labelClass: 'hw-section__label--info',
        items: yapilan,
      })}

      {renderAccordionSection({
        keyName: 'tamamlanan',
        title: 'Tamamlandı',
        labelClass: 'hw-section__label--success',
        items: tamamlanan,
      })}

      {renderAccordionSection({
        keyName: 'yapilmayan',
        title: 'Yapılmayan',
        labelClass: 'hw-section__label--error',
        items: yapilmayan,
      })}

      {aktif.length === 0 && yapilan.length === 0 && tamamlanan.length === 0 && yapilmayan.length === 0 && (
        <EmptyLine>Bu bölümde iş yok.</EmptyLine>
      )}
    </div>

    {/* Mounted only while open: a closed ComposedModal keeps its
        ModalHeader in the document outline. */}
    {selectedHw && (
      <ComposedModal open onClose={() => setSelectedHw(null)} size="md">
        <ModalHeader
          title={selectedHw["Ödev Başlığı"] || ''}
          label={selectedHw.normalized_course || selectedHw["Ders Adı"] || ''}
        />
        <ModalBody>
          <HomeworkModalBody hw={selectedHw} enrichmentData={enrichmentData} />
        </ModalBody>
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
}: {
  hw: HomeworkItem
  onOpen: (hw: HomeworkItem) => void
  showDoneAction?: boolean
  onDone?: (hw: HomeworkItem) => void
  doneLoading?: boolean
}) {
  const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
  const countdown = getCountdown(deadline)

  const status = hw.student_marked_done
    ? { label: 'YAPILAN', type: 'blue' as const }
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
      onClick={() => onOpen(hw)}
      className={['homework-item', 'dashboard-list-tile', 'homework-item--clickable', borderClass].join(' ')}
    >
      <div className="homework-item__row">
        <div className="homework-item__main">
          <div className="homework-item__course">
            {hw.normalized_course || hw["Ders Adı"]}
            {(hw.student_marked_done || (hw["Ödev Durumu"] && hw["Ödev Durumu"] !== 'Değerlendirilmemiş')) && (
              <Tag
                type={status.type}
                size="sm"
                className="homework-item__status-badge"
              >
                {status.type === 'green'
                  ? <CheckmarkFilled size={12} />
                  : status.type === 'red'
                    ? <CloseFilled size={12} />
                    : null}
                {' '}{status.label}
              </Tag>
            )}
          </div>
          <div className="homework-item__title">{hw["Ödev Başlığı"]}</div>
          <div className="homework-item__deadline">
            Teslim: {formatTurkishDate(hw["Ödev Son Teslim Tarihi"])}
          </div>
          {formatTurkishDate(hw.first_seen) && (
            <div className="homework-item__first-seen" style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary, #525252)', marginTop: '2px' }}>
              İlk görülme: {formatTurkishDate(hw.first_seen)}
            </div>
          )}
        </div>
        <div className="homework-item__countdown">
          {countdown.urgency !== 'expired' && (
            <div className={countdown.urgency === 'critical' || countdown.urgency === 'urgent' ? 'tag-urgent' : ''}>
              <Tag type={countdown.urgency === 'critical' ? 'red' : countdown.urgency === 'urgent' ? 'red' : countdown.urgency === 'soon' ? 'warm-gray' : 'blue'} size="sm">
                <Timer size={12} /> {countdown.text}
              </Tag>
            </div>
          )}
          {countdown.urgency === 'expired' && !hw.student_marked_done && (
            <Tag type="warm-gray" size="sm">Süresi doldu</Tag>
          )}

          {showDoneAction && onDone && (
            <div
              className="homework-item__action"
              onClick={(e) => {
                e.stopPropagation()
              }}
            >
              {doneLoading ? (
                <InlineLoading description="Kaydediliyor" status="active" />
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

function HomeworkModalBody({ hw, enrichmentData }: { hw: HomeworkItem; enrichmentData: Record<string, { course: string; title: string; note: string; type: string }> }) {
  const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
  const countdown = getCountdown(deadline)
  const status = hw.student_marked_done
    ? { label: 'YAPILAN', type: 'blue' as const }
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
            type={countdown.urgency === 'critical' || countdown.urgency === 'urgent' ? 'red' : countdown.urgency === 'soon' ? 'warm-gray' : 'blue'}
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
        <div className="homework-modal__deadline-row" style={{ marginTop: '0.25rem' }}>
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

      {/* Attachments */}
      {(hw.detail?.attachments?.length ?? 0) > 0 && (
        <div className="homework-modal__attachments">
          <h5 className="homework-modal__attachments-title">Ekler</h5>
          {hw.detail!.attachments.map((att, i) => (
            <a key={i} href={att.url} target="_blank" rel="noopener noreferrer"
               className="homework-modal__attachment-link">
              <Document size={16} /> {att.name}
            </a>
          ))}
        </div>
      )}

      {enrichNote && (
        <div className="homework-modal__enrichment">
          <h5 className="homework-modal__enrichment-title">🤖 Gemini Notu</h5>
          <p className="homework-modal__enrichment-text">{enrichNote}</p>
        </div>
      )}
    </div>
  )
}
