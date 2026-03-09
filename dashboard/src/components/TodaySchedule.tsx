import { Tile, Tag } from '@carbon/react'
import { Time } from '@carbon/icons-react'
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
  name: string
  subtitle: string
  type: 'lesson' | 'ogep' | 'deadline' | 'event'
  isActive?: boolean
}

const TAG_CONFIG = {
  lesson: { type: 'blue' as const, label: '' },
  ogep: { type: 'teal' as const, label: 'ÖGEP' },
  deadline: { type: 'red' as const, label: 'Teslim' },
  event: { type: 'purple' as const, label: 'Etkinlik' },
}

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

  // 1. Class lessons from schedule
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
        time: `${timeMatch[1]}:${timeMatch[2]}-${timeMatch[3]}:${timeMatch[4]}`,
        startMin,
        name: lines[0]?.trim() || '',
        subtitle: lines.slice(1).join(', ').trim(),
        type: 'lesson',
        isActive: nowMin >= startMin && nowMin < endMin,
      })
    }
  }

  // 2. ÖGEP sessions today
  for (const s of teamsData.ogep || []) {
    const d = parseTurkishDate(s["Çalışma Başlangıç"])
    if (!d || !isToday(d)) continue
    const end = parseTurkishDate(s["Çalışma Bitiş"])
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ehh = end ? String(end.getHours()).padStart(2, '0') : ''
    const emm = end ? String(end.getMinutes()).padStart(2, '0') : ''
    items.push({
      time: end ? `${hh}:${mm}-${ehh}:${emm}` : `${hh}:${mm}`,
      startMin: toMinutes(d.getHours(), d.getMinutes()),
      name: s["ÖGEP (Öğrenci Gelişim Programı)"],
      subtitle: s["Katılım Durumu"] || 'Bekliyor',
      type: 'ogep',
    })
  }

  // 3. Homework deadlines today
  for (const hw of hwData.homework || []) {
    const d = parseDeadline(hw["Ödev Son Teslim Tarihi"])
    if (!d || !isToday(d)) continue
    items.push({
      time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
      startMin: toMinutes(d.getHours(), d.getMinutes()),
      name: hw["Ödev Başlığı"],
      subtitle: hw.normalized_course || hw["Ders Adı"],
      type: 'deadline',
    })
  }

  // 4. Calendar events today
  for (const ev of calData.events || []) {
    if (ev.allDay) continue
    const d = new Date(ev.start)
    if (!isToday(d)) continue
    const end = new Date(ev.end)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ehh = String(end.getHours()).padStart(2, '0')
    const emm = String(end.getMinutes()).padStart(2, '0')
    items.push({
      time: `${hh}:${mm}-${ehh}:${emm}`,
      startMin: toMinutes(d.getHours(), d.getMinutes()),
      name: ev.title,
      subtitle: ev.extendedProps?.location || '',
      type: 'event',
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

  if (loading) return <Tile className="dashboard-loading-tile">Yükleniyor...</Tile>

  const agenda = buildAgenda(scheduleData, teamsData, hwData, calData)

  if (agenda.length === 0) return (
    <div className="dashboard-card">
      <h4 className="dashboard-card__title" style={{ margin: 0 }}>
        <Time size={20} /> Bugün için ajanda öğesi yok
      </h4>
    </div>
  )

  return (
    <div className="dashboard-card">
      <h4 className="dashboard-card__title">
        <Time size={20} />
        Bugünün Ajandası &mdash; {scheduleData.today}
      </h4>
      <div className="agenda-row">
        {agenda.map((item, i) => {
          const cfg = TAG_CONFIG[item.type]
          const agendaItemClass = [
            'agenda-item',
            `agenda-item--${item.type}`,
            item.isActive ? 'agenda-item--active' : '',
          ].filter(Boolean).join(' ')

          return (
            <Tile key={i}
              className={agendaItemClass}
            >
              <div className="agenda-item__time">
                {item.time}
              </div>
              <div className="agenda-item__name">
                {item.name}
              </div>
              <div className="agenda-item__subtitle">
                {item.subtitle}
              </div>
              <div className="agenda-item__tags">
                {item.isActive && <Tag type="blue" size="sm">Şimdi</Tag>}
                {cfg.label && <Tag type={cfg.type} size="sm">{cfg.label}</Tag>}
              </div>
            </Tile>
          )
        })}
      </div>
    </div>
  )
}
