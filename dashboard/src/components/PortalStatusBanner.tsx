import { InlineNotification } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { SECTION_LABELS } from '../utils/formatters'
import type { HealthData } from '../types'

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
export function PortalStatusBanner() {
  const { data: health } = useApi<HealthData | null>('/api/health', null)

  const unavailable = health?.unavailable
  const keys = unavailable ? Object.keys(unavailable) : []
  if (keys.length === 0) return null

  const names = keys.map(k => SECTION_LABELS[k] || k)
  const details = keys
    .map(k => unavailable?.[k]?.detail)
    .filter((d): d is string => Boolean(d && d.trim()))

  return (
    <InlineNotification
      className="portal-status"
      kind="info"
      lowContrast
      hideCloseButton
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
  )
}
