import { Calendar } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { CSSProperties } from 'react'

interface ScheduleData {
  latest: {
    week_label?: string
    schedule?: { rows: string[][] }
  }
  today: string
}

const DAYS = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma']

const SKIP_CONTENT = new Set([
  'Kahvaltı', 'Öğle yemeği', 'İkindi Kahvaltısı', 'Çıkış'
])

function formatTime(cell: string): string {
  const periodMatch = cell.match(/(\d+)\. Ders/)
  const timeMatch = cell.match(/(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})/)
  if (periodMatch && timeMatch) return `${periodMatch[1]}. ${timeMatch[1]}`
  const justTime = cell.match(/(\d{2}:\d{2})/)
  return justTime ? justTime[1] : cell
}

const thStyle: CSSProperties = {
  padding: '0.5rem 0.75rem',
  textAlign: 'left',
  borderBottom: '2px solid #E0E0E0',
  backgroundColor: '#F4F4F4',
  fontSize: '0.75rem'
}

const tdStyle: CSSProperties = {
  padding: '0.5rem 0.75rem',
  borderBottom: '1px solid #E0E0E0',
  verticalAlign: 'top',
  fontSize: '0.8125rem'
}

export default function WeeklySchedule() {
  const { data, loading } = useApi<ScheduleData>(
    '/api/schedule',
    { latest: {}, today: '' }
  )

  if (loading) return <div className="dashboard-card">Yükleniyor...</div>

  const rows = data.latest?.schedule?.rows || []
  if (rows.length === 0) return null

  const dayHeaders = rows[0] || []
  const dayIndices = DAYS.map(d => dayHeaders.indexOf(d)).filter(i => i >= 0)

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Calendar size={20} />
        Haftalık Program &mdash; {data.latest.week_label || ''}
      </h4>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={thStyle}>Saat</th>
              {DAYS.map((day, i) => (
                <th key={day}
                    className={day === data.today ? 'today-column' : ''}
                    style={{ ...thStyle, ...(dayIndices[i] < 0 ? { display: 'none' } : {}) }}>
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(1).map((row, ri) => {
              const timeCell = row[0] || ''
              if (!timeCell) return null
              // Skip break/meal rows
              const isBreak = row.some(c => SKIP_CONTENT.has(c))
              if (isBreak || timeCell.includes('Çıkış') || SKIP_CONTENT.has(timeCell)) return null
              return (
                <tr key={ri}>
                  <td style={{ ...tdStyle, fontWeight: 600, whiteSpace: 'nowrap', fontSize: '0.75rem' }}>
                    {formatTime(timeCell)}
                  </td>
                  {dayIndices.map((di, ci) => {
                    const cell = row[di] || ''
                    const lines = cell.split('\n')
                    const isToday = DAYS[ci] === data.today
                    return (
                      <td key={ci}
                          className={isToday ? 'today-column' : ''}
                          style={{ ...tdStyle, ...(isToday ? { backgroundColor: '#EDF5FF' } : {}) }}>
                        {lines[0] && (
                          <>
                            <div style={{ fontWeight: 500 }}>
                              {lines[0].replace(/\s*\(.*?\)\s*/g, '').trim()}
                            </div>
                            {lines[1] && (
                              <div style={{ fontSize: '0.6875rem', color: '#525252' }}>
                                {lines.slice(1).join(', ').trim()}
                              </div>
                            )}
                          </>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
