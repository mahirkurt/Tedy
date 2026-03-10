import { useState, useEffect, useMemo } from 'react'
import { Tag } from '@carbon/react'
import {
  Education,
  Bookmark,
  Task as TaskIcon,
  EventSchedule,
  Checkmark,
} from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { parseDeadline } from '../utils/formatters'
import type { HomeworkItem, CalendarEvent, OgepSession } from '../types'

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
  type: 'lesson' | 'ogep' | 'deadline' | 'event'
  isActive: boolean
  isPast: boolean
  period?: number
}

type IconComponent = typeof Education

const TYPE_CONFIG: Record<AgendaItem['type'], {
  color: string
  tagType: 'blue' | 'teal' | 'red' | 'purple'
  label: string
  icon: IconComponent
}> = {
  lesson:   { color: '#002d9c', tagType: 'blue',   label: '',         icon: Education },
  ogep:     { color: '#009d9a', tagType: 'teal',    label: 'ÖGEP',     icon: Bookmark },
  deadline: { color: '#da1e28', tagType: 'red',     label: 'Teslim',   icon: TaskIcon },
  event:    { color: '#8a3ffc', tagType: 'purple',  label: 'Etkinlik', icon: EventSchedule },
}

const DAYS_TR = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi']
const MONTHS_TR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                   'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

const SCHOOL_START = 8 * 60
const SCHOOL_END = 15 * 60 + 45

function toMinutes(h: number, m: number) { return h * 60 + m }

function isToday(date: Date): boolean {
  const now = new Date()
  return date.getFullYear() === now.getFullYear()
    && date.getMonth() === now.getMonth()
    && date.getDate() === now.getDate()
}

function parseTurkishDate(s: string): Date | null {
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!m) return null
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5])
}

function buildAgenda(
  scheduleData: ScheduleData,
  teamsData: { ogep: OgepSession[] },
  hwData: { homework: HomeworkItem[] },
  calData: { events: CalendarEvent[] },
): AgendaItem[] {
  const items: AgendaItem[] = []
  const now = new Date()
  const nowMin = toMinutes(now.getHours(), now.getMinutes())

  const rows = scheduleData.latest?.schedule?.rows || []
  const dayHeaders = rows[0] || []
  const todayIdx = dayHeaders.indexOf(scheduleData.today)
  if (todayIdx >= 0) {
    for (let r = 1; r < rows.length; r++) {
      const timeCell = rows[r][0] || ''
      const content = rows[r][todayIdx] || ''
      if (!content) continue
      if (['Kahvaltı', 'Öğle yemeği', 'İkindi Kahvaltısı', 'Çıkış'].includes(content)) continue
      const periodMatch = timeCell.match(/(\d+)\. Ders/)
      const timeMatch = timeCell.match(/(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})/)
      if (!periodMatch || !timeMatch) continue
      const lines = content.split('\n')
      const startMin = toMinutes(+timeMatch[1], +timeMatch[2])
      const endMin = toMinutes(+timeMatch[3], +timeMatch[4])
      items.push({
        time: `${timeMatch[1]}:${timeMatch[2]}\u2013${timeMatch[3]}:${timeMatch[4]}`,
        startMin, endMin,
        name: lines[0]?.trim() || '',
        subtitle: lines.slice(1).join(', ').trim(),
        type: 'lesson',
        isActive: nowMin >= startMin && nowMin < endMin,
        isPast: nowMin >= endMin,
        period: +periodMatch[1],
      })
    }
  }

  for (const s of teamsData.ogep || []) {
    const d = parseTurkishDate(s["Çalışma Başlangıç"])
    if (!d || !isToday(d)) continue
    const end = parseTurkishDate(s["Çalışma Bitiş"])
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ehh = end ? String(end.getHours()).padStart(2, '0') : hh
    const emm = end ? String(end.getMinutes()).padStart(2, '0') : mm
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const endMin = end ? toMinutes(end.getHours(), end.getMinutes()) : startMin + 40
    items.push({
      time: `${hh}:${mm}\u2013${ehh}:${emm}`,
      startMin, endMin,
      name: s["ÖGEP (Öğrenci Gelişim Programı)"],
      subtitle: s["Katılım Durumu"] || 'Bekliyor',
      type: 'ogep',
      isActive: nowMin >= startMin && nowMin < endMin,
      isPast: nowMin >= endMin,
    })
  }

  for (const hw of hwData.homework || []) {
    const d = parseDeadline(hw["Ödev Son Teslim Tarihi"])
    if (!d || !isToday(d)) continue
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    items.push({
      time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
      startMin, endMin: startMin,
      name: hw["Ödev Başlığı"],
      subtitle: hw.normalized_course || hw["Ders Adı"],
      type: 'deadline',
      isActive: false,
      isPast: nowMin > startMin,
    })
  }

  for (const ev of calData.events || []) {
    if (ev.allDay) continue
    const d = new Date(ev.start)
    if (!isToday(d)) continue
    const end = new Date(ev.end)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ehh = String(end.getHours()).padStart(2, '0')
    const emm = String(end.getMinutes()).padStart(2, '0')
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const endMin = toMinutes(end.getHours(), end.getMinutes())
    items.push({
      time: `${hh}:${mm}\u2013${ehh}:${emm}`,
      startMin, endMin,
      name: ev.title,
      subtitle: ev.extendedProps?.location || '',
      type: 'event',
      isActive: nowMin >= startMin && nowMin < endMin,
      isPast: nowMin >= endMin,
    })
  }

  return items.sort((a, b) => a.startMin - b.startMin)
}

export default function TodaySchedule() {
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

  // Re-render every 60s so countdowns stay fresh
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 60_000)
    return () => clearInterval(t)
  }, [])

  const agenda = useMemo(
    () => buildAgenda(scheduleData, teamsData, hwData, calData),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scheduleData, teamsData, hwData, calData, tick]
  )

  const now = new Date()
  const nowMin = toMinutes(now.getHours(), now.getMinutes())
  const dayName = DAYS_TR[now.getDay()]
  const dateStr = `${now.getDate()} ${MONTHS_TR[now.getMonth()]}`

  const activeItem = agenda.find(a => a.isActive)
  const nextItem = agenda.find(a => !a.isPast && !a.isActive)
  const lessonsTotal = agenda.filter(a => a.type === 'lesson').length
  const lessonsDone = agenda.filter(a => a.type === 'lesson' && a.isPast).length
  const lessonsInProgress = activeItem?.type === 'lesson' ? 1 : 0
  const lessonsRemaining = lessonsTotal - lessonsDone - lessonsInProgress

  const progress = Math.min(100, Math.max(0,
    ((nowMin - SCHOOL_START) / (SCHOOL_END - SCHOOL_START)) * 100
  ))
  const schoolDayActive = nowMin >= SCHOOL_START && nowMin <= SCHOOL_END

  const nowInsertIdx = agenda.findIndex(a => a.startMin > nowMin)
  const showNowMarker = !activeItem && schoolDayActive

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

  if (agenda.length === 0) {
    return (
      <div className="today-empty">
        <div className="today-empty__icon" aria-hidden>&#9728;</div>
        <h3 className="today-empty__title">Bugün ajanda boş</h3>
        <p className="today-empty__text">
          Planlı ders, ödev teslimi veya etkinlik yok.
        </p>
      </div>
    )
  }

  return (
    <div className="today">
      {/* ── Date header ── */}
      <div className="today__header">
        <div>
          <span className="today__day-name">{dayName}</span>
          <span className="today__date-str">{dateStr}</span>
        </div>
        {lessonsTotal > 0 && (
          <span className="today__lesson-counter">
            {lessonsDone + lessonsInProgress}/{lessonsTotal}
          </span>
        )}
      </div>

      {/* ── Hero card ── */}
      {activeItem ? (
        <HeroActive item={activeItem} nowMin={nowMin} />
      ) : nextItem ? (
        <HeroNext item={nextItem} nowMin={nowMin} />
      ) : (
        <HeroDone lessonsDone={lessonsDone} />
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
                ].filter(Boolean).join(' ')}
                style={{ '--tl-color': cfg.color } as React.CSSProperties}
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

function NowMarker({ time }: { time: string }) {
  return (
    <div className="today-tl__now">
      <span className="today-tl__now-time">{time}</span>
      <span className="today-tl__now-line" />
    </div>
  )
}
