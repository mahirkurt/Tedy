import { useState, useRef, useEffect } from 'react'
import {
  Header, HeaderName, HeaderMenuButton, HeaderGlobalBar, HeaderGlobalAction,
  Tag, SkeletonText, Toggle
} from '@carbon/react'
import {
  Renew, Logout,
  CheckmarkFilled, WarningFilled, ErrorFilled, SkipForwardFilled
} from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import type { HealthData, SectionHealth } from '../types'
import type { User } from '../hooks/useAuth'
import { SECTION_LABELS } from '../utils/formatters'

function StatusIcon({ status }: { status: SectionHealth['status'] }) {
  if (status === 'ok') return <CheckmarkFilled size={14} style={{ color: 'var(--status-success)' }} />
  if (status === 'warning') return <WarningFilled size={14} style={{ color: 'var(--status-warning)' }} />
  if (status === 'error') return <ErrorFilled size={14} style={{ color: 'var(--status-error)' }} />
  // 'unavailable' means the portal itself refused the page — not our failure,
  // but distinct from a skip, so it gets its own colour rather than falling
  // through to the grey skip icon.
  if (status === 'unavailable') return <WarningFilled size={14} style={{ color: 'var(--cds-support-caution-undefined)' }} />
  // Muted rather than near-invisible: the old #A8A8A8 sat at 2.2:1 on the
  // popover's white ground, under the 3:1 floor for a glyph that carries state.
  return <SkipForwardFilled size={14} style={{ color: 'var(--cds-text-helper)' }} />
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

function formatSyncDateTime(timestamp?: string): string {
  if (!timestamp) return '—'
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleString('tr-TR')
}

interface Props {
  user: User
  onLogout: () => void
  isSideNavExpanded: boolean
  onClickSideNavExpand: () => void
}

export default function DashboardHeader({ user, onLogout, isSideNavExpanded, onClickSideNavExpand }: Props) {
  const { focusMode, toggleFocusMode } = useFocusMode()
  const { data: health, loading, refresh } = useApi<HealthData>(
    '/api/health',
    { timestamp: '', success: false, scrape_errors: [], duration_seconds: 0 }
  )
  const [healthOpen, setHealthOpen] = useState(false)
  const popoverRef = useRef<HTMLElement>(null)

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

  useEffect(() => {
    if (!healthOpen) return
    function onEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') setHealthOpen(false)
    }
    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [healthOpen])

  const effectiveSyncTimestamp = health.staleness?.last_successful_full_scrape || health.timestamp
  const syncAgo = effectiveSyncTimestamp ? getTimeAgo(effectiveSyncTimestamp) : 'Bekleniyor'
  const staleSections = health.staleness?.stale_sections || []
  const warningCount = (health.validation_warnings?.length || 0)
    + (health.scrape_errors?.length || 0)
    + staleSections.length
  // A constant "4 uyarı" is an alarm that never resolves (İ6). Name the
  // sync, and only mention warnings when there are some and we are not in
  // focus — focus silences badges (§5). Gray, not warm-gray: the count is
  // information, not a yellow emergency.
  const showWarningCount = warningCount > 0 && !focusMode
  const tagType: 'gray' | 'red' = !effectiveSyncTimestamp || health.success
    ? 'gray'
    : 'red'
  const tagText = showWarningCount ? `${syncAgo} · ${warningCount} uyarı` : syncAgo
  const shortTagText = showWarningCount ? `${warningCount} uyarı` : syncAgo
  const displayName = (user.name || '').trim() || user.email
  const shortDisplayName = displayName.split(/\s+/)[0] || displayName

  return (
    <>
      <Header aria-label="TEDY Dashboard">
        <HeaderMenuButton
          aria-label="Menü"
          isActive={isSideNavExpanded}
          onClick={onClickSideNavExpand}
        />
        <HeaderName href="/" prefix="">
          <picture>
            {/* Windows high contrast paints the band in the system Canvas, usually
                white; the white logo vanished on it (2026-09-25). */}
            <source srcSet="/tedy-logo.svg" media="(forced-colors: active)" />
            <img src="/tedy-logo-white.svg" alt="TEDY" className="dashboard-header__brand-logo" />
          </picture>
        </HeaderName>
        <HeaderGlobalBar>
          <div className="dashboard-header__meta">
            {user.picture && (
              <img
                src={user.picture}
                alt={`${displayName} profil fotoğrafı`}
                className="dashboard-header__avatar"
                referrerPolicy="no-referrer"
              />
            )}
            <div className="dashboard-header__identity">
              <strong className="dashboard-header__user-name dashboard-header__user-name--full">{displayName}</strong>
              <strong className="dashboard-header__user-name dashboard-header__user-name--short">{shortDisplayName}</strong>
              <span className="dashboard-header__user-email">{user.email}</span>
            </div>
            <span className="dashboard-header__health-wrap" ref={popoverRef}>
              <button
                type="button"
                onClick={() => setHealthOpen(o => !o)}
                className="dashboard-header__health-trigger"
                // Named by its visible text plus a hidden prefix, not an
                // aria-label: "Senkron durumunu göster" on a button reading
                // "15 dk önce" failed WCAG 2.5.3 — a voice user says what they see.
                aria-expanded={healthOpen}
                aria-haspopup="dialog"
              >
                <span className="cds--visually-hidden">Senkron durumu: </span>
                {loading ? (
                  <SkeletonText width="72px" />
                ) : (
                  <Tag
                    type={tagType}
                    size="sm"
                    title={formatSyncDateTime(effectiveSyncTimestamp)}
                  >
                    <span className="dashboard-header__sync-label dashboard-header__sync-label--full">{tagText}</span>
                    <span className="dashboard-header__sync-label dashboard-header__sync-label--short">{shortTagText}</span>
                  </Tag>
                )}
              </button>
              {healthOpen && !loading && (
                <div className="health-popover" role="dialog" aria-label="Senkron sağlık bilgisi">
                  <p className="health-popover__title">Senkron Sağlığı</p>
                  <p className="health-popover__meta">
                    <span className="health-popover__meta-label">Son Sync:</span>
                    <span className="health-popover__meta-value">{formatSyncDateTime(effectiveSyncTimestamp)}</span>
                  </p>
                  <p className="health-popover__meta">
                    <span className="health-popover__meta-label">Son Başarılı Tam Sync:</span>
                    <span className="health-popover__meta-value">{formatSyncDateTime(health.staleness?.last_successful_full_scrape || effectiveSyncTimestamp)}</span>
                  </p>
                  {health.login && (
                    <p className="health-popover__meta">
                      <span className="health-popover__meta-label">Login:</span>
                      <span className="health-popover__meta-value">{health.login.method === 'cached_session'
                        ? 'Kayıtlı oturum'
                        : health.login.method === 'captcha_login'
                          ? `CAPTCHA (${health.login.captcha_attempts} deneme)`
                          : 'Başarısız'}</span>
                    </p>
                  )}
                  <p className="health-popover__meta">
                    <span className="health-popover__meta-label">Süre:</span>
                    <span className="health-popover__meta-value">{health.duration_seconds}s</span>
                  </p>
                  {staleSections.length > 0 && (
                    <p className="health-popover__warning">
                      {staleSections.length} bölüm eski veriyle gösteriliyor.
                    </p>
                  )}
                  {health.sections && Object.entries(health.sections).map(([key, sec]) => (
                    <div key={key} className="health-popover__row">
                      <span
                        title={health.unavailable?.[key]?.detail || undefined}
                      >
                        {SECTION_LABELS[key] || key}
                      </span>
                      <span className="health-popover__value">
                        {sec.count} öğe
                        <StatusIcon status={sec.status} />
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </span>
          </div>
          <div className="dashboard-header__focus-toggle">
            <Toggle
              id="focus-mode-toggle"
              size="sm"
              labelA="Odak"
              labelB="Odak"
              aria-label="Odak"
              toggled={focusMode}
              onToggle={toggleFocusMode}
            />
          </div>
          <HeaderGlobalAction aria-label="Yenile" onClick={refresh}>
            <Renew size={20} />
          </HeaderGlobalAction>
          <HeaderGlobalAction aria-label="Çıkış" onClick={onLogout}>
            <Logout size={20} />
          </HeaderGlobalAction>
        </HeaderGlobalBar>
      </Header>
    </>
  )
}
