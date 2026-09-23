import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tag } from '@carbon/react'
import {
  Education,
  Bookmark,
  Task as TaskIcon,
  EventSchedule,
  Checkmark,
  ChevronLeft,
  ChevronRight,
  UserAvatar,
} from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { parseDeadline, cleanTeacherNames, toTitleCase, formatTurkishDate, MONTHS_SHORT } from '../utils/formatters'
import { getCountdown, getExamCountdown } from '../utils/countdown'
import { dayColumns } from '../utils/schedule'
import { DayStrip } from './DayStrip'
import { NextThing } from './NextThing'
import { useBookProgress } from '../hooks/useBookReader'
import type { BookSummary } from '../types'
import type { HomeworkItem, CalendarEvent, OgepSession, ExamsApiResponse } from '../types'
import { EmptyLine } from './patterns/EmptyLine'

interface ScheduleData {
  latest: { schedule?: { rows: string[][] } }
  today: string
}

interface AgendaItem {
  time: string
  startMin: number
  endMin: number
  name: string
  subtitle: string
  type: 'lesson' | 'ogep' | 'deadline' | 'private_lesson' | 'event'
  isActive: boolean
  isPast: boolean
  period?: number
}

type IconComponent = typeof Education

type ActiveHomeworkItem = {
  hw: HomeworkItem
  deadline: Date | null
  countdown: ReturnType<typeof getCountdown>
}

const TYPE_CONFIG: Record<AgendaItem['type'], {
  color: string
  tagType: 'blue' | 'teal' | 'red' | 'purple' | 'warm-gray'
  label: string
  icon: IconComponent
}> = {
  lesson:         { color: 'var(--ted-cat-lesson)', tagType: 'blue',      label: '',           icon: Education },
  ogep:           { color: 'var(--ted-cat-ogep)', tagType: 'teal',      label: 'ÖGEP',       icon: Bookmark },
  deadline:       { color: 'var(--ted-cat-homework)', tagType: 'red',       label: 'Teslim',     icon: TaskIcon },
  private_lesson: { color: 'var(--ted-cat-private-lesson)', tagType: 'warm-gray', label: 'Özel Ders',  icon: UserAvatar },
  event:          { color: 'var(--ted-cat-team)', tagType: 'purple',    label: 'Etkinlik',   icon: EventSchedule },
}

const DAYS_TR = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi']
const MONTHS_TR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                   'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

const SCHOOL_START = 8 * 60
const SCHOOL_END = 15 * 60 + 45
// Işık's sustained-attention window closes before homework hours begin, so the
// stretch between the last bell and the window's edge is the most valuable time
// in the day and the interface spends it on one demanding thing. See §2 of
// docs/frontend-design-principles.md — this is a parameter, not a fact of life.
const FOCUS_END = 16 * 60
const BEDTIME = 22 * 60 + 30

function toMinutes(h: number, m: number) { return h * 60 + m }

/**
 * The focus window is 08:00–16:00. "ŞİMDİ" only belongs inside it.
 * Before the first bell and after bedtime the work is still named, but
 * the voice stops pretending the next ten minutes are the slot (İ4).
 */
function windowVoice(minutes: number, kind: 'work' | 'reading'): {
  eyebrow: string
  hint?: string
  anchorMin?: number
} {
  const afterBedtime = minutes >= BEDTIME
  const afterWindow = minutes >= FOCUS_END
  const beforeSchool = minutes < SCHOOL_START
  const beforeLastBell = !beforeSchool && minutes < SCHOOL_END

  if (kind === 'work') {
    if (afterBedtime) {
      return { eyebrow: 'YARIN', hint: 'Bunu yarın okuldan sonra yapmak daha kolay' }
    }
    if (afterWindow) {
      return { eyebrow: 'BU AKŞAM' }
    }
    if (beforeSchool || beforeLastBell) {
      return {
        eyebrow: 'OKULDAN SONRA',
        hint: 'Bunu okuldan sonra yapmak daha kolay',
        anchorMin: SCHOOL_END,
      }
    }
    return { eyebrow: 'ŞİMDİ' }
  }

  if (afterBedtime) {
    return { eyebrow: 'YARIN', hint: 'Yarın okuldan sonra daha kolay' }
  }
  if (afterWindow) {
    return { eyebrow: 'BU AKŞAM' }
  }
  if (beforeSchool) {
    return { eyebrow: 'BUGÜN', hint: 'Bunu okuldan sonra yapmak daha kolay' }
  }
  return { eyebrow: 'ŞİMDİ' }
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate()
}

function compareCalendarDay(target: Date, reference: Date): -1 | 0 | 1 {
  const t = new Date(target.getFullYear(), target.getMonth(), target.getDate()).getTime()
  const r = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate()).getTime()
  if (t === r) return 0
  return t < r ? -1 : 1
}

function parseTurkishDate(s?: string | null): Date | null {
  if (!s) return null
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!m) return null
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5])
}

function buildAgenda(
  scheduleData: ScheduleData,
  teamsData: { ogep: OgepSession[] },
  hwData: { homework: HomeworkItem[] },
  calData: { events: CalendarEvent[] },
  targetDate: Date,
  nowMs: number,
): AgendaItem[] {
  const items: AgendaItem[] = []
  const now = new Date(nowMs)
  const nowMin = toMinutes(now.getHours(), now.getMinutes())
  const selectedDayName = DAYS_TR[targetDate.getDay()]
  const dayRelation = compareCalendarDay(targetDate, now)

  const getTemporalState = (startMin: number, endMin: number) => {
    if (dayRelation < 0) return { isActive: false, isPast: true }
    if (dayRelation > 0) return { isActive: false, isPast: false }
    return {
      isActive: nowMin >= startMin && nowMin < endMin,
      isPast: nowMin >= endMin,
    }
  }

  const rows = scheduleData.latest?.schedule?.rows || []
  // The portal writes the days in caps ("ÇARŞAMBA") and this matched them with
  // `indexOf('Çarşamba')`, so no day ever matched and the day's agenda showed
  // no lessons at all — measured 2026-09-23: every one of the seven days
  // returned -1. The time column has to come from the day's own block too,
  // because Friday runs on a later bell than Monday through Thursday.
  const gun = dayColumns(rows[0] || [], [selectedDayName])[0]
  if (gun) {
    for (let r = 1; r < rows.length; r++) {
      const timeCell = rows[r][gun.timeIdx] || ''
      const content = rows[r][gun.idx] || ''
      if (!content) continue
      if (['Kahvaltı', 'Öğle yemeği', 'İkindi Kahvaltısı', 'Çıkış'].includes(content)) continue
      const periodMatch = timeCell.match(/(\d+)\. Ders/)
      const timeMatch = timeCell.match(/(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})/)
      if (!periodMatch || !timeMatch) continue
      const lines = content.split('\n')
      const startMin = toMinutes(+timeMatch[1], +timeMatch[2])
      const endMin = toMinutes(+timeMatch[3], +timeMatch[4])
      const teacherRaw = lines.slice(1).join('\n')
      const timeState = getTemporalState(startMin, endMin)
      items.push({
        time: `${timeMatch[1]}:${timeMatch[2]}\u2013${timeMatch[3]}:${timeMatch[4]}`,
        startMin, endMin,
        name: toTitleCase(lines[0]?.trim() || ''),
        subtitle: cleanTeacherNames(teacherRaw),
        type: 'lesson',
        isActive: timeState.isActive,
        isPast: timeState.isPast,
        period: +periodMatch[1],
      })
    }
  }

  for (const s of teamsData.ogep || []) {
    const d = parseTurkishDate(s["Çalışma Başlangıç"])
    if (!d || !isSameDay(d, targetDate)) continue
    const end = parseTurkishDate(s["Çalışma Bitiş"])
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ehh = end ? String(end.getHours()).padStart(2, '0') : hh
    const emm = end ? String(end.getMinutes()).padStart(2, '0') : mm
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const endMin = end ? toMinutes(end.getHours(), end.getMinutes()) : startMin + 40
    const timeState = getTemporalState(startMin, endMin)
    items.push({
      time: `${hh}:${mm}\u2013${ehh}:${emm}`,
      startMin, endMin,
      name: s["ÖGEP (Öğrenci Gelişim Programı)"],
      subtitle: s["Katılım Durumu"] || 'Bekliyor',
      type: 'ogep',
      isActive: timeState.isActive,
      isPast: timeState.isPast,
    })
  }

  for (const hw of hwData.homework || []) {
    const d = parseDeadline(hw["Ödev Son Teslim Tarihi"])
    if (!d || !isSameDay(d, targetDate)) continue
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const timeState = getTemporalState(startMin, startMin)
    items.push({
      time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
      startMin, endMin: startMin,
      name: hw["Ödev Başlığı"],
      subtitle: hw.normalized_course || hw["Ders Adı"],
      type: 'deadline',
      isActive: false,
      isPast: dayRelation === 0 ? nowMin > startMin : timeState.isPast,
    })
  }

  for (const ev of calData.events || []) {
    if (ev.allDay) continue
    const d = new Date(ev.start)
    if (!isSameDay(d, targetDate)) continue
    const end = new Date(ev.end)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ehh = String(end.getHours()).padStart(2, '0')
    const emm = String(end.getMinutes()).padStart(2, '0')
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const endMin = toMinutes(end.getHours(), end.getMinutes())
    const timeState = getTemporalState(startMin, endMin)
    const eventType: AgendaItem['type'] = ev.extendedProps?.kind === 'private_lesson'
      ? 'private_lesson'
      : 'event'
    items.push({
      time: `${hh}:${mm}\u2013${ehh}:${emm}`,
      startMin, endMin,
      name: ev.title,
      subtitle: ev.extendedProps?.description || ev.extendedProps?.location || '',
      type: eventType,
      isActive: timeState.isActive,
      isPast: timeState.isPast,
    })
  }

  return items.sort((a, b) => a.startMin - b.startMin)
}

export default function TodaySchedule() {
  const navigate = useNavigate()
  const { data: scheduleData, loading } = useApi<ScheduleData>(
    '/api/schedule', { latest: {}, today: '' }
  )
  const { data: teamsData } = useApi<{ ogep: OgepSession[] }>(
    '/api/teams', { ogep: [] }
  )
  const { data: hwData } = useApi<{ homework: HomeworkItem[] }>(
    '/api/homework', { homework: [] }
  )
  const { data: calData } = useApi<{ events: CalendarEvent[] }>(
    '/api/calendar', { events: [] }
  )
  const { data: examData } = useApi<ExamsApiResponse>(
    '/api/exams', { exams: [], stats: { upcoming: 0, past: 0, averageGrade: null } }
  )
  const [dayOffset, setDayOffset] = useState(0)

  const selectedDate = useMemo(() => {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    d.setDate(d.getDate() + dayOffset)
    return d
  }, [dayOffset])

  // Reference time for every countdown on this page, refreshed each minute.
  const [nowMs, setNowMs] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 60_000)
    return () => clearInterval(t)
  }, [])

  const agenda = useMemo(
    () => buildAgenda(scheduleData, teamsData, hwData, calData, selectedDate, nowMs),
    [scheduleData, teamsData, hwData, calData, selectedDate, nowMs]
  )

  const activeHomework = useMemo<ActiveHomeworkItem[]>(() => {
    // Recompute countdown labels whenever the minute ticker advances.
    const urgencyOrder: Record<ReturnType<typeof getCountdown>['urgency'], number> = {
      critical: 0,
      urgent: 1,
      soon: 2,
      normal: 3,
      expired: 4,
    }

    return (hwData.homework || [])
      .map(hw => {
        const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
        return {
          hw,
          deadline,
          countdown: getCountdown(deadline, nowMs),
        }
      })
      .filter(({ hw, countdown }) =>
        hw["Ödev Durumu"] === 'Değerlendirilmemiş' && countdown.urgency !== 'expired'
      )
      .sort((a, b) => {
        const urgencyDiff = urgencyOrder[a.countdown.urgency] - urgencyOrder[b.countdown.urgency]
        if (urgencyDiff !== 0) return urgencyDiff
        const aTime = a.deadline?.getTime() ?? Number.MAX_SAFE_INTEGER
        const bTime = b.deadline?.getTime() ?? Number.MAX_SAFE_INTEGER
        return aTime - bTime
      })
  }, [hwData, nowMs])

  const { data: booksData } = useApi<{ books: BookSummary[] }>(
    '/api/books', { books: [] })
  const firstBook = booksData.books[0]
  const bookProgress = useBookProgress(firstBook?.slug)



  const topHomework = activeHomework.slice(0, 3)
  const extraHomeworkCount = Math.max(0, activeHomework.length - topHomework.length)

  const getCountdownTagType = (urgency: ReturnType<typeof getCountdown>['urgency']): 'red' | 'warm-gray' | 'blue' => {
    if (urgency === 'critical' || urgency === 'urgent') return 'red'
    if (urgency === 'soon') return 'warm-gray'
    return 'blue'
  }

  const now = new Date(nowMs)
  const nowMin = toMinutes(now.getHours(), now.getMinutes())

  // Exactly one named next step (İ1), offered as a box to start inside rather
  // than an estimate we do not have (İ3).
  const nextThing = useMemo(() => {
    // Derived from nowMs inside the memo rather than taken as a dependency:
    // the compiler cannot prove a value computed in the render body stays put.
    const d = new Date(nowMs)
    const minutes = toMinutes(d.getHours(), d.getMinutes())
    const top = activeHomework[0]
    if (top) {
      const course = String(top.hw['Ders Adı'] || '').trim()
      const title = String(top.hw['Ödev Başlığı'] || '').trim()
      const voice = windowVoice(minutes, 'work')
      return {
        anchorMin: voice.anchorMin,
        props: {
          eyebrow: voice.eyebrow,
          title: [course, title].filter(Boolean).join(' — ') || 'Ödev',
          stepMinutes: 10,
          actionLabel: 'Başla',
          onAction: () => navigate('/isler'),
          variant: 'work' as const,
          hint: voice.hint,
        },
      }
    }
    // Nothing is owed, so reading takes the slot. It is not louder than school
    // work any more; it is what remains when there is none.
    const resumeId = bookProgress.lastChapterId
    const target = firstBook
      ? (resumeId ? `/kitaplar/${firstBook.slug}/${resumeId}` : `/kitaplar/${firstBook.slug}`)
      : '/kitaplar'
    const voice = windowVoice(minutes, 'reading')
    return {
      anchorMin: voice.anchorMin,
      props: {
        eyebrow: voice.eyebrow,
        title: firstBook ? `Tedy Books — ${firstBook.title}` : 'Tedy Books',
        stepMinutes: 15,
        stepSuffix: 'oku',
        actionLabel: 'Okumaya başla',
        onAction: () => navigate(target),
        variant: 'reading' as const,
        hint: voice.hint,
      },
    }
  }, [activeHomework, nowMs, firstBook, bookProgress.lastChapterId, navigate])

  const selectedIsToday = compareCalendarDay(selectedDate, now) === 0
  const dayName = DAYS_TR[selectedDate.getDay()]
  const dateStr = `${selectedDate.getDate()} ${MONTHS_TR[selectedDate.getMonth()]}`

  const activeItem = agenda.find(a => a.isActive)
  const nextItem = agenda.find(a => !a.isPast && !a.isActive)
  const lessonsTotal = agenda.filter(a => a.type === 'lesson').length
  const lessonsDone = agenda.filter(a => a.type === 'lesson' && a.isPast).length
  const lessonsInProgress = selectedIsToday && activeItem?.type === 'lesson' ? 1 : 0
  const lessonsRemaining = lessonsTotal - lessonsDone - lessonsInProgress

  const progress = Math.min(100, Math.max(0,
    ((nowMin - SCHOOL_START) / (SCHOOL_END - SCHOOL_START)) * 100
  ))
  const schoolDayActive = selectedIsToday && nowMin >= SCHOOL_START && nowMin <= SCHOOL_END

  const nowInsertIdx = agenda.findIndex(a => a.startMin > nowMin)
  const showNowMarker = selectedIsToday && !activeItem && schoolDayActive

  const nowTimeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`

  if (loading) {
    return (
      <div className="today-loading">
        <div className="today-loading__bar" />
        <div className="today-loading__bar today-loading__bar--short" />
        <div className="today-loading__bar" />
        <div className="today-loading__bar today-loading__bar--short" />
      </div>
    )
  }

  return (
    <div className="today">
      {/* ── Date header ── */}
      <div className="today__header">
        <div className="today__header-main">
          <button
            type="button"
            className="today__nav-btn"
            onClick={() => setDayOffset(v => v - 1)}
            aria-label="Önceki gün"
          >
            <ChevronLeft size={16} />
          </button>
          <div className="today__header-text">
            <span className="today__day-name">{dayName}</span>
            <span className="today__date-str">{dateStr}</span>
          </div>
          <button
            type="button"
            className="today__nav-btn"
            onClick={() => setDayOffset(v => v + 1)}
            aria-label="Sonraki gün"
          >
            <ChevronRight size={16} />
          </button>
        </div>
        <div className="today__header-meta">
          {dayOffset !== 0 && (
            <button
              type="button"
              className="today__today-btn"
              onClick={() => setDayOffset(0)}
            >
              Bugüne dön
            </button>
          )}
          {lessonsTotal > 0 && (
            <span className="today__lesson-counter">
              {lessonsDone + lessonsInProgress}/{lessonsTotal}
            </span>
          )}
        </div>
      </div>

      <DayStrip
        nowMin={nowMin}
        bedtimeMin={BEDTIME}
        focusEndMin={FOCUS_END}
        anchorMin={nextThing.anchorMin}
      />

      <NextThing {...nextThing.props} />

      {examData.exams.filter(e => e.status === 'upcoming').length > 0 && (
        <div className="today-exams">
          <div className="today-exams__header">
            <span className="today-exams__title">Yaklaşan Sınavlar</span>
            <button
              type="button"
              className="today-exams__all-btn"
              onClick={() => navigate('/sinavlar')}
            >
              Tümünü gör
            </button>
          </div>
          <div className="today-exams__list">
            {examData.exams
              .filter(e => e.status === 'upcoming')
              .slice(0, 3)
              .map(exam => {
                const cd = exam.date ? getExamCountdown(new Date(exam.date), nowMs) : null
                const tagType = cd?.urgency === 'critical' || cd?.urgency === 'urgent' ? 'red' as const
                  : cd?.urgency === 'soon' ? 'magenta' as const : 'cool-gray' as const
                const dateLabel = exam.date ? (() => {
                  try {
                    const d = new Date(exam.date)
                    return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`
                  } catch { return '' }
                })() : ''
                return (
                  <button
                    key={exam.id}
                    type="button"
                    className="today-exams__item"
                    onClick={() => navigate('/sinavlar')}
                  >
                    <div className="today-exams__item-main">
                      <span className="today-exams__item-course" style={{ color: exam.courseColor || undefined }}>{exam.course}</span>
                      <span className="today-exams__item-title">{exam.title || exam.rawTitle}</span>
                      {dateLabel && <span className="today-exams__item-date">{dateLabel}</span>}
                    </div>
                    {cd && <Tag type={tagType} size="sm">{cd.text}</Tag>}
                  </button>
                )
              })}
          </div>
        </div>
      )}

      {activeHomework.length > 0 && (
        <div className="today-homework">
          <div className="today-homework__header">
            <span className="today-homework__title">Aktif Ödevler</span>
            <button
              type="button"
              className="today-homework__all-btn"
              onClick={() => navigate('/isler')}
            >
              Tümünü gör
            </button>
          </div>
          <div className="today-homework__list">
            {topHomework.map(({ hw, countdown }, i) => (
              <button
                key={`${hw["Ödev Başlığı"]}-${i}`}
                type="button"
                className="today-homework__item"
                onClick={() => navigate('/isler')}
              >
                <div className="today-homework__item-main">
                  <span className="today-homework__item-course">{hw.normalized_course || hw["Ders Adı"]}</span>
                  <span className="today-homework__item-title">{hw["Ödev Başlığı"]}</span>
                  <span className="today-homework__item-deadline">
                    Teslim: {formatTurkishDate(hw["Ödev Son Teslim Tarihi"])}
                  </span>
                </div>
                <Tag type={getCountdownTagType(countdown.urgency)} size="sm">
                  {countdown.text}
                </Tag>
              </button>
            ))}
          </div>
          {extraHomeworkCount > 0 && (
            <p className="today-homework__more">+{extraHomeworkCount} aktif ödev daha var</p>
          )}
        </div>
      )}

      {agenda.length === 0 ? (
        // One line, not a card. The old empty state spent a large decorative
        // sun and ~200px competing with the one thing above it, which is the
        // attention budget spent on the absence of news (İ6, §2.3).
        <EmptyLine>
          {dayName} için planlı ders, ödev teslimi veya etkinlik yok.
        </EmptyLine>
      ) : (
        <>
          {/* ── Hero card ── */}
          {selectedIsToday ? (
            activeItem ? (
              <HeroActive item={activeItem} nowMin={nowMin} />
            ) : nextItem ? (
              <HeroNext item={nextItem} nowMin={nowMin} />
            ) : (
              <HeroDone lessonsDone={lessonsDone} />
            )
          ) : (
            <HeroPlanned dateLabel={`${dayName}, ${dateStr}`} itemCount={agenda.length} />
          )}

          {/* ── School day progress ── */}
          {schoolDayActive && lessonsTotal > 0 && (
            <div className="today-daybar">
              <div className="today-daybar__track">
                <div className="today-daybar__fill" style={{ width: `${progress}%` }} />
              </div>
              <div className="today-daybar__labels">
                <span>08:00</span>
                <span>{lessonsRemaining > 0 ? `${lessonsRemaining} ders kaldı` : 'Son ders'}</span>
                <span>15:45</span>
              </div>
            </div>
          )}

          {/* ── Timeline ── */}
          <div className="today-tl">
            {agenda.map((item, i) => {
              const cfg = TYPE_CONFIG[item.type]
              const Icon = cfg.icon

              return (
                <div key={i}>
                  {showNowMarker && nowInsertIdx === i && (
                    <NowMarker time={nowTimeStr} />
                  )}
                  <div
                    className={[
                      'today-tl__item',
                      item.isPast && 'today-tl__item--past',
                      item.isActive && 'today-tl__item--active',
                      item.type === 'deadline' && 'today-tl__item--deadline',
                    ].filter(Boolean).join(' ')}
                    style={{ '--tl-color': cfg.color } as React.CSSProperties}
                    onClick={item.type === 'deadline' ? () => navigate('/isler') : undefined}
                  >
                    <div className="today-tl__time">
                      {item.time.split('\u2013')[0]}
                    </div>
                    <div className="today-tl__spine">
                      <div className="today-tl__dot">
                        {item.isPast
                          ? <Checkmark size={10} />
                          : <Icon size={10} />}
                      </div>
                    </div>
                    <div className="today-tl__card">
                      <div className="today-tl__card-top">
                        <span className="today-tl__card-name">{item.name}</span>
                        {item.period != null && (
                          <span className="today-tl__card-period">{item.period}.</span>
                        )}
                      </div>
                      {item.subtitle && (
                        <div className="today-tl__card-sub">{item.subtitle}</div>
                      )}
                      {(cfg.label || item.isActive) && (
                        <div className="today-tl__card-tags">
                          {item.isActive && <Tag type="blue" size="sm">Devam ediyor</Tag>}
                          {cfg.label && <Tag type={cfg.tagType} size="sm">{cfg.label}</Tag>}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
            {showNowMarker && nowInsertIdx === -1 && (
              <NowMarker time={nowTimeStr} />
            )}
          </div>
        </>
      )}
    </div>
  )
}

/* ── Sub-components ────────────────────────────────────────────────────────── */

function HeroActive({ item, nowMin }: { item: AgendaItem; nowMin: number }) {
  const elapsed = nowMin - item.startMin
  const total = item.endMin - item.startMin
  const remaining = item.endMin - nowMin
  const pct = total > 0 ? (elapsed / total) * 100 : 0
  const Icon = TYPE_CONFIG[item.type].icon

  return (
    <div className="today-hero today-hero--active">
      <div className="today-hero__top">
        <div className="today-hero__badge">
          <span className="today-hero__pulse" />
          Şu an
        </div>
        <Icon size={20} className="today-hero__icon" />
      </div>
      <h2 className="today-hero__title">{item.name}</h2>
      {item.subtitle && <p className="today-hero__sub">{item.subtitle}</p>}
      <div className="today-hero__footer">
        <span className="today-hero__time-range">{item.time}</span>
        <span className="today-hero__remaining">{remaining} dk kaldı</span>
      </div>
      <div className="today-hero__bar">
        <div className="today-hero__bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function HeroNext({ item, nowMin }: { item: AgendaItem; nowMin: number }) {
  const until = item.startMin - nowMin
  const Icon = TYPE_CONFIG[item.type].icon

  return (
    <div className="today-hero today-hero--next">
      <div className="today-hero__top">
        <div className="today-hero__badge today-hero__badge--upcoming">Sıradaki</div>
        <Icon size={20} className="today-hero__icon" />
      </div>
      <h2 className="today-hero__title">{item.name}</h2>
      {item.subtitle && <p className="today-hero__sub">{item.subtitle}</p>}
      <div className="today-hero__footer">
        <span className="today-hero__time-range">{item.time}</span>
        <span className="today-hero__remaining">{until} dk sonra</span>
      </div>
    </div>
  )
}

function HeroDone({ lessonsDone }: { lessonsDone: number }) {
  return (
    <div className="today-hero today-hero--done">
      <div className="today-hero__badge today-hero__badge--complete">Tamamlandı</div>
      <h2 className="today-hero__title">Bugünkü program bitti</h2>
      {lessonsDone > 0 && (
        <p className="today-hero__sub">{lessonsDone} ders tamamlandı</p>
      )}
    </div>
  )
}

function HeroPlanned({ dateLabel, itemCount }: { dateLabel: string; itemCount: number }) {
  return (
    <div className="today-hero today-hero--next">
      <div className="today-hero__top">
        <div className="today-hero__badge today-hero__badge--upcoming">Seçili gün</div>
      </div>
      <h2 className="today-hero__title">{dateLabel}</h2>
      <p className="today-hero__sub">{itemCount} ajanda öğesi planlandı</p>
    </div>
  )
}

function NowMarker({ time }: { time: string }) {
  return (
    <div className="today-tl__now">
      <span className="today-tl__now-time">{time}</span>
      <span className="today-tl__now-line" />
    </div>
  )
}
