import { useState, useRef, useEffect } from 'react'
import {
  Header, HeaderName, HeaderMenuButton, HeaderGlobalBar, HeaderGlobalAction,
  Tag, SkeletonText
} from '@carbon/react'
import {
  Renew, Logout,
  CheckmarkFilled, WarningFilled, ErrorFilled, SkipForwardFilled
} from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import type { HealthData, SectionHealth } from '../types'
import type { User } from '../hooks/useAuth'

const SECTION_LABELS: Record<string, string> = {
  odevlerim: 'Ödevler',
  ders_programi: 'Ders Programı',
  takvim: 'Takvim',
  gelisim_raporu: 'Notlar',
  ders_icerikleri: 'Ders İçerikleri',
  takim_calismalari: 'Takımlar',
  ogep: 'ÖGEP',
  duyurular: 'Duyurular',
}

function StatusIcon({ status }: { status: SectionHealth['status'] }) {
  if (status === 'ok') return <CheckmarkFilled size={14} style={{ color: 'var(--status-success)' }} />
  if (status === 'warning') return <WarningFilled size={14} style={{ color: 'var(--status-warning)' }} />
  if (status === 'error') return <ErrorFilled size={14} style={{ color: 'var(--status-error)' }} />
  return <SkipForwardFilled size={14} style={{ color: '#A8A8A8' }} />
}

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
  isSideNavExpanded: boolean
  onClickSideNavExpand: () => void
}

export default function DashboardHeader({ user, onLogout, isSideNavExpanded, onClickSideNavExpand }: Props) {
  const { data: health, loading, refresh } = useApi<HealthData>(
    '/api/health',
    { timestamp: '', success: false, scrape_errors: [], duration_seconds: 0 }
  )
  const [healthOpen, setHealthOpen] = useState(false)
  const popoverRef = useRef<HTMLDivElement>(null)

  // Close popover on outside click
  useEffect(() => {
    if (!healthOpen) return
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setHealthOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [healthOpen])

  const syncAgo = health.timestamp ? getTimeAgo(health.timestamp) : '...'
  const warningCount = (health.validation_warnings?.length || 0)
    + (health.scrape_errors?.length || 0)
  const tagType = !health.timestamp ? 'gray'
    : health.success ? (warningCount > 0 ? 'warm-gray' : 'green')
    : 'red'
  const tagText = warningCount > 0 ? `${syncAgo} · ${warningCount} uyarı` : syncAgo

  return (
    <Header aria-label="TEDY Dashboard">
      <HeaderMenuButton
        aria-label="Menü"
        isActive={isSideNavExpanded}
        onClick={onClickSideNavExpand}
      />
      <HeaderName href="/" prefix="">
        <img src="/tedy-logo-white.svg" alt="TEDY" className="dashboard-header__brand-logo" />
      </HeaderName>
      <HeaderGlobalBar>
        <span className="dashboard-header__meta">
          {user.picture && (
            <img
              src={user.picture}
              alt=""
              className="dashboard-header__avatar"
              referrerPolicy="no-referrer"
            />
          )}
          <strong>{user.name || user.email}</strong>
          <span style={{ position: 'relative' }} ref={popoverRef}>
            <button
              type="button"
              onClick={() => setHealthOpen(o => !o)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              {loading ? (
                <SkeletonText width="60px" />
              ) : (
                <Tag type={tagType} size="sm">{tagText}</Tag>
              )}
            </button>
            {healthOpen && !loading && (
              <div className="health-popover">
                <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
                  Son Sync: {health.timestamp
                    ? new Date(health.timestamp).toLocaleString('tr-TR')
                    : '—'}
                </p>
                {health.login && (
                  <p style={{ color: '#525252', marginBottom: '0.5rem' }}>
                    Login: {health.login.method === 'cached_session'
                      ? 'Kayıtlı oturum'
                      : health.login.method === 'captcha_login'
                        ? `CAPTCHA (${health.login.captcha_attempts} deneme)`
                        : 'Başarısız'}
                  </p>
                )}
                <p style={{ color: '#525252', marginBottom: '0.75rem' }}>
                  Süre: {health.duration_seconds}s
                </p>
                {health.sections && Object.entries(health.sections).map(([key, sec]) => (
                  <div key={key} className="health-popover__row">
                    <span>{SECTION_LABELS[key] || key}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      {sec.count} öğe
                      <StatusIcon status={sec.status} />
                    </span>
                  </div>
                ))}
              </div>
            )}
          </span>
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
