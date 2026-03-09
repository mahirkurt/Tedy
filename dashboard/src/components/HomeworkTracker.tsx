import { Tag, Tile } from '@carbon/react'
import { Task, Timer } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { HomeworkItem } from '../types'
import { parseDeadline, formatTurkishDate } from '../utils/formatters'
import { getCountdown } from '../utils/countdown'
import { useState, useEffect } from 'react'

const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000

export default function HomeworkTracker() {
  const { data: hwData } = useApi<{ summary: string; homework: HomeworkItem[] }>(
    '/api/homework', { summary: '', homework: [] }
  )

  const [, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 60000)
    return () => clearInterval(t)
  }, [])

  const now = Date.now()
  const portalHw = (hwData.homework || []).filter(hw => {
    const d = parseDeadline(hw["Ödev Son Teslim Tarihi"])
    return !d || d.getTime() >= now - TWO_WEEKS_MS
  })

  const sortedPortal = [...portalHw].sort((a, b) => {
    const aDate = parseDeadline(a["Ödev Son Teslim Tarihi"])
    const bDate = parseDeadline(b["Ödev Son Teslim Tarihi"])
    return (aDate?.getTime() || 0) - (bDate?.getTime() || 0)
  })

  const summaryLines = hwData.summary.split('\n').filter(l => l.trim())

  return (
    <div className="dashboard-card dashboard-card--accent">
      <h4 style={{ margin: '0 0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Task size={20} />
        Ödevler & Geri Sayım
      </h4>
      {summaryLines.length > 1 && (
        <p style={{ fontSize: '0.8125rem', color: '#525252', margin: '0 0 1rem' }}>
          {summaryLines.slice(1).join(' · ')}
        </p>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {sortedPortal.slice(0, 15).map((hw, i) => {
          const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
          const countdown = getCountdown(deadline)
          return (
            <Tile key={`p-${i}`} style={{ padding: '0.75rem 1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.8125rem' }}>
                      {hw.normalized_course || hw["Ders Adı"]}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8125rem' }}>{hw["Ödev Başlığı"]}</div>
                  <div style={{ fontSize: '0.75rem', color: '#525252', marginTop: '0.25rem' }}>
                    Teslim: {formatTurkishDate(hw["Ödev Son Teslim Tarihi"])}
                  </div>
                </div>
                <div style={{ textAlign: 'right', minWidth: '80px' }}>
                  {countdown.urgency !== 'expired' && (
                    <div className={countdown.urgency === 'urgent' ? 'tag-urgent' : ''}>
                      <Tag type={countdown.urgency === 'urgent' ? 'red' : countdown.urgency === 'soon' ? 'warm-gray' : 'blue'} size="sm">
                        <Timer size={12} /> {countdown.text}
                      </Tag>
                    </div>
                  )}
                  {countdown.urgency === 'expired' && (
                    <Tag type="warm-gray" size="sm">Süresi doldu</Tag>
                  )}
                </div>
              </div>
            </Tile>
          )
        })}
      </div>

    </div>
  )
}
