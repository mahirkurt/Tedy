import {
  Header, HeaderName, HeaderGlobalBar, HeaderGlobalAction,
  Tag, SkeletonText
} from '@carbon/react'
import { Renew, Logout } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { HealthData } from '../types'
import type { User } from '../hooks/useAuth'

function getTimeAgo(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Az önce'
  if (mins < 60) return `${mins} dk önce`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} saat önce`
  return `${Math.floor(hours / 24)} gün önce`
}

interface Props {
  user: User
  onLogout: () => void
}

export default function DashboardHeader({ user, onLogout }: Props) {
  const { data: health, loading, refresh } = useApi<HealthData>(
    '/api/health',
    { timestamp: '', success: false, scrape_errors: [], duration_seconds: 0 }
  )

  const syncAgo = health.timestamp ? getTimeAgo(health.timestamp) : '...'

  return (
    <Header aria-label="TEDY Dashboard">
      <HeaderName href="/" prefix="">
        <img src="/tedy-logo-white.svg" alt="TEDY" style={{
          height: 28, verticalAlign: 'middle'
        }} />
      </HeaderName>
      <HeaderGlobalBar>
        <span style={{
          color: 'var(--ted-header-text)', padding: '0 1rem',
          display: 'flex', alignItems: 'center', gap: '0.75rem',
          fontSize: '0.875rem'
        }}>
          {user.picture && (
            <img src={user.picture} alt="" style={{
              width: 24, height: 24, borderRadius: '50%'
            }} referrerPolicy="no-referrer" />
          )}
          <strong>{user.name || user.email}</strong>
          {loading ? (
            <SkeletonText width="60px" />
          ) : (
            <Tag type={health.success ? 'green' : 'red'} size="sm">
              {syncAgo}
            </Tag>
          )}
        </span>
        <HeaderGlobalAction aria-label="Yenile" onClick={refresh}>
          <Renew size={20} />
        </HeaderGlobalAction>
        <HeaderGlobalAction aria-label="Çıkış" onClick={onLogout}>
          <Logout size={20} />
        </HeaderGlobalAction>
      </HeaderGlobalBar>
    </Header>
  )
}
