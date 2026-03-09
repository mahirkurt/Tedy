import { Tile } from '@carbon/react'
import { EventSchedule } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { CalendarEvent } from '../types'

const MONTHS = ['Oca', 'Sub', 'Mar', 'Nis', 'May', 'Haz',
                'Tem', 'Agu', 'Eyl', 'Eki', 'Kas', 'Ara']

export default function CalendarEvents() {
  const { data } = useApi<{ events: CalendarEvent[] }>('/api/calendar', { events: [] })

  const now = new Date()
  const upcoming = data.events
    .filter(e => new Date(e.end || e.start) >= now)
    .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())
    .slice(0, 10)

  return (
    <div className="dashboard-card">
      <h4 className="dashboard-card__title">
        <EventSchedule size={20} />
        Takvim & Yaklaşan Etkinlikler
      </h4>
      {upcoming.length === 0 ? (
        <p className="dashboard-empty-text">Yaklaşan etkinlik yok</p>
      ) : (
        <div className="stack-sm">
          {upcoming.map((ev, i) => {
            const d = new Date(ev.start)
            return (
              <Tile key={i} className="dashboard-list-tile dashboard-event-tile">
                <div className="dashboard-event-date">
                  <div className="dashboard-event-date__day">
                    {d.getDate()}
                  </div>
                  <div className="dashboard-event-date__month">
                    {MONTHS[d.getMonth()]}
                  </div>
                </div>
                <div>
                  <div className="dashboard-list-tile__label">{ev.title}</div>
                  {!ev.allDay && (
                    <div className="dashboard-list-tile__meta">
                      {d.getHours().toString().padStart(2, '0')}:{d.getMinutes().toString().padStart(2, '0')}
                    </div>
                  )}
                  {ev.extendedProps?.location && (
                    <div className="dashboard-list-tile__meta">
                      {ev.extendedProps.location}
                    </div>
                  )}
                </div>
              </Tile>
            )
          })}
        </div>
      )}
    </div>
  )
}
