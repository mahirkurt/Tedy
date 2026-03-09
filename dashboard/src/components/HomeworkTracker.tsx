import { Tag, Tile, ComposedModal, ModalHeader, ModalBody } from '@carbon/react'
import { Task, Timer, Document } from '@carbon/icons-react'
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

  const [selectedHw, setSelectedHw] = useState<HomeworkItem | null>(null)
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
    <>
    <div className="dashboard-card dashboard-card--accent">
      <h4 className="dashboard-card__title dashboard-card__title--tight">
        <Task size={20} />
        Ödevler & Geri Sayım
      </h4>
      {summaryLines.length > 1 && (
        <p className="dashboard-summary-text">
          {summaryLines.slice(1).join(' · ')}
        </p>
      )}

      <div className="stack-sm">
        {sortedPortal.slice(0, 15).map((hw, i) => {
          const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
          const countdown = getCountdown(deadline)
          const tileClass = [
            'homework-item',
            'dashboard-list-tile',
            hw.detail ? 'homework-item--clickable' : '',
          ].filter(Boolean).join(' ')

          return (
            <Tile key={`p-${i}`} onClick={() => hw.detail && setSelectedHw(hw)}
              className={tileClass}>
              <div className="homework-item__row">
                <div className="homework-item__main">
                  <div className="homework-item__course">
                    {hw.normalized_course || hw["Ders Adı"]}
                  </div>
                  <div className="homework-item__title">{hw["Ödev Başlığı"]}</div>
                  <div className="homework-item__deadline">
                    Teslim: {formatTurkishDate(hw["Ödev Son Teslim Tarihi"])}
                  </div>
                </div>
                <div className="homework-item__countdown">
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

    <ComposedModal open={!!selectedHw} onClose={() => setSelectedHw(null)} size="md">
      <ModalHeader
        title={selectedHw?.["Ödev Başlığı"] || ''}
        label={selectedHw?.normalized_course || selectedHw?.["Ders Adı"] || ''}
      />
      <ModalBody>
        {selectedHw?.detail?.description && (
          <p className="homework-modal__description">
            {selectedHw.detail.description}
          </p>
        )}
        {(selectedHw?.detail?.attachments?.length ?? 0) > 0 && (
          <div className="homework-modal__attachments">
            <h5 className="homework-modal__attachments-title">Ekler</h5>
            {selectedHw!.detail!.attachments.map((att, i) => (
              <a key={i} href={att.url} target="_blank" rel="noopener noreferrer"
                 className="homework-modal__attachment-link">
                <Document size={16} /> {att.name}
              </a>
            ))}
          </div>
        )}
      </ModalBody>
    </ComposedModal>
    </>
  )
}
