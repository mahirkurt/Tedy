import { useState } from 'react'
import { InlineNotification } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { SECTION_LABELS } from '../utils/formatters'
import type { HealthData } from '../types'

const DISMISS_KEY = 'tedy-portal-banner-dismissed'

function todayKey(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function wasDismissedToday(): boolean {
  try {
    return sessionStorage.getItem(DISMISS_KEY) === todayKey()
  } catch {
    return false
  }
}

/**
 * Says, once and in the open, which parts of the dashboard are empty because
 * the portal is not serving them.
 *
 * The reason has always been in /api/health, but only as a `title=` tooltip on
 * a row inside the header's health popover — so an empty Program page read as
 * "our sync is broken" when it actually meant "the school closed the module".
 * Only sections the portal explicitly refused appear here; a genuinely empty
 * table (no homework set yet) is not a fault and gets no banner.
 */
/**
 * Which surfaces show a given section. An unread section is worth saying on
 * the page whose emptiness it explains and nowhere else: telling Işık on
 * Takvim that her homework could not be read is noise (İ6), and saying
 * nothing on İşler — where she is looking at the empty list — is the bug
 * this exists to fix.
 */
const BOLUM_YUZEYLERI: Record<string, string[]> = {
  odevlerim: ['/', '/isler'],
  ders_programi: ['/', '/dersler'],
  ders_icerikleri: ['/dersler'],
  takvim: ['/', '/takvim'],
  gelisim_raporu: ['/notlar'],
  duyurular: ['/duyurular'],
  takim_calismalari: ['/takimlar'],
  ogep: ['/takimlar'],
  ogrenci_profili: ['/profil'],
}

export function PortalStatusBanner({ pathname = '' }: { pathname?: string }) {
  const { data: health } = useApi<HealthData | null>('/api/health', null)
  const [dismissed, setDismissed] = useState(wasDismissedToday)

  const unavailable = health?.unavailable
  const keys = unavailable ? Object.keys(unavailable) : []
  const okunamadi = health?.okunamadi
  const unreadKeys = (okunamadi ? Object.keys(okunamadi) : [])
    .filter(k => (BOLUM_YUZEYLERI[k] || []).includes(pathname))

  // The closed-portal sentence names Ders Programı and Takvim, so it belongs
  // on the two pages that render them and nowhere else. Dismissal is its
  // alone: the unread warning is meant to disappear by itself on the next
  // sync that works, not to be silenced for a day.
  const showClosed = keys.length > 0 && !dismissed
    && (pathname === '/dersler' || pathname === '/takvim')

  if (!showClosed && unreadKeys.length === 0) return null

  const names = keys.map(k => SECTION_LABELS[k] || k)
  const details = keys
    .map(k => unavailable?.[k]?.detail)
    .filter((d): d is string => Boolean(d && d.trim()))
  const unreadNames = unreadKeys.map(k => SECTION_LABELS[k] || k)

  return (
    <>
      {showClosed && (
        <InlineNotification
          className="portal-status"
          kind="info"
          lowContrast
          onClose={() => {
            try { sessionStorage.setItem(DISMISS_KEY, todayKey()) } catch { /* ignore */ }
            setDismissed(true)
          }}
          title={
            names.length > 1
              ? `Portal şu an ${names.join(' ve ')} bölümlerini sunmuyor`
              : `Portal şu an ${names[0]} bölümünü sunmuyor`
          }
          subtitle={
            details.join(' · ')
            + (health?.academic_year ? ` — ${health.academic_year} öğretim yılı` : '')
          }
        />
      )}
      {/* A different sentence, because it is a different fact. "The school
          closed this module" and "we could not read it" both leave the page
          empty, and for nearly two hours on 2026-09-21 the second was being
          told as the first — every surface said "portalda kayıt yok" while
          the homework, the timetable and the grades were simply unread.
          Not dismissible for the day: it is meant to go away by itself on
          the next sync that works. */}
      {unreadKeys.length > 0 && (
        <InlineNotification
          className="portal-unread"
          kind="warning"
          lowContrast
          hideCloseButton
          title={
            unreadNames.length > 1
              ? `${unreadNames.join(', ')} bu turda okunamadı`
              : `${unreadNames[0]} bu turda okunamadı`
          }
          subtitle="Boş görünmeleri veri olmadığı anlamına gelmiyor — bir sonraki senkronda yeniden denenecek."
        />
      )}
    </>
  )
}
