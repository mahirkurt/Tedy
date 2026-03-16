import { Accordion, AccordionItem, Tag } from '@carbon/react'
import { Notification } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/FocusModeContext'
import type { Announcement } from '../types'
import { formatTurkishDate, MONTHS_SHORT } from '../utils/formatters'

const DETAIL_FIELDS = [
  'e-Posta İçerik',
  'Duyuru Detayı',
  'İçerik',
  'Açıklama',
  'Mesaj',
] as const

function getAnnouncementDetail(ann: Announcement): string {
  for (const field of DETAIL_FIELDS) {
    const value = ann[field]
    if (value && value.trim() && value.trim() !== '-') return value.trim()
  }
  return 'Detay bulunamadı.'
}

function getWeekLabel(dateStr: string): string {
  const m = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})/)
  if (!m) return ''
  const d = new Date(+m[3], +m[2] - 1, +m[1])
  const startOfWeek = new Date(d)
  startOfWeek.setDate(d.getDate() - d.getDay() + 1)
  const day = startOfWeek.getDate()
  return `${day} ${MONTHS_SHORT[startOfWeek.getMonth()]} haftası`
}

function groupByWeek(announcements: Announcement[]): Map<string, Announcement[]> {
  const groups = new Map<string, Announcement[]>()
  for (const ann of announcements) {
    const week = getWeekLabel(ann["Yayın Tarihi"]) || 'Diğer'
    if (!groups.has(week)) groups.set(week, [])
    groups.get(week)!.push(ann)
  }
  return groups
}

export default function Announcements() {
  const { data } = useApi<{ announcements: Announcement[] }>(
    '/api/announcements', { announcements: [] }
  )
  const { focusMode } = useFocusMode()

  if (data.announcements.length === 0) return null

  const weekGroups = groupByWeek(data.announcements)
  const weeks = Array.from(weekGroups.entries())

  // Focus mode: show only the most recent week
  const visibleWeeks = focusMode ? weeks.slice(0, 1) : weeks

  return (
    <div className="dashboard-card">
      <h4 className="dashboard-card__title">
        <Notification size={20} />
        Okul Duyuruları
      </h4>
      {visibleWeeks.map(([weekLabel, anns]) => (
        <div key={weekLabel} className="announcements-week-group">
          <h5 className="announcements-week-group__label">{weekLabel}</h5>
          <Accordion>
            {anns.map((ann, i) => (
              <AccordionItem
                key={i}
                title={ann["e-Posta Başlık"]}
              >
                <div className="announcements-detail">
                  <Tag type="gray" size="sm">
                    {formatTurkishDate(ann["Yayın Tarihi"])}
                  </Tag>
                  <p className="announcements-detail__text">{getAnnouncementDetail(ann)}</p>
                  {ann["Ekleri"] && ann["Ekleri"] !== '-' && (
                    <p className="announcements-detail__attach">
                      Ek: {ann["Ekleri"]}
                    </p>
                  )}
                  {ann["Ekleri_url"] && (
                    <a
                      className="announcements-detail__link"
                      href={ann["Ekleri_url"]}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Eki aç
                    </a>
                  )}
                </div>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      ))}
    </div>
  )
}
