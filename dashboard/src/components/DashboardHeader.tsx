import { useState, useRef, useEffect, useMemo, type ChangeEvent } from 'react'
import {
  Header, HeaderName, HeaderMenuButton, HeaderGlobalBar, HeaderGlobalAction,
  Tag, SkeletonText, Toggle,
  ComposedModal, ModalHeader, ModalBody, ModalFooter, Button
} from '@carbon/react'
import {
  Renew, Logout, Camera,
  CheckmarkFilled, WarningFilled, ErrorFilled, SkipForwardFilled
} from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import type { HealthData, SectionHealth, PrivateLesson } from '../types'
import type { User } from '../hooks/useAuth'
import { COURSE_CONTENT_ORDER, SECTION_LABELS } from '../utils/formatters'

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
  const { data: privateLessonData } = useApi<{ lessons: PrivateLesson[] }>(
    '/api/private-lessons',
    { lessons: [] }
  )
  const [healthOpen, setHealthOpen] = useState(false)
  const [photoProcessing, setPhotoProcessing] = useState(false)
  const [photoModalOpen, setPhotoModalOpen] = useState(false)
  const [selectedPhoto, setSelectedPhoto] = useState<File | null>(null)
  const [sourceType, setSourceType] = useState<'ted' | 'private'>('ted')
  const [course, setCourse] = useState('Matematik')
  const [privateLessonId, setPrivateLessonId] = useState('')
  const [dueDate, setDueDate] = useState('')
  const popoverRef = useRef<HTMLElement>(null)
  const photoCaptureInputRef = useRef<HTMLInputElement>(null)
  const photoUploadInputRef = useRef<HTMLInputElement>(null)

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
  // Memoised so the `|| []` fallback does not mint a new array on every render
  // and invalidate the hooks below.
  const privateLessons = useMemo(
    () => privateLessonData.lessons || [],
    [privateLessonData]
  )
  const displayName = (user.name || '').trim() || user.email
  const shortDisplayName = displayName.split(/\s+/)[0] || displayName

  const courseOptions = useMemo(() => {
    const lessonCourses = privateLessons.map(l => l.course).filter(Boolean)
    return Array.from(new Set([...COURSE_CONTENT_ORDER, ...lessonCourses]))
  }, [privateLessons])

  useEffect(() => {
    if (courseOptions.length === 0) return
    if (!course || !courseOptions.includes(course)) {
      setCourse(courseOptions[0])
    }
  }, [courseOptions, course])

  useEffect(() => {
    if (sourceType !== 'private') return
    if (!privateLessonId && privateLessons.length > 0) {
      setPrivateLessonId(privateLessons[0].id)
      return
    }
    const selected = privateLessons.find(l => l.id === privateLessonId)
    if (selected?.course) setCourse(selected.course)
  }, [sourceType, privateLessonId, privateLessons])

  function resetPhotoFlow() {
    setSelectedPhoto(null)
    setSourceType('ted')
    setPrivateLessonId('')
    setDueDate('')
    setPhotoModalOpen(false)
  }

  function handlePhotoSelected(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    if (!file.type.startsWith('image/')) {
      window.alert('Lütfen bir görsel dosyası seçin.')
      return
    }
    setSelectedPhoto(file)
  }

  async function submitPhotoHomework() {
    if (!selectedPhoto) return
    if (!course) {
      window.alert('Lütfen ders seçin.')
      return
    }
    if (sourceType === 'private' && !privateLessonId) {
      window.alert('Lütfen öğrenciye tanımlı bir özel ders seçin.')
      return
    }
    setPhotoProcessing(true)
    try {
      const formData = new FormData()
      formData.append('photo', selectedPhoto)
      formData.append('source_type', sourceType)
      formData.append('course', course)
      if (privateLessonId) formData.append('private_lesson_id', privateLessonId)
      if (dueDate) formData.append('due_date', dueDate)
      const res = await fetch('/api/homework/photo', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      })
      const payload = await res.json().catch(() => null)
      if (!res.ok) {
        throw new Error(payload?.error || `HTTP ${res.status}`)
      }

      const addedCount = Number(payload?.added_count || 0)
      const skippedCount = Number(payload?.skipped_count || 0)
      window.dispatchEvent(new CustomEvent('tedy:homework-updated'))
      resetPhotoFlow()
      if (addedCount > 0) {
        window.alert(`${addedCount} ödev AI ile işlendi ve sisteme eklendi.`)
      } else {
        window.alert(`Yeni ödev eklenmedi. ${skippedCount} kayıt zaten mevcut.`)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Bilinmeyen hata'
      window.alert(`Fotoğraf işlenemedi: ${msg}`)
    } finally {
      setPhotoProcessing(false)
    }
  }

  function onPhotoActionClick() {
    if (photoProcessing) return
    setPhotoModalOpen(true)
  }

  return (
    <>
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
                aria-label="Senkron durumunu göster"
                aria-expanded={healthOpen}
                aria-haspopup="dialog"
              >
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
          <HeaderGlobalAction
            aria-label={photoProcessing ? 'Fotoğraf işleniyor' : 'Ödev fotoğrafı ekle'}
            onClick={onPhotoActionClick}
          >
            {photoProcessing ? (
              <Renew size={20} className="dashboard-header__spin" />
            ) : (
              <Camera size={20} />
            )}
          </HeaderGlobalAction>
          <HeaderGlobalAction aria-label="Çıkış" onClick={onLogout}>
            <Logout size={20} />
          </HeaderGlobalAction>
          <input
            ref={photoCaptureInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: 'none' }}
            onChange={handlePhotoSelected}
          />
          <input
            ref={photoUploadInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={handlePhotoSelected}
          />
        </HeaderGlobalBar>
      </Header>

      {/* Mounted only while open. A closed ComposedModal keeps its
          ModalHeader in the DOM, and those two headings led the heading
          outline of every page in the app. */}
      {photoModalOpen && (
      <ComposedModal
        open
        onClose={resetPhotoFlow}
        size="md"
      >
        <ModalHeader title="Ödev Fotoğrafı Ekle" label="AI Destekli Ödev İşleme" />
        <ModalBody>
          {!selectedPhoto ? (
            <div className="photo-intake-select">
              <p className="photo-intake-select__text">
                Fotoğrafı kamerayla çekebilir veya galeriden mevcut görsel yükleyebilirsiniz.
              </p>
              <div className="photo-intake-select__actions">
                <Button kind="secondary" size="sm" onClick={() => photoCaptureInputRef.current?.click()}>
                  Kamera ile çek
                </Button>
                <Button kind="primary" size="sm" onClick={() => photoUploadInputRef.current?.click()}>
                  Galeriden yükle
                </Button>
              </div>
            </div>
          ) : (
            <div className="photo-intake-form">
              <p className="photo-intake-form__file">
                Seçilen dosya: <strong>{selectedPhoto.name}</strong>
              </p>

              <label className="photo-intake-form__label">
                Kaynak
                <select
                  className="photo-intake-form__input"
                  value={sourceType}
                  onChange={e => setSourceType(e.target.value as 'ted' | 'private')}
                >
                  <option value="ted">TED Connect</option>
                  <option value="private">Özel Ders</option>
                </select>
              </label>

              {sourceType === 'private' && (
                <label className="photo-intake-form__label">
                  Özel Ders
                  <select
                    className="photo-intake-form__input"
                    value={privateLessonId}
                    onChange={e => setPrivateLessonId(e.target.value)}
                  >
                    {privateLessons.length === 0 && <option value="">Tanımlı özel ders yok</option>}
                    {privateLessons.map(lesson => (
                      <option key={lesson.id} value={lesson.id}>
                        {lesson.course} · {lesson.teacher}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <label className="photo-intake-form__label">
                Ders
                <select
                  className="photo-intake-form__input"
                  value={course}
                  onChange={e => setCourse(e.target.value)}
                  disabled={sourceType === 'private'}
                >
                  {courseOptions.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </label>

              <label className="photo-intake-form__label">
                Teslim Tarihi (opsiyonel)
                <input
                  type="datetime-local"
                  className="photo-intake-form__input"
                  value={dueDate}
                  onChange={e => setDueDate(e.target.value)}
                />
              </label>
              <p className="photo-intake-form__hint">
                Boş bırakırsanız teslim tarihi fotoğraftan yapay zekâ ile otomatik çıkarılır.
              </p>
            </div>
          )}
        </ModalBody>
        <ModalFooter>
          {selectedPhoto && (
            <Button
              kind="ghost"
              size="sm"
              onClick={() => setSelectedPhoto(null)}
              disabled={photoProcessing}
            >
              Fotoğrafı değiştir
            </Button>
          )}
          <Button
            kind="secondary"
            size="sm"
            onClick={resetPhotoFlow}
            disabled={photoProcessing}
          >
            İptal
          </Button>
          <Button
            kind="primary"
            size="sm"
            onClick={submitPhotoHomework}
            disabled={!selectedPhoto || photoProcessing}
          >
            {photoProcessing ? 'İşleniyor...' : 'Kaydet ve İşle'}
          </Button>
        </ModalFooter>
      </ComposedModal>
      )}
    </>
  )
}
