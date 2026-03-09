import { Tile, Tag } from '@carbon/react'
import { Time } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'

interface ScheduleData {
  latest: { schedule?: { rows: string[][] } }
  today: string
}

interface Lesson {
  period: string
  time: string
  name: string
  teacher: string
}

function parseLessons(rows: string[][], dayIdx: number): Lesson[] {
  const lessons: Lesson[] = []
  for (let r = 1; r < rows.length; r++) {
    const timeCell = rows[r][0] || ''
    const content = rows[r][dayIdx] || ''
    if (!content || content === 'Kahvalti' || content === 'Ogle yemegi'
        || content === 'Ikindi Kahvaltisi' || content === 'Cikis') continue
    // Also skip meal/break cells by checking for known patterns
    if (['Kahvaltı', 'Öğle yemeği', 'İkindi Kahvaltısı', 'Çıkış'].includes(content)) continue
    const periodMatch = timeCell.match(/(\d+)\. Ders/)
    const timeMatch = timeCell.match(/(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})/)
    if (!periodMatch || !timeMatch) continue
    const lines = content.split('\n')
    const name = lines[0]?.replace(/\s*\(.*?\)\s*/g, '').trim() || ''
    const teacher = lines.slice(1).join(', ').trim()
    lessons.push({
      period: `${periodMatch[1]}. Ders`,
      time: `${timeMatch[1]}-${timeMatch[2]}`,
      name,
      teacher
    })
  }
  return lessons
}

function isCurrentLesson(timeRange: string, hour: number, min: number): boolean {
  const match = timeRange.match(/(\d{2}):(\d{2})-(\d{2}):(\d{2})/)
  if (!match) return false
  const startMin = parseInt(match[1]) * 60 + parseInt(match[2])
  const endMin = parseInt(match[3]) * 60 + parseInt(match[4])
  const nowMin = hour * 60 + min
  return nowMin >= startMin && nowMin < endMin
}

export default function TodaySchedule() {
  const { data, loading } = useApi<ScheduleData>(
    '/api/schedule',
    { latest: {}, today: '' }
  )

  if (loading) return <Tile style={{ height: '120px' }}>Yükleniyor...</Tile>

  const rows = data.latest?.schedule?.rows || []
  const dayHeaders = rows[0] || []
  const todayIdx = dayHeaders.indexOf(data.today)
  if (todayIdx < 0) return (
    <div className="dashboard-card">
      <h4 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Time size={20} /> Bugün ders yok
      </h4>
    </div>
  )

  const lessons = parseLessons(rows, todayIdx)
  const now = new Date()
  const currentHour = now.getHours()
  const currentMin = now.getMinutes()

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Time size={20} />
        Bugünün Dersleri &mdash; {data.today}
      </h4>
      <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
        {lessons.map((lesson, i) => {
          const isActive = isCurrentLesson(lesson.time, currentHour, currentMin)
          return (
            <Tile key={i}
              className={isActive ? 'lesson-active' : ''}
              style={{
                minWidth: '160px', flex: '0 0 auto',
                borderLeft: isActive ? '3px solid var(--highlight-today)' : '3px solid transparent',
                padding: '0.75rem 1rem'
              }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--status-info)', fontWeight: 600 }}>
                {lesson.period} &middot; {lesson.time}
              </div>
              <div style={{ fontWeight: 600, margin: '0.25rem 0' }}>
                {lesson.name}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                {lesson.teacher}
              </div>
              {isActive && <Tag type="blue" size="sm">Şimdi</Tag>}
            </Tile>
          )
        })}
      </div>
    </div>
  )
}
