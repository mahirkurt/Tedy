import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { Button } from '@carbon/react'
import { ChevronLeft, ChevronRight, EventSchedule, Close } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { UnifiedEvent } from '../types'
import { MONTHS_SHORT } from '../utils/formatters'

// ── Constants ──

const DAY_LABELS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum'] as const
const HOUR_START = 7
const HOUR_END = 17
const HOURS = Array.from({ length: HOUR_END - HOUR_START + 1 }, (_, i) => HOUR_START + i)

const TYPE_LABELS: Record<string, string> = {
  lesson: 'Ders',
  homework: 'Ödev',
  private_lesson: 'Özel Ders',
  ogep: 'ÖGEP',
  team: 'Takım',
  sebit: 'SEBIT',
  event: 'Etkinlik',
}

const TYPE_COLORS: Record<string, string> = {
  lesson: 'var(--ted-cat-lesson)',
  homework: 'var(--ted-cat-homework)',
  private_lesson: 'var(--ted-cat-private-lesson)',
  ogep: 'var(--ted-cat-ogep)',
  team: 'var(--ted-cat-team)',
  sebit: 'var(--ted-cat-sebit)',
  event: 'var(--ted-cat-event)',
}

const MONTHS_LONG = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
]

// ── Helpers ──

function getMonday(d: Date): Date {
  const date = new Date(d)
  const day = date.getDay()
  const diff = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + diff)
  date.setHours(0, 0, 0, 0)
  return date
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
}

function weekDates(monday: Date): Date[] {
  return Array.from({ length: 5 }, (_, i) => addDays(monday, i))
}

function weekLabel(monday: Date): string {
  const friday = addDays(monday, 4)
  const mLabel = `${monday.getDate()} ${
    monday.getMonth() === friday.getMonth() ? '' : MONTHS_LONG[monday.getMonth()] + ' '
  }`
  return `${mLabel.trim()} - ${friday.getDate()} ${MONTHS_LONG[friday.getMonth()]} ${friday.getFullYear()}`
}

function parseEventDate(s: string): Date | null {
  if (!s) return null
  // ISO format
  const d = new Date(s)
  if (!isNaN(d.getTime())) return d
  // DD.MM.YYYY HH:MM
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (m) return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5])
  return null
}

function formatTime(d: Date): string {
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

// ── Component ──

export default function CalendarEvents() {
  const { data, loading } = useApi<{ events: UnifiedEvent[] }>('/api/calendar/unified', { events: [] })
  const [weekOffset, setWeekOffset] = useState(0)
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())
  const [selectedEvent, setSelectedEvent] = useState<UnifiedEvent | null>(null)
  const popoverRef = useRef<HTMLDivElement>(null)

  const today = useMemo(() => new Date(), [])
  const monday = useMemo(() => {
    const m = getMonday(today)
    m.setDate(m.getDate() + weekOffset * 7)
    return m
  }, [today, weekOffset])
  const days = useMemo(() => weekDates(monday), [monday])

  // Close popover on outside click
  useEffect(() => {
    if (!selectedEvent) return
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setSelectedEvent(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [selectedEvent])

  // Filter and bucket events into day/hour cells
  const eventsInWeek = useMemo(() => {
    return data.events
      .filter(ev => !hiddenTypes.has(ev.type))
      .map(ev => {
        const start = parseEventDate(ev.start)
        const end = parseEventDate(ev.end)
        return { ...ev, _start: start, _end: end }
      })
      .filter(ev => {
        if (!ev._start) return false
        const friday = addDays(monday, 4)
        friday.setHours(23, 59, 59)
        return ev._start >= monday && ev._start <= friday
      })
  }, [data.events, monday, hiddenTypes])

  // Group events by day column index
  const eventsByDay = useMemo(() => {
    const map: Record<number, typeof eventsInWeek> = {}
    for (let i = 0; i < 5; i++) map[i] = []
    for (const ev of eventsInWeek) {
      if (!ev._start) continue
      for (let di = 0; di < 5; di++) {
        if (isSameDay(ev._start, days[di])) {
          map[di].push(ev)
          break
        }
      }
    }
    return map
  }, [eventsInWeek, days])

  const toggleType = useCallback((t: string) => {
    setHiddenTypes(prev => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }, [])

  // Build cell events: which events fall into each (hour, dayIdx) cell
  const getCellEvents = useCallback((hour: number, dayIdx: number) => {
    return eventsByDay[dayIdx]?.filter(ev => {
      if (!ev._start) return false
      const evHour = ev._start.getHours()
      // For homework/sebit (point events), place them at their hour
      if (ev.type === 'homework' || ev.type === 'sebit') {
        return evHour === hour
      }
      // For block events, show in every hour they span
      const endHour = ev._end ? ev._end.getHours() : evHour
      const endMin = ev._end ? ev._end.getMinutes() : 0
      const effectiveEnd = endMin > 0 ? endHour : endHour - 1
      return evHour <= hour && effectiveEnd >= hour
    }) ?? []
  }, [eventsByDay])

  if (loading) {
    return (
      <div className="dashboard-card">
        <h2 className="dashboard-card__title">
          <EventSchedule size={20} />
          Haftalik Takvim
        </h2>
        <div className="today-loading">
          <div className="today-loading__bar" />
          <div className="today-loading__bar today-loading__bar--short" />
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-card" style={{ position: 'relative' }}>
      <h2 className="dashboard-card__title">
        <EventSchedule size={20} />
        Haftalik Takvim
      </h2>

      {/* Navigation */}
      <div className="calendar-nav">
        <Button
          kind="ghost"
          size="sm"
          hasIconOnly
          renderIcon={ChevronLeft}
          iconDescription="Onceki hafta"
          onClick={() => setWeekOffset(w => w - 1)}
        />
        <span className="calendar-nav__label">{weekLabel(monday)}</span>
        <Button
          kind="ghost"
          size="sm"
          hasIconOnly
          renderIcon={ChevronRight}
          iconDescription="Sonraki hafta"
          onClick={() => setWeekOffset(w => w + 1)}
        />
        {weekOffset !== 0 && (
          <Button kind="ghost" size="sm" onClick={() => setWeekOffset(0)}>
            Bugun
          </Button>
        )}
      </div>

      {/* Legend */}
      <div className="calendar-legend">
        {Object.entries(TYPE_LABELS).map(([type, label]) => (
          <button
            key={type}
            className={`calendar-legend__chip${hiddenTypes.has(type) ? ' calendar-legend__chip--hidden' : ''}`}
            onClick={() => toggleType(type)}
            title={`${label} ${hiddenTypes.has(type) ? 'goster' : 'gizle'}`}
          >
            <span className="calendar-legend__dot" style={{ background: TYPE_COLORS[type] }} />
            {label}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="calendar-grid">
        {/* Header row */}
        <div className="calendar-grid__header" />
        {days.map((d, i) => (
          <div
            key={i}
            className={`calendar-grid__header${isSameDay(d, today) ? ' calendar-grid__header--today' : ''}`}
          >
            <div>{DAY_LABELS[i]}</div>
            <div>{d.getDate()} {MONTHS_SHORT[d.getMonth()]}</div>
          </div>
        ))}

        {/* Hour rows */}
        {HOURS.map(hour => (
          <>
            <div key={`t-${hour}`} className="calendar-grid__time">
              {hour.toString().padStart(2, '0')}:00
            </div>
            {days.map((d, di) => {
              const cellEvts = getCellEvents(hour, di)
              const isToday = isSameDay(d, today)
              // Hours already spent cannot be acted on, so they stop competing
              // for attention (İ7). Today marks the boundary; earlier days in
              // this week, and earlier hours today, are behind it.
              const isPast = d < today && !isToday
                ? true
                : isToday && hour < today.getHours()
              return (
                <div
                  key={`c-${hour}-${di}`}
                  className={
                    'calendar-grid__cell'
                    + (isToday ? ' calendar-grid__cell--today' : '')
                    + (isPast ? ' calendar-grid__cell--past' : '')
                  }
                >
                  {cellEvts.map(ev => {
                    const isHw = ev.type === 'homework'
                    const isPrivate = ev.type === 'private_lesson'
                    const isBlock = !isHw && ev.type !== 'sebit'
                    // Only show title in the first hour of a block event
                    const isFirstHour = ev._start ? ev._start.getHours() === hour : true
                    if (!isFirstHour && isBlock) {
                      // Continuation block — thin colored bar
                      return (
                        <div
                          key={ev.id}
                          className="calendar-event calendar-event--continuation"
                          style={{ background: ev.color }}
                          onClick={() => setSelectedEvent(ev)}
                        />
                      )
                    }
                    return (
                      <div
                        key={ev.id}
                        className={[
                          'calendar-event',
                          isHw ? 'calendar-event--homework' : '',
                          isPrivate ? 'calendar-event--private' : '',
                        ].filter(Boolean).join(' ')}
                        style={isHw ? {} : { background: ev.color }}
                        onClick={() => setSelectedEvent(ev)}
                        title={ev.title}
                      >
                        {ev.title}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </>
        ))}
      </div>

      {/* Event detail popover */}
      {selectedEvent && (
        <div className="calendar-popover" ref={popoverRef}>
          <div className="calendar-popover__header">
            <span
              className="calendar-popover__type"
              style={{ background: selectedEvent.color }}
            >
              {TYPE_LABELS[selectedEvent.type] ?? selectedEvent.type}
            </span>
            <button
              className="calendar-popover__close"
              onClick={() => setSelectedEvent(null)}
              aria-label="Kapat"
            >
              <Close size={16} />
            </button>
          </div>
          <h5 className="calendar-popover__title">{selectedEvent.title}</h5>
          {selectedEvent._start && (
            <p className="calendar-popover__time">
              {formatTime(selectedEvent._start)}
              {selectedEvent._end && selectedEvent._end.getTime() !== selectedEvent._start.getTime()
                ? ` - ${formatTime(selectedEvent._end)}`
                : ''}
            </p>
          )}
          {selectedEvent.course && (
            <p className="calendar-popover__meta">Ders: {selectedEvent.course}</p>
          )}
          {selectedEvent.subtitle && (
            <p className="calendar-popover__meta">{selectedEvent.subtitle}</p>
          )}
          {selectedEvent.status && (
            <p className="calendar-popover__meta">Durum: {selectedEvent.status}</p>
          )}
        </div>
      )}
    </div>
  )
}

// Extend the event type locally for parsed dates
declare module '../types' {
  interface UnifiedEvent {
    _start?: Date | null
    _end?: Date | null
  }
}
