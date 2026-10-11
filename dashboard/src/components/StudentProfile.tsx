import { useMemo, useState } from 'react'
import {
  Button, Checkbox, DatePicker, DatePickerInput, InlineLoading, InlineNotification, Layer, Select, SelectItem, Tag,
  TextInput, TimePicker,
} from '@carbon/react'
import { UserAvatar, UserProfile, AddAlt } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { COURSE_CONTENT_ORDER } from '../utils/formatters'
import type { PrivateLesson, StudentProfileData } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import OdakPenceresiAyari from './OdakPenceresiAyari'

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

/** Local calendar date as the API takes it (YYYY-MM-DD); DatePicker hands back Date objects. */
function isoTarih(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
const SAAT = /^([01]\d|2[0-3]):[0-5]\d$/

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
  // B22 (D3, D4): the form answers on the page — a field's own error under it, the result under the form —
  // never in a browser alert and never with the server's raw error text.
  const [alanHatasi, setAlanHatasi] = useState<{ ogretmen?: string; saat?: string; tarih?: string }>({})
  const [sonuc, setSonuc] = useState<{ tur: 'basari' | 'hata'; metin: string } | null>(null)

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
    const hatalar: typeof alanHatasi = {}
    if (!teacher.trim()) hatalar.ogretmen = 'Öğretmen adını yaz.'
    if (!SAAT.test(startTime) || !SAAT.test(endTime)) hatalar.saat = 'Saati SS:DD biçiminde yaz (örneğin 17:00).'
    else if (startTime >= endTime) hatalar.saat = 'Bitiş saati başlangıçtan sonra olmalı.'
    if (!isRecurring && !singleDate) hatalar.tarih = 'Tek seferlik ders için tarihi seç.'
    setAlanHatasi(hatalar)
    setSonuc(null)
    if (Object.keys(hatalar).length) return

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
      if (!res.ok) throw new Error('kaydedilemedi')
      setTeacher('')
      if (!isRecurring) setSingleDate('')
      refreshLessons()
      window.dispatchEvent(new CustomEvent('tedy:homework-updated'))
      setSonuc({ tur: 'basari', metin: 'Özel ders eklendi. Takvimde ve Bugün\'de görünecek.' })
    } catch {
      setSonuc({ tur: 'hata', metin: 'Özel ders eklenemedi. Bağlantını kontrol edip yeniden dene.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="dashboard-card student-profile-card">
        <h2 className="dashboard-card__title">
          <UserProfile size={20} />
          Öğrenci profili
        </h2>
        <div className="student-profile">
          <div className="student-profile__photo-wrap">
            {displayPhoto ? (
              <img className="student-profile__photo" src={displayPhoto} alt={displayName} />
            ) : (
              <div className="student-profile__photo-fallback" aria-hidden>
                <UserAvatar size={32} />
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
        <h2 className="dashboard-card__title" id="ozel-ders-ekle-baslik">
          <AddAlt size={20} />
          Özel ders ekle
        </h2>
        {/* Named by its heading: Profil has two forms now, and two unnamed form
            landmarks cannot be told apart (IBM aria_form_label_unique). */}
        {/* B60 (§5.6): Carbon's own controls in a <Layer> one step above the card (B31), sentence-case labels,
            the date format said as help, today as the earliest date, and on a phone one column. Every field is
            required, so none is marked; an optional one would say "(isteğe bağlı)". */}
        <Layer>
        <form className="private-lesson-form" onSubmit={handleAddLesson} noValidate aria-labelledby="ozel-ders-ekle-baslik">
          <Select id="ozel-ders-ders" labelText="Ders" value={course} onChange={e => setCourse(e.target.value)}>
            {courseOptions.map(opt => <SelectItem key={opt} value={opt} text={opt} />)}
          </Select>

          <TextInput
            id="ozel-ders-ogretmen"
            labelText="Öğretmen adı"
            placeholder="Örn: Ayşe Yılmaz"
            value={teacher}
            onChange={e => setTeacher(e.target.value)}
            invalid={Boolean(alanHatasi.ogretmen)}
            invalidText={alanHatasi.ogretmen}
          />

          <Checkbox
            id="ozel-ders-tekrar"
            labelText="Ders her hafta tekrar ediyor"
            checked={isRecurring}
            onChange={(_, { checked }) => setIsRecurring(checked)}
          />

          {isRecurring ? (
            <Select id="ozel-ders-gun" labelText="Haftanın günü" value={weekday} onChange={e => setWeekday(e.target.value)}>
              {DAYS.map(d => <SelectItem key={d} value={d} text={d} />)}
            </Select>
          ) : (
            <DatePicker
              datePickerType="single"
              dateFormat="d.m.Y"
              locale="tr"
              minDate={new Date(new Date().setHours(0, 0, 0, 0))}
              onChange={(tarihler: Date[]) => setSingleDate(tarihler[0] ? isoTarih(tarihler[0]) : '')}
            >
              <DatePickerInput
                id="ozel-ders-tarih"
                labelText="Tarih"
                placeholder="gg.aa.yyyy"
                helperText="Bugünden sonraki bir gün, gg.aa.yyyy biçiminde."
                invalid={Boolean(alanHatasi.tarih)}
                invalidText={alanHatasi.tarih}
              />
            </DatePicker>
          )}

          <div className="private-lesson-form__time-row">
            <TimePicker
              id="ozel-ders-baslangic"
              labelText="Başlangıç"
              placeholder="ss:dd"
              maxLength={5}
              value={startTime}
              onChange={e => setStartTime(e.target.value)}
              invalid={Boolean(alanHatasi.saat)}
              invalidText={alanHatasi.saat}
            />
            <TimePicker
              id="ozel-ders-bitis"
              labelText="Bitiş"
              placeholder="ss:dd"
              maxLength={5}
              value={endTime}
              onChange={e => setEndTime(e.target.value)}
              invalid={Boolean(alanHatasi.saat)}
            />
          </div>

          {saving
            ? <InlineLoading description="Ekleniyor…" iconDescription="Ekleniyor" status="active" />
            : <Button kind="tertiary" size="md" type="submit">Özel ders ekle</Button>}
          {sonuc && (
            <InlineNotification className="private-lesson-form__sonuc" lowContrast hideCloseButton
              kind={sonuc.tur === 'basari' ? 'success' : 'error'} role={sonuc.tur === 'basari' ? 'status' : 'alert'}
              statusIconDescription={sonuc.tur === 'basari' ? 'Başarılı' : 'Hata'} title={sonuc.metin} />
          )}
        </form>
        </Layer>
      </div>

      <OdakPenceresiAyari />

      <div className="dashboard-card">
        <h2 className="dashboard-card__title">Tanımlı özel dersler</h2>
        {(lessonData.lessons || []).length === 0 ? (
          <EmptyLine>Tanımlı özel ders yok.</EmptyLine>
        ) : (
          <div className="stack-sm">
            {lessonData.lessons.map(lesson => (
              <div key={lesson.id} className="dashboard-list-tile cds--tile student-private-lesson-item">
                <div className="student-private-lesson-item__top">
                  <strong>{lesson.course}</strong>
                  <Tag type="warm-gray" size="sm">Özel ders</Tag>
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

