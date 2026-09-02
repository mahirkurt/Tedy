import { useApi } from '../hooks/useApi'
import type { HealthData } from '../types'

function formatSyncAgo(timestamp?: string): string {
  if (!timestamp) return ''
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return ''
  const mins = Math.floor((Date.now() - parsed.getTime()) / 60000)
  if (mins < 1) return 'az önce'
  if (mins < 60) return `${mins} dk önce`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} saat önce`
  return `${Math.floor(hours / 24)} gün önce`
}

export default function DashboardFooter() {
  const { data: health } = useApi<HealthData | null>('/api/health', null)
  const syncAt = health?.staleness?.last_successful_full_scrape || health?.timestamp
  const ago = formatSyncAgo(syncAt)
  const year = new Date().getFullYear()

  return (
    <footer className="dashboard-footer">
      <p>
        TED Rönesans Koleji · TEDY {year}
        {ago ? ` · Son senkron ${ago}` : ''}
      </p>
    </footer>
  )
}
