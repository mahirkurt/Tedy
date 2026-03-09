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
      <h4 className="dashboard-card__title">
        <Notification size={20} />
        Okul Duyuruları
      </h4>
      <div className="stack-xs">
        {data.announcements.map((ann, i) => (
          <Tile key={i} className="dashboard-list-tile dashboard-list-tile--between">
            <span className="dashboard-list-tile__label">
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
