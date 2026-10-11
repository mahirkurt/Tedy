import { useState } from 'react'
import { ContainedList, ContainedListItem } from '@carbon/react'
import { CheckmarkOutline, GroupPresentation } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import type { TeamActivity, OgepSession } from '../types'
import { EmptyLine } from './patterns/EmptyLine'

const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000

function parseTurkishDate(s?: string | null): Date | null {
  if (!s) return null
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!m) return null
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5])
}

function formatShortDate(s?: string | null): string {
  if (!s) return ''
  const m = s.match(/(\d{2})\.(\d{2})\.\d{4}\s+(\d{2}):(\d{2})/)
  if (!m) return s
  return `${m[1]}.${m[2]} ${m[3]}:${m[4]}`
}

function IsSatiri({ ad, ek, zaman, durum }: { ad?: string; ek?: string; zaman: string; durum?: string }) {
  const katildi = durum === 'Katıldı'
  return <span className="is-satiri">
    <span className="is-satiri__ana">
      <span className="is-satiri__ad">{ad}</span>
      {ek && <span className="is-satiri__ek">{ek}</span>}
    </span>
    <span className="is-satiri__yan">
      {zaman && <span className="is-satiri__zaman tedy-time">{zaman}</span>}
      <span className="is-satiri__durum">
        {katildi && <CheckmarkOutline size={16} aria-hidden="true" />}
        {durum || 'Bekliyor'}
      </span>
    </span>
  </span>
}

export default function TeamActivities() {
  const { data } = useApi<{ activities: TeamActivity[]; ogep: OgepSession[] }>(
    '/api/teams', { activities: [], ogep: [] }
  )
  const { focusMode } = useFocusMode()

  // Pinned when the view opens: the two-week window must not shift underfoot
  // while the list is on screen.
  const [now] = useState(() => Date.now())
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

  // Returning null left the page blank, which reads the same as a page that
  // failed to load (D3).
  if (activities.length === 0 && ogep.length === 0) {
    return <EmptyLine label="Takım çalışmaları &amp; ÖGEP">Kayıtlı takım etkinliği veya ÖGEP oturumu yok.</EmptyLine>
  }

  return (
    <div className="dashboard-card">
      <h2 className="dashboard-card__title">
        <GroupPresentation size={20} />
        Takım çalışmaları & <abbr title="Öğrenci Gelişim Programı">ÖGEP</abbr>
      </h2>

      {/* B65 (§4.6, §2.2): one-line work rows, not a three-column table — the name leads, the time sits on
          the right in mono, the status is a word with its icon (S4); a finished row stays neutral (İ7). */}
      {activities.length > 0 && (
        <ContainedList label={`Academy+ (${activities.length})`} kind="on-page" size="lg" className="team-list">
          {activities.map((a, i) => (
            <ContainedListItem key={i}>
              <IsSatiri ad={a["Academy+"]} ek={focusMode ? '' : a["Teams Link"]}
                zaman={formatShortDate(a["Çalışma Başlangıç"])} durum={a["Katılım Durumu"]} />
            </ContainedListItem>
          ))}
        </ContainedList>
      )}

      {ogep.length > 0 && (
        <ContainedList label={`ÖGEP oturumları (${ogep.length})`} kind="on-page" size="lg" className="team-list">
          {ogep.map((s, i) => (
            <ContainedListItem key={i}>
              <IsSatiri ad={s["ÖGEP (Öğrenci Gelişim Programı)"]} zaman={formatShortDate(s["Çalışma Başlangıç"])}
                durum={s["Katılım Durumu"]} />
            </ContainedListItem>
          ))}
        </ContainedList>
      )}
    </div>
  )
}
