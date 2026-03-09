import { Tag, Tile } from '@carbon/react'
import { GroupPresentation } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { TeamActivity, OgepSession } from '../types'

const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000

function parseTurkishDate(s: string): Date | null {
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!m) return null
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5])
}

export default function TeamActivities() {
  const { data } = useApi<{ activities: TeamActivity[]; ogep: OgepSession[] }>(
    '/api/teams', { activities: [], ogep: [] }
  )

  const now = Date.now()
  const activities = data.activities.filter(a => {
    const d = parseTurkishDate(a["Çalışma Başlangıç"])
    return !d || d.getTime() >= now - TWO_WEEKS_MS
  })
  const ogep = data.ogep.filter(s => {
    const d = parseTurkishDate(s["Çalışma Başlangıç"])
    return !d || d.getTime() >= now - TWO_WEEKS_MS
  })

  if (activities.length === 0 && ogep.length === 0) return null

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <GroupPresentation size={20} />
        Takım Çalışmaları & ÖGEP
      </h4>

      {activities.length > 0 && (
        <>
          <h5 style={{ fontSize: '0.8125rem', margin: '0 0 0.5rem', color: '#525252' }}>Academy+</h5>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }}>
            {activities.map((a, i) => (
              <Tile key={i} style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: '0.8125rem' }}>{a["Academy+"]}</div>
                  <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                    {a["Çalışma Başlangıç"]} &mdash; {a["Çalışma Bitiş"]}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Tag type={a["Katılım Durumu"] === "Katıldı" ? 'green' : 'gray'} size="sm">
                    {a["Katılım Durumu"] || 'Bekliyor'}
                  </Tag>
                  <Tag type={a["Teams Link"] === "Yüz Yüze" ? 'blue' : 'teal'} size="sm">
                    {a["Teams Link"]}
                  </Tag>
                </div>
              </Tile>
            ))}
          </div>
        </>
      )}

      {ogep.length > 0 && (
        <>
          <h5 style={{ fontSize: '0.8125rem', margin: '0 0 0.5rem', color: '#525252' }}>ÖGEP Oturumları</h5>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            {ogep.map((s, i) => (
              <Tile key={i} style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: '0.8125rem' }}>
                    {s["ÖGEP (Öğrenci Gelişim Programı)"]}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                    {s["Çalışma Başlangıç"]} &mdash; {s["Çalışma Bitiş"]}
                  </div>
                </div>
                <Tag type={s["Katılım Durumu"] === "Katıldı" ? 'green' : 'gray'} size="sm">
                  {s["Katılım Durumu"] || 'Bekliyor'}
                </Tag>
              </Tile>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
