import { Tile, Tag } from '@carbon/react'
import { Notification } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { Announcement } from '../types'
import { formatTurkishDate } from '../utils/formatters'

export default function Announcements() {
  const { data } = useApi<{ announcements: Announcement[] }>(
    '/api/announcements', { announcements: [] }
  )

  if (data.announcements.length === 0) return null

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Notification size={20} />
        Okul Duyuruları
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        {data.announcements.map((ann, i) => (
          <Tile key={i} style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 500 }}>
              {ann["e-Posta Başlık"]}
            </span>
            <Tag type="gray" size="sm">
              {formatTurkishDate(ann["Yayın Tarihi"])}
            </Tag>
          </Tile>
        ))}
      </div>
    </div>
  )
}
