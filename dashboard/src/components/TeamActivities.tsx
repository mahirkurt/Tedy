import { Tag,
  StructuredListWrapper, StructuredListHead, StructuredListRow,
  StructuredListCell, StructuredListBody,
} from '@carbon/react'
import { GroupPresentation } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/FocusModeContext'
import type { TeamActivity, OgepSession } from '../types'

const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000

function parseTurkishDate(s: string): Date | null {
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!m) return null
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5])
}

function formatShortDate(s: string): string {
  const m = s.match(/(\d{2})\.(\d{2})\.\d{4}\s+(\d{2}):(\d{2})/)
  if (!m) return s
  return `${m[1]}.${m[2]} ${m[3]}:${m[4]}`
}

export default function TeamActivities() {
  const { data } = useApi<{ activities: TeamActivity[]; ogep: OgepSession[] }>(
    '/api/teams', { activities: [], ogep: [] }
  )
  const { focusMode } = useFocusMode()

  const now = Date.now()
  let activities = data.activities.filter(a => {
    const d = parseTurkishDate(a["Çalışma Başlangıç"])
    return !d || d.getTime() >= now - TWO_WEEKS_MS
  })
  let ogep = data.ogep.filter(s => {
    const d = parseTurkishDate(s["Çalışma Başlangıç"])
    return !d || d.getTime() >= now - TWO_WEEKS_MS
  })

  // Focus mode: show only upcoming
  if (focusMode) {
    activities = activities.filter(a => {
      const d = parseTurkishDate(a["Çalışma Başlangıç"])
      return !d || d.getTime() >= now
    })
    ogep = ogep.filter(s => {
      const d = parseTurkishDate(s["Çalışma Başlangıç"])
      return !d || d.getTime() >= now
    })
  }

  if (activities.length === 0 && ogep.length === 0) return null

  return (
    <div className="dashboard-card">
      <h4 className="dashboard-card__title">
        <GroupPresentation size={20} />
        Takım Çalışmaları & ÖGEP
      </h4>

      {activities.length > 0 && (
        <>
          <h5 className="team-section-label">Academy+</h5>
          <StructuredListWrapper isCondensed>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Etkinlik</StructuredListCell>
                <StructuredListCell head>Tarih</StructuredListCell>
                <StructuredListCell head>Durum</StructuredListCell>
                {!focusMode && <StructuredListCell head>Konum</StructuredListCell>}
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {activities.map((a, i) => (
                <StructuredListRow key={i}>
                  <StructuredListCell className="team-cell-name">
                    {a["Academy+"]}
                  </StructuredListCell>
                  <StructuredListCell className="team-cell-date">
                    {formatShortDate(a["Çalışma Başlangıç"])}
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag type={a["Katılım Durumu"] === "Katıldı" ? 'green' : 'gray'} size="sm">
                      {a["Katılım Durumu"] || 'Bekliyor'}
                    </Tag>
                  </StructuredListCell>
                  {!focusMode && (
                    <StructuredListCell>
                      <Tag type={a["Teams Link"] === "Yüz Yüze" ? 'blue' : 'teal'} size="sm">
                        {a["Teams Link"]}
                      </Tag>
                    </StructuredListCell>
                  )}
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
        </>
      )}

      {ogep.length > 0 && (
        <>
          <h5 className="team-section-label">ÖGEP Oturumları</h5>
          <StructuredListWrapper isCondensed>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Oturum</StructuredListCell>
                <StructuredListCell head>Tarih</StructuredListCell>
                <StructuredListCell head>Katılım</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {ogep.map((s, i) => (
                <StructuredListRow key={i}>
                  <StructuredListCell className="team-cell-name">
                    {s["ÖGEP (Öğrenci Gelişim Programı)"]}
                  </StructuredListCell>
                  <StructuredListCell className="team-cell-date">
                    {formatShortDate(s["Çalışma Başlangıç"])}
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag type={s["Katılım Durumu"] === "Katıldı" ? 'green' : 'gray'} size="sm">
                      {s["Katılım Durumu"] || 'Bekliyor'}
                    </Tag>
                  </StructuredListCell>
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
        </>
      )}
    </div>
  )
}
