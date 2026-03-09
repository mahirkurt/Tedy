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
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <EventSchedule size={20} />
        Takvim & Yaklaşan Etkinlikler
      </h4>
      {upcoming.length === 0 ? (
        <p style={{ fontSize: '0.8125rem', color: '#525252' }}>Yaklaşan etkinlik yok</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {upcoming.map((ev, i) => {
            const d = new Date(ev.start)
            return (
              <Tile key={i} style={{ padding: '0.5rem 1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <div style={{
                  textAlign: 'center', minWidth: '48px',
                  padding: '0.25rem', backgroundColor: '#EDF5FF', borderRadius: '4px'
                }}>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--highlight-today)' }}>
                    {d.getDate()}
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: '#525252' }}>
                    {MONTHS[d.getMonth()]}
                  </div>
                </div>
                <div>
                  <div style={{ fontWeight: 500, fontSize: '0.8125rem' }}>{ev.title}</div>
                  {!ev.allDay && (
                    <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                      {d.getHours().toString().padStart(2, '0')}:{d.getMinutes().toString().padStart(2, '0')}
                    </div>
                  )}
                  {ev.extendedProps?.location && (
                    <div style={{ fontSize: '0.75rem', color: '#525252' }}>
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
