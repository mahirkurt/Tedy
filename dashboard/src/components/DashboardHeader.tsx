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

interface PhotoDraft {
  course: string
  title: string
  due: string
  description: string
  kaynak: string
  dueSkipped: boolean
}

type PhotoGap = { index: number, field: 'course' | 'due' }

function courseMissing(course: string): boolean {
  const name = course.trim()
  return name === '' || name === 'Genel' || name === 'Özel Ders'
}

function dueLooksReal(value: string): boolean {
  const text = value.trim()
  return /^\d{1,2}[./-]\d{1,2}[./-]\d{4}(?:\s+\d{1,2}[:.]\d{2})?$/.test(text)
    || /^\d{4}[./-]\d{1,2}[./-]\d{1,2}(?:\s+\d{1,2}[:.]\d{2})?$/.test(text)
}

function firstPhotoGap(drafts: PhotoDraft[]): PhotoGap | null {
  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index]
    if (courseMissing(draft.course)) return { index, field: 'course' }
    if (!draft.due.trim() && !draft.dueSkipped) return { index, field: 'due' }
  }
  return null
}

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
  const [photoError, setPhotoError] = useState('')
  const [photoHash, setPhotoHash] = useState('')
  const [photoDrafts, setPhotoDrafts] = useState<PhotoDraft[] | null>(null)
  const [sourceType, setSourceType] = useState<'ted' | 'private'>('ted')
  const [privateLessonId, setPrivateLessonId] = useState('')
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
    if (sourceType !== 'private') return
    if (!privateLessonId && privateLessons.length > 0) {
      setPrivateLessonId(privateLessons[0].id)
    }
  }, [sourceType, privateLessonId, privateLessons])

  function resetPhotoFlow() {
    setSelectedPhoto(null)
    setSourceType('ted')
    setPrivateLessonId('')
    setPhotoError('')
    setPhotoHash('')
    setPhotoDrafts(null)
    setPhotoModalOpen(false)
  }

  function photoFormBase() {
    const formData = new FormData()
    formData.append('source_type', sourceType)
    if (privateLessonId) formData.append('private_lesson_id', privateLessonId)
    return formData
  }

  function handlePhotoSelected(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setPhotoError('Lütfen bir görsel dosyası seçin.')
      return
    }
    setPhotoError('')
    setPhotoHash('')
    setPhotoDrafts(null)
    setSelectedPhoto(file)
  }

  async function readPhotoHomework() {
    if (!selectedPhoto || photoProcessing) return
    if (sourceType === 'private' && !privateLessonId) {
      setPhotoError('Özel ders seçilmeden fotoğraf okunmaz.')
      return
    }
    setPhotoProcessing(true)
    setPhotoError('')
    try {
      const formData = photoFormBase()
      formData.append('stage', 'preview')
      formData.append('photo', selectedPhoto)
      const res = await fetch('/api/homework/photo', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      })
      const payload = await res.json().catch(() => null)
      if (!res.ok) {
        throw new Error(payload?.error || `HTTP ${res.status}`)
      }
      const rows = Array.isArray(payload?.homework) ? payload.homework : []
      if (rows.length === 0) {
        setPhotoError('Bu fotoğrafta ödev görünmüyor.')
        setPhotoDrafts(null)
        return
      }
      setPhotoHash(String(payload?.photo_hash || ''))
      setPhotoDrafts(rows.map((row: Record<string, unknown>) => ({
        course: String(row['Ders Adı'] || ''),
        title: String(row['Ödev Başlığı'] || ''),
        due: String(row['Ödev Son Teslim Tarihi'] || ''),
        description: String(
          (row.detail && typeof row.detail === 'object'
            ? (row.detail as { description?: string }).description
            : '') || '',
        ),
        kaynak: String(row.odev_kaynagi || ''),
        dueSkipped: false,
      })))
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : 'Fotoğraf okunamadı.')
    } finally {
      setPhotoProcessing(false)
    }
  }

  function updateDraft(index: number, patch: Partial<PhotoDraft>) {
    setPhotoDrafts(prev => prev?.map((row, i) => (i === index ? { ...row, ...patch } : row)) ?? prev)
  }

  const photoGap = photoDrafts ? firstPhotoGap(photoDrafts) : null
  const gapKey = photoGap ? `${photoGap.index}:${photoGap.field}` : ''
  const [gapAnswer, setGapAnswer] = useState('')
  const [seenGap, setSeenGap] = useState(gapKey)
  if (seenGap !== gapKey) {
    setSeenGap(gapKey)
    setGapAnswer('')
  }

  function answerPhotoGap(value: string) {
    if (!photoGap) return
    if (photoGap.field === 'course') {
      if (courseMissing(value)) {
        setPhotoError('Ders seçilmeden devam edilmez.')
        return
      }
      updateDraft(photoGap.index, { course: value })
      setPhotoError('')
      return
    }
    const due = value.trim()
    if (!dueLooksReal(due)) {
      setPhotoError('Teslim tarihi gün.ay.yıl olarak yazılmalı.')
      return
    }
    updateDraft(photoGap.index, { due, dueSkipped: false })
    setPhotoError('')
  }

  function skipPhotoDue() {
    if (!photoGap || photoGap.field !== 'due') return
    updateDraft(photoGap.index, { due: '', dueSkipped: true })
    setPhotoError('')
  }

  async function commitPhotoHomework() {
    if (!photoDrafts || photoProcessing) return
    const named = photoDrafts.filter(row => row.title.trim() && row.title.trim() !== 'Başlıksız Ödev')
    if (named.length === 0) {
      setPhotoError('Eklenecek işin bir başlığı olmalı.')
      return
    }
    setPhotoProcessing(true)
    setPhotoError('')
    try {
      const formData = photoFormBase()
      formData.append('stage', 'commit')
      formData.append('photo_hash', photoHash)
      formData.append('homework', JSON.stringify(named.map(row => ({
        'Ders Adı': row.course,
        'Ödev Başlığı': row.title.trim(),
        'Ödev Son Teslim Tarihi': row.due.trim(),
        odev_kaynagi: row.kaynak,
        eksik_birakilan: row.dueSkipped && !row.due.trim() ? ['teslim'] : [],
        detail: { description: row.description.trim() },
      }))))
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
      if (addedCount === 0) {
        setPhotoError(
          skippedCount > 0
            ? 'Bu iş zaten listede. Yeni bir şey eklenmedi.'
            : 'Eklenecek yeni bir iş yok.',
        )
        return
      }
      resetPhotoFlow()
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : 'Ödev eklenemedi.')
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
        <ModalHeader
          title={
            photoGap?.field === 'course' ? 'Bu iş hangi ders?'
              : photoGap?.field === 'due' ? 'Ne zaman teslim?'
                : photoDrafts ? 'Okunan işler' : 'Ödev fotoğrafı'
          }
          label={photoGap ? 'Fotoğrafta bu yok' : photoDrafts ? 'Eklemeden önce kontrol et' : 'Fotoğraftan okuma'}
        />
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
              {photoError && <p className="photo-intake-form__error" role="alert">{photoError}</p>}
            </div>
          ) : (
            <div className="photo-intake-form">
              <p className="photo-intake-form__file">
                Seçilen dosya: <strong>{selectedPhoto.name}</strong>
              </p>

              {!photoDrafts && (
                <>
                  <label className="photo-intake-form__label">
                    Kaynak
                    <select
                      className="photo-intake-form__input"
                      value={sourceType}
                      onChange={e => setSourceType(e.target.value as 'ted' | 'private')}
                    >
                      <option value="ted">Okul ödevi</option>
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
                  <p className="photo-intake-form__hint">
                    Önce fotoğraf okunur. Ders ve teslim tarihi sayfada yazıyorsa oradan gelir; yazmıyorsa boş kalır.
                  </p>
                </>
              )}

              {photoGap && photoDrafts && (
                <div className="photo-intake-draft">
                  <p className="photo-intake-draft__legend">
                    {photoDrafts[photoGap.index].title || 'Bu iş'}
                  </p>
                  {photoGap.field === 'course' ? (
                    <label className="photo-intake-form__label">
                      Hangi ders?
                      <select
                        className="photo-intake-form__input"
                        value={gapAnswer}
                        onChange={e => setGapAnswer(e.target.value)}
                      >
                        <option value="">Ders seç</option>
                        {courseOptions
                          .filter(course => course !== 'Genel' && course !== 'Özel Ders')
                          .map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    </label>
                  ) : (
                    <label className="photo-intake-form__label">
                      Teslim tarihi
                      <input
                        className="photo-intake-form__input"
                        value={gapAnswer}
                        placeholder="02.10.2026"
                        onChange={e => setGapAnswer(e.target.value)}
                      />
                    </label>
                  )}
                </div>
              )}

              {!photoGap && photoDrafts?.map((draft, index) => (
                <fieldset key={index} className="photo-intake-draft">
                  <legend className="photo-intake-draft__legend">İş {index + 1}</legend>
                  {draft.kaynak && (
                    <p className="photo-intake-form__hint">Kaynak: {draft.kaynak}</p>
                  )}
                  <label className="photo-intake-form__label">
                    Ders
                    <select
                      className="photo-intake-form__input"
                      value={draft.course}
                      onChange={e => updateDraft(index, { course: e.target.value })}
                    >
                      {draft.course && !courseOptions.includes(draft.course) && (
                        <option value={draft.course}>{draft.course}</option>
                      )}
                      {courseOptions.map(opt => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  </label>
                  <label className="photo-intake-form__label">
                    Başlık
                    <input
                      className="photo-intake-form__input"
                      value={draft.title}
                      onChange={e => updateDraft(index, { title: e.target.value })}
                    />
                  </label>
                  <label className="photo-intake-form__label">
                    Teslim
                    <input
                      className="photo-intake-form__input"
                      value={draft.due}
                      placeholder="Fotoğrafta yoksa boş bırak"
                      onChange={e => updateDraft(index, { due: e.target.value })}
                    />
                  </label>
                  <label className="photo-intake-form__label">
                    Yönerge
                    <textarea
                      className="photo-intake-form__input"
                      rows={3}
                      value={draft.description}
                      onChange={e => updateDraft(index, { description: e.target.value })}
                    />
                  </label>
                </fieldset>
              ))}

              {photoError && <p className="photo-intake-form__error" role="alert">{photoError}</p>}
            </div>
          )}
        </ModalBody>
        <ModalFooter>
          {selectedPhoto && (
            <Button
              kind="ghost"
              size="sm"
              onClick={() => {
                setSelectedPhoto(null)
                setPhotoDrafts(null)
                setPhotoError('')
              }}
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
          {photoGap ? (
            <>
              {photoGap.field === 'due' && (
                <Button kind="ghost" size="sm" onClick={skipPhotoDue}>
                  Bilmiyorum
                </Button>
              )}
              <Button kind="primary" size="sm" onClick={() => answerPhotoGap(gapAnswer)}>
                Devam
              </Button>
            </>
          ) : photoDrafts ? (
            <Button
              kind="primary"
              size="sm"
              onClick={commitPhotoHomework}
              disabled={photoProcessing}
            >
              {photoProcessing ? 'Ekleniyor...' : 'İşler\'e ekle'}
            </Button>
          ) : (
            <Button
              kind="primary"
              size="sm"
              onClick={readPhotoHomework}
              disabled={!selectedPhoto || photoProcessing}
            >
              {photoProcessing ? 'Okunuyor...' : 'Fotoğrafı oku'}
            </Button>
          )}
        </ModalFooter>
      </ComposedModal>
      )}
    </>
  )
}
