import { useMemo, useState } from 'react'
import { Button, Tag } from '@carbon/react'
import { UserAvatar, UserProfile, AddAlt } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { COURSE_CONTENT_ORDER } from '../utils/formatters'
import type { PrivateLesson, StudentProfileData } from '../types'
import { EmptyLine } from './patterns/EmptyLine'

const DEFAULT_PROFILE: StudentProfileData = {
  name: '',
  student_no: '',
  class_name: '',
  branch: '',
  photo_data_url: '',
  fields: {},
  scraped_at: '',
  auth: {},
}

const DAYS = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']

export default function StudentProfile() {
  const { data: profile } = useApi<StudentProfileData>('/api/student/profile', DEFAULT_PROFILE)
  const { data: lessonData, refresh: refreshLessons } = useApi<{ lessons: PrivateLesson[] }>(
    '/api/private-lessons',
    { lessons: [] }
  )

  const [course, setCourse] = useState('Matematik')
  const [teacher, setTeacher] = useState('')
  const [isRecurring, setIsRecurring] = useState(true)
  const [weekday, setWeekday] = useState('Pazartesi')
  const [singleDate, setSingleDate] = useState('')
  const [startTime, setStartTime] = useState('17:00')
  const [endTime, setEndTime] = useState('18:00')
  const [saving, setSaving] = useState(false)

  const courseOptions = useMemo(() => {
    const dynamicCourses = new Set<string>()
    for (const lesson of lessonData.lessons || []) {
      if (lesson.course) dynamicCourses.add(lesson.course)
    }
    const combined = [
      ...COURSE_CONTENT_ORDER,
      ...Array.from(dynamicCourses).sort((a, b) => a.localeCompare(b, 'tr')),
    ]
    return Array.from(new Set(combined.filter(Boolean)))
  }, [lessonData.lessons])

  const displayName = profile.name || profile.auth?.name || 'Öğrenci'
  const displayPhoto = profile.photo_data_url || profile.auth?.picture || ''

  async function handleAddLesson(e: React.FormEvent) {
    e.preventDefault()
    if (!teacher.trim()) {
      window.alert('Öğretmen adı gerekli.')
      return
    }
    if (!startTime || !endTime) {
      window.alert('Başlangıç ve bitiş saatleri gerekli.')
      return
    }
    if (!isRecurring && !singleDate) {
      window.alert('Tek seferlik ders için tarih seçin.')
      return
    }

    setSaving(true)
    try {
      const res = await fetch('/api/private-lessons', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          course,
          teacher: teacher.trim(),
          is_recurring: isRecurring,
          weekday: isRecurring ? weekday : '',
          date: isRecurring ? '' : singleDate,
          start_time: startTime,
          end_time: endTime,
        }),
      })
      const payload = await res.json().catch(() => null)
      if (!res.ok) throw new Error(payload?.error || `HTTP ${res.status}`)
      setTeacher('')
      if (!isRecurring) setSingleDate('')
      refreshLessons()
      window.dispatchEvent(new CustomEvent('tedy:homework-updated'))
      window.alert('Özel ders eklendi. Takvimde "Özel Ders" badge’iyle görünecek.')
    } catch (err) {
      window.alert(`Özel ders eklenemedi: ${err instanceof Error ? err.message : 'Bilinmeyen hata'}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="dashboard-card student-profile-card">
        <h2 className="dashboard-card__title">
          <UserProfile size={20} />
          Öğrenci Profili
        </h2>
        <div className="student-profile">
          <div className="student-profile__photo-wrap">
            {displayPhoto ? (
              <img className="student-profile__photo" src={displayPhoto} alt={displayName} />
            ) : (
              <div className="student-profile__photo-fallback" aria-hidden>
                <UserAvatar size={36} />
              </div>
            )}
          </div>
          <div className="student-profile__main">
            <h3 className="student-profile__name">{displayName}</h3>
            <div className="student-profile__meta">
              {profile.student_no && <Tag type="cool-gray">No: {profile.student_no}</Tag>}
              {profile.class_name && <Tag type="cool-gray">Sınıf: {profile.class_name}</Tag>}
              {profile.branch && <Tag type="cool-gray">Şube: {profile.branch}</Tag>}
            </div>
            {/* The sync timestamp lived here in English as "TED Connect sync".
                It is operator detail on the one page that is about Işık rather
                than about her work, and the header's health popover already
                carries it. */}
            {Object.entries(profile.fields || {}).length > 0 ? (
              <div className="student-profile__fields">
                {/* Every field, not the first twelve: the old cap dropped the
                    rest without saying so, and a profile that quietly omits
                    part of itself is the shape of defect this dashboard keeps
                    turning up (D3). */}
                {Object.entries(profile.fields).map(([k, v]) => (
                  <div key={k} className="student-profile__field">
                    <span className="student-profile__field-key">{k}</span>
                    <span className="student-profile__field-val">{v}</span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyLine>
                Portaldan öğrenci bilgisi gelmedi.
              </EmptyLine>
            )}
          </div>
        </div>
      </div>

      <div className="dashboard-card">
        <h2 className="dashboard-card__title">
          <AddAlt size={20} />
          Özel Ders Ekle
        </h2>
        <form className="private-lesson-form" onSubmit={handleAddLesson}>
          <label className="private-lesson-form__label">
            Ders
            <select value={course} onChange={e => setCourse(e.target.value)} className="private-lesson-form__input">
              {courseOptions.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </label>

          <label className="private-lesson-form__label">
            Öğretmen Adı
            <input
              value={teacher}
              onChange={e => setTeacher(e.target.value)}
              className="private-lesson-form__input"
              placeholder="Örn: Ayşe Yılmaz"
              required
            />
          </label>

          <label className="private-lesson-form__checkbox">
            <input
              type="checkbox"
              checked={isRecurring}
              onChange={e => setIsRecurring(e.target.checked)}
            />
            <span>Ders tekrar ediyor</span>
          </label>

          {isRecurring ? (
            <label className="private-lesson-form__label">
              Haftanın Günü
              <select value={weekday} onChange={e => setWeekday(e.target.value)} className="private-lesson-form__input">
                {DAYS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </label>
          ) : (
            <label className="private-lesson-form__label">
              Tarih
              <input
                type="date"
                value={singleDate}
                onChange={e => setSingleDate(e.target.value)}
                className="private-lesson-form__input"
                required={!isRecurring}
              />
            </label>
          )}

          <div className="private-lesson-form__time-row">
            <label className="private-lesson-form__label">
              Başlangıç
              <input
                type="time"
                value={startTime}
                onChange={e => setStartTime(e.target.value)}
                className="private-lesson-form__input"
                required
              />
            </label>
            <label className="private-lesson-form__label">
              Bitiş
              <input
                type="time"
                value={endTime}
                onChange={e => setEndTime(e.target.value)}
                className="private-lesson-form__input"
                required
              />
            </label>
          </div>

          <Button kind="tertiary" size="sm" type="submit" disabled={saving}>
            {saving ? 'Ekleniyor...' : 'Özel Ders Ekle'}
          </Button>
        </form>
      </div>

      <div className="dashboard-card">
        <h2 className="dashboard-card__title">Tanımlı Özel Dersler</h2>
        {(lessonData.lessons || []).length === 0 ? (
          <EmptyLine>Tanımlı özel ders yok.</EmptyLine>
        ) : (
          <div className="stack-sm">
            {lessonData.lessons.map(lesson => (
              <div key={lesson.id} className="dashboard-list-tile cds--tile student-private-lesson-item">
                <div className="student-private-lesson-item__top">
                  <strong>{lesson.course}</strong>
                  <Tag type="warm-gray" size="sm">Özel Ders</Tag>
                </div>
                <div className="student-private-lesson-item__meta">
                  Öğretmen: {lesson.teacher}
                </div>
                <div className="student-private-lesson-item__meta">
                  {lesson.is_recurring
                    ? `Her ${lesson.weekday} · ${lesson.start_time}-${lesson.end_time}`
                    : `${lesson.date} · ${lesson.start_time}-${lesson.end_time}`}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

