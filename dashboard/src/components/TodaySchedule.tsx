import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tag } from '@carbon/react'
import {
  Education,
  Bookmark,
  Task as TaskIcon,
  EventSchedule,
  Checkmark,
  ChevronLeft,
  ChevronRight,
  UserAvatar,
} from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import {
  parseDeadline, cleanTeacherNames, normalizeCourseDisplayName, htmlToText, kisaTeslim,
} from '../utils/formatters'
import { getCountdown } from '../utils/countdown'
import { dayColumns } from '../utils/schedule'
import { DayStrip } from './DayStrip'
import { NextThing } from './NextThing'
import { useBookProgress } from '../hooks/useBookReader'
import { useZamanKutusu } from '../hooks/useZamanKutusu'
import { yaptimIsaretle } from '../utils/odevYaptim'
import type { BookSummary } from '../types'
import type { HomeworkItem, CalendarEvent, OgepSession, ExamsApiResponse } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import SubjectLabel from './SubjectLabel'
import { subjectClass } from '../utils/subject'

interface ScheduleData {
  latest: { schedule?: { rows: string[][] } }
  today: string
}

interface AgendaItem {
  time: string
  startMin: number
  endMin: number
  name: string
  subtitle: string
  type: 'lesson' | 'ogep' | 'deadline' | 'private_lesson' | 'event'
  /** The course, when the item has one: its mark colours the dot. */
  course?: string
  isActive: boolean
  isPast: boolean
  period?: number
}

type IconComponent = typeof Education

type ActiveHomeworkItem = {
  hw: HomeworkItem
  deadline: Date | null
  countdown: ReturnType<typeof getCountdown>
}

// The kind of an item is its icon and its label, not a colour: teal, purple
// and blue are courses now (Tedy ders renk sistemi) and red is urgency. The
// dot takes the course's mark; an item without a course is the neutral grey.
// Red stays on "Teslim" alone — a deadline on today's line is urgent.
const TYPE_CONFIG: Record<AgendaItem['type'], {
  tagType: 'gray' | 'red'
  label: string
  icon: IconComponent
}> = {
  lesson:         { tagType: 'gray', label: '',          icon: Education },
  ogep:           { tagType: 'gray', label: 'ÖGEP',      icon: Bookmark },
  deadline:       { tagType: 'red',  label: 'Teslim',    icon: TaskIcon },
  private_lesson: { tagType: 'gray', label: 'Özel Ders', icon: UserAvatar },
  event:          { tagType: 'gray', label: 'Etkinlik',  icon: EventSchedule },
}

const DAYS_TR = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi']
const MONTHS_TR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                   'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

const SCHOOL_START = 8 * 60
const SCHOOL_END = 15 * 60 + 45
// Işık's sustained-attention window closes before homework hours begin, so the
// stretch between the last bell and the window's edge is the most valuable time
// in the day and the interface spends it on one demanding thing. See §2 of
// docs/frontend-design-principles.md — this is a parameter, not a fact of life.
const FOCUS_END = 16 * 60
const BEDTIME = 22 * 60 + 30

function toMinutes(h: number, m: number) { return h * 60 + m }

/**
 * The focus window is 08:00–16:00. "ŞİMDİ" only belongs inside it.
 * Before the first bell and after bedtime the work is still named, but
 * the voice stops pretending the next ten minutes are the slot (İ4).
 */
function windowVoice(minutes: number, kind: 'work' | 'reading'): {
  eyebrow: string
  hint?: string
  anchorMin?: number
} {
  const afterBedtime = minutes >= BEDTIME
  const afterWindow = minutes >= FOCUS_END
  const beforeSchool = minutes < SCHOOL_START
  const beforeLastBell = !beforeSchool && minutes < SCHOOL_END

  if (kind === 'work') {
    if (afterBedtime) {
      return { eyebrow: 'YARIN', hint: 'Bunu yarın okuldan sonra yapmak daha kolay' }
    }
    if (afterWindow) {
      return { eyebrow: 'BU AKŞAM' }
    }
    if (beforeSchool || beforeLastBell) {
      return {
        eyebrow: 'OKULDAN SONRA',
        hint: 'Bunu okuldan sonra yapmak daha kolay',
        anchorMin: SCHOOL_END,
      }
    }
    return { eyebrow: 'ŞİMDİ' }
  }

  if (afterBedtime) {
    return { eyebrow: 'YARIN', hint: 'Yarın okuldan sonra daha kolay' }
  }
  if (afterWindow) {
    return { eyebrow: 'BU AKŞAM' }
  }
  if (beforeSchool) {
    return { eyebrow: 'BUGÜN', hint: 'Bunu okuldan sonra yapmak daha kolay' }
  }
  // During lessons the card is a preview under the lesson; "ŞİMDİ" there
  // would contradict the lesson card above it.
  if (beforeLastBell) {
    return { eyebrow: 'OKULDAN SONRA' }
  }
  return { eyebrow: 'ŞİMDİ' }
}

/** An event's second line: its description as text, unless that only says
 *  the title again, in which case the location, or nothing. */
function altBaslik(baslik: string, aciklama?: string, yer?: string): string {
  const esit = (a: string, b: string) =>
    a.replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr') === b.replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr')
  const metin = htmlToText(aciklama)
  if (metin && !esit(metin, baslik || '')) return metin
  return htmlToText(yer)
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate()
}

function compareCalendarDay(target: Date, reference: Date): -1 | 0 | 1 {
  const t = new Date(target.getFullYear(), target.getMonth(), target.getDate()).getTime()
  const r = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate()).getTime()
  if (t === r) return 0
  return t < r ? -1 : 1
}

function parseTurkishDate(s?: string | null): Date | null {
  if (!s) return null
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!m) return null
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5])
}

function buildAgenda(
  scheduleData: ScheduleData,
  teamsData: { ogep: OgepSession[] },
  hwData: { homework: HomeworkItem[] },
  calData: { events: CalendarEvent[] },
  targetDate: Date,
  nowMs: number,
): AgendaItem[] {
  const items: AgendaItem[] = []
  const now = new Date(nowMs)
  const nowMin = toMinutes(now.getHours(), now.getMinutes())
  const selectedDayName = DAYS_TR[targetDate.getDay()]
  const dayRelation = compareCalendarDay(targetDate, now)

  const getTemporalState = (startMin: number, endMin: number) => {
    if (dayRelation < 0) return { isActive: false, isPast: true }
    if (dayRelation > 0) return { isActive: false, isPast: false }
    return {
      isActive: nowMin >= startMin && nowMin < endMin,
      isPast: nowMin >= endMin,
    }
  }

  const rows = scheduleData.latest?.schedule?.rows || []
  // The portal writes the days in caps ("ÇARŞAMBA") and this matched them with
  // `indexOf('Çarşamba')`, so no day ever matched and the day's agenda showed
  // no lessons at all — measured 2026-09-23: every one of the seven days
  // returned -1. The time column has to come from the day's own block too,
  // because Friday runs on a later bell than Monday through Thursday.
  const gun = dayColumns(rows[0] || [], [selectedDayName])[0]
  if (gun) {
    for (let r = 1; r < rows.length; r++) {
      const timeCell = rows[r][gun.timeIdx] || ''
      const content = rows[r][gun.idx] || ''
      if (!content) continue
      if (['Kahvaltı', 'Öğle yemeği', 'İkindi Kahvaltısı', 'Çıkış'].includes(content)) continue
      const periodMatch = timeCell.match(/(\d+)\. Ders/)
      const timeMatch = timeCell.match(/(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})/)
      if (!periodMatch || !timeMatch) continue
      const lines = content.split('\n')
      const startMin = toMinutes(+timeMatch[1], +timeMatch[2])
      const endMin = toMinutes(+timeMatch[3], +timeMatch[4])
      const teacherRaw = lines.slice(1).join('\n')
      const timeState = getTemporalState(startMin, endMin)
      items.push({
        time: `${timeMatch[1]}:${timeMatch[2]}\u2013${timeMatch[3]}:${timeMatch[4]}`,
        startMin, endMin,
        // The API has already normalised the name ("Kültür ve Medeniyetimize
        // Yön Verenler"); title-casing it again capitalised the "ve". Same
        // function Dersler uses, so a lesson has one name everywhere (İ9).
        name: normalizeCourseDisplayName(lines[0]?.trim() || ''),
        subtitle: cleanTeacherNames(teacherRaw),
        type: 'lesson',
        course: normalizeCourseDisplayName(lines[0]?.trim() || ''),
        isActive: timeState.isActive,
        isPast: timeState.isPast,
        period: +periodMatch[1],
      })
    }
  }

  for (const s of teamsData.ogep || []) {
    const d = parseTurkishDate(s["Çalışma Başlangıç"])
    if (!d || !isSameDay(d, targetDate)) continue
    const end = parseTurkishDate(s["Çalışma Bitiş"])
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ehh = end ? String(end.getHours()).padStart(2, '0') : hh
    const emm = end ? String(end.getMinutes()).padStart(2, '0') : mm
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const endMin = end ? toMinutes(end.getHours(), end.getMinutes()) : startMin + 40
    const timeState = getTemporalState(startMin, endMin)
    items.push({
      time: `${hh}:${mm}\u2013${ehh}:${emm}`,
      startMin, endMin,
      name: s["ÖGEP (Öğrenci Gelişim Programı)"],
      subtitle: s["Katılım Durumu"] || 'Bekliyor',
      type: 'ogep',
      isActive: timeState.isActive,
      isPast: timeState.isPast,
    })
  }

  for (const hw of hwData.homework || []) {
    const d = parseDeadline(hw["Ödev Son Teslim Tarihi"])
    if (!d || !isSameDay(d, targetDate)) continue
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const timeState = getTemporalState(startMin, startMin)
    items.push({
      time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
      startMin, endMin: startMin,
      name: hw["Ödev Başlığı"],
      subtitle: hw.normalized_course || hw["Ders Adı"],
      type: 'deadline',
      course: hw.normalized_course || hw["Ders Adı"],
      isActive: false,
      isPast: dayRelation === 0 ? nowMin > startMin : timeState.isPast,
    })
  }

  for (const ev of calData.events || []) {
    if (ev.allDay) continue
    const d = new Date(ev.start)
    if (!isSameDay(d, targetDate)) continue
    const end = new Date(ev.end)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ehh = String(end.getHours()).padStart(2, '0')
    const emm = String(end.getMinutes()).padStart(2, '0')
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const endMin = toMinutes(end.getHours(), end.getMinutes())
    const timeState = getTemporalState(startMin, endMin)
    const eventType: AgendaItem['type'] = ev.extendedProps?.kind === 'private_lesson'
      ? 'private_lesson'
      : 'event'
    items.push({
      time: `${hh}:${mm}\u2013${ehh}:${emm}`,
      startMin, endMin,
      name: ev.title,
      // The portal sends the description as HTML, and it usually repeats the
      // title; printed as-is it read "<p>…</p>" under the event (D4).
      subtitle: altBaslik(ev.title, ev.extendedProps?.description, ev.extendedProps?.location),
      type: eventType,
      isActive: timeState.isActive,
      isPast: timeState.isPast,
    })
  }

  return items.sort((a, b) => a.startMin - b.startMin)
}

export default function TodaySchedule() {
  const navigate = useNavigate()
  const { data: scheduleData, loading } = useApi<ScheduleData>(
    '/api/schedule', { latest: {}, today: '' }
  )
  const { data: teamsData } = useApi<{ ogep: OgepSession[] }>(
    '/api/teams', { ogep: [] }
  )
  const { data: hwData } = useApi<{ homework: HomeworkItem[] }>(
    '/api/homework', { homework: [] }
  )
  const { data: calData } = useApi<{ events: CalendarEvent[] }>(
    '/api/calendar', { events: [] }
  )
  const { data: examData } = useApi<ExamsApiResponse>(
    '/api/exams', { exams: [], stats: { upcoming: 0, past: 0, averageGrade: null } }
  )
  const [dayOffset, setDayOffset] = useState(0)
  const [gecmisAcik, setGecmisAcik] = useState(false)
  const [kayitDurumu, setKayitDurumu] = useState<'bos' | 'kaydediliyor' | 'hata'>('bos')
  const [sonYapilan, setSonYapilan] = useState('')

  const selectedDate = useMemo(() => {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    d.setDate(d.getDate() + dayOffset)
    return d
  }, [dayOffset])

  // Reference time for every countdown on this page, refreshed each minute.
  const [nowMs, setNowMs] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 60_000)
    return () => clearInterval(t)
  }, [])

  const agenda = useMemo(
    () => buildAgenda(scheduleData, teamsData, hwData, calData, selectedDate, nowMs),
    [scheduleData, teamsData, hwData, calData, selectedDate, nowMs]
  )

  const activeHomework = useMemo<ActiveHomeworkItem[]>(() => {
    // Recompute countdown labels whenever the minute ticker advances.
    const urgencyOrder: Record<ReturnType<typeof getCountdown>['urgency'], number> = {
      critical: 0,
      urgent: 1,
      soon: 2,
      normal: 3,
      expired: 4,
    }

    return (hwData.homework || [])
      .map(hw => {
        const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
        return {
          hw,
          deadline,
          countdown: getCountdown(deadline, nowMs),
        }
      })
      // "Yaptım" takes work off this list exactly as it does on İşler. Bugün
      // used to check the teacher's status only, so work Işık had already
      // marked done kept coming back as the next thing.
      .filter(({ hw, countdown }) =>
        hw["Ödev Durumu"] === 'Değerlendirilmemiş'
        && !hw.student_marked_done
        && countdown.urgency !== 'expired'
      )
      .sort((a, b) => {
        const urgencyDiff = urgencyOrder[a.countdown.urgency] - urgencyOrder[b.countdown.urgency]
        if (urgencyDiff !== 0) return urgencyDiff
        const aTime = a.deadline?.getTime() ?? Number.MAX_SAFE_INTEGER
        const bTime = b.deadline?.getTime() ?? Number.MAX_SAFE_INTEGER
        return aTime - bTime
      })
  }, [hwData, nowMs])

  const { data: booksData } = useApi<{ books: BookSummary[] }>(
    '/api/books', { books: [] })
  const firstBook = booksData.books[0]
  const bookProgress = useBookProgress(firstBook?.slug)



  // The card names the most urgent work; the list under it is the rest, so the
  // same item is never said twice (İ1). It used to be the top three, which put
  // the card's own homework straight back underneath it.
  const top = activeHomework[0]
  const digerOdevler = activeHomework.slice(1)
  const ayricaGoster = digerOdevler.slice(0, 2)
  const ayricaFazla = digerOdevler.length - ayricaGoster.length

  const now = new Date(nowMs)
  const nowMin = toMinutes(now.getHours(), now.getMinutes())

  // The ten minutes behind "10 dakikayla başla", kept on this card and across
  // a reload. Keyed by the work, so a different top item finds no box.
  const isAnahtari = top
    ? top.hw.homework_key
      || [top.hw['Ders Adı'], top.hw['Ödev Başlığı'], top.hw['Ödev Son Teslim Tarihi']].join('|')
    : ''
  const kutu = useZamanKutusu(isAnahtari, 10, nowMs)
  const baslat = kutu.baslat

  // Exactly one named next step (İ1), offered as a box to start inside rather
  // than an estimate we do not have (İ3).
  const nextThing = useMemo(() => {
    // Derived from nowMs inside the memo rather than taken as a dependency:
    // the compiler cannot prove a value computed in the render body stays put.
    const d = new Date(nowMs)
    const minutes = toMinutes(d.getHours(), d.getMinutes())
    if (top) {
      // The normalised name, as "Ayrıca" and İşler print it: the raw portal
      // name put "İkinci Yabancı Dil (Fransızca)" on the card and "Fransızca"
      // one line below it (İ9).
      const course = String(top.hw.normalized_course || top.hw['Ders Adı'] || '').trim()
      const title = String(top.hw['Ödev Başlığı'] || '').trim()
      const voice = windowVoice(minutes, 'work')
      return {
        anchorMin: voice.anchorMin,
        props: {
          eyebrow: voice.eyebrow,
          title: [course, title].filter(Boolean).join(' — ') || 'Ödev',
          course: course || undefined,
          stepMinutes: 10,
          actionLabel: 'Başla',
          // Opens the box here. It used to navigate to İşler, so "Başla"
          // started nothing and the work had to be found again (İ5).
          onAction: baslat,
          variant: 'work' as const,
          hint: voice.hint,
          due: top.deadline ? `Teslim ${kisaTeslim(top.deadline, d)}` : undefined,
        },
      }
    }
    // Nothing is owed, so reading takes the slot. It is not louder than school
    // work any more; it is what remains when there is none.
    const resumeId = bookProgress.lastChapterId
    const target = firstBook
      ? (resumeId ? `/kitaplar/${firstBook.slug}/${resumeId}` : `/kitaplar/${firstBook.slug}`)
      : '/kitaplar'
    const voice = windowVoice(minutes, 'reading')
    return {
      anchorMin: voice.anchorMin,
      props: {
        eyebrow: voice.eyebrow,
        title: firstBook ? `Tedy Books — ${firstBook.title}` : 'Tedy Books',
        stepMinutes: 15,
        stepSuffix: 'oku',
        actionLabel: 'Okumaya başla',
        onAction: () => navigate(target),
        variant: 'reading' as const,
        hint: voice.hint,
        due: undefined,
      },
    }
  }, [top, nowMs, firstBook, bookProgress.lastChapterId, navigate, baslat])

  // "Yaptım" from inside the box. On success the homework reloads everywhere
  // (tedy:homework-updated), the card steps to the next work, and a quiet line
  // says what was recorded; on failure the box stays open and the card says so.
  const yaptim = async () => {
    if (!top) return
    const ad = [top.hw.normalized_course || top.hw['Ders Adı'], top.hw['Ödev Başlığı']]
      .filter(Boolean).join(' — ')
    setKayitDurumu('kaydediliyor')
    if (await yaptimIsaretle(top.hw)) {
      kutu.birak()
      setSonYapilan(ad)
      setKayitDurumu('bos')
    } else {
      setKayitDurumu('hata')
    }
  }

  // The next school day, for the evening: where to be, not what is owed —
  // the card and "Ayrıca" already name the work with its day. The timetable
  // repeats week to week (measured 2026-09-20), so next Monday reads from
  // this week's grid.
  const sonrakiGun = useMemo(() => {
    const bugun = new Date(nowMs)
    bugun.setHours(0, 0, 0, 0)
    for (let k = 1; k <= 7; k++) {
      const gun = new Date(bugun)
      gun.setDate(bugun.getDate() + k)
      const ajanda = buildAgenda(scheduleData, teamsData, hwData, calData, gun, nowMs)
      const dersleri = ajanda.filter(a => a.type === 'lesson')
      if (dersleri.length === 0) continue
      return {
        k,
        tarih: gun,
        gunAdi: DAYS_TR[gun.getDay()].toLocaleUpperCase('tr'),
        dersleri,
        etkinlikler: ajanda.filter(a => a.type !== 'lesson' && a.type !== 'deadline'),
      }
    }
    return null
  }, [scheduleData, teamsData, hwData, calData, nowMs])

  // The teacher's own words for the work in the box, one paragraph per line.
  const talimat = (top?.hw.detail?.description || '')
    .split('\n').map(l => l.trim()).filter(Boolean)

  const selectedIsToday = compareCalendarDay(selectedDate, now) === 0
  const dayName = DAYS_TR[selectedDate.getDay()]
  const dateStr = `${selectedDate.getDate()} ${MONTHS_TR[selectedDate.getMonth()]}`

  // Where to be. Deadlines are points in time, not places, so they never
  // take this slot.
  const yerler = agenda.filter(a => a.type !== 'deadline')
  const dersler = agenda.filter(a => a.type === 'lesson')
  const sonZil = dersler.reduce((m, a) => Math.max(m, a.endMin), 0)
  const simdikiYer = yerler.find(a => a.isActive) ?? yerler.find(a => !a.isPast)
  // Until the last bell the lesson is the one thing and the homework waits
  // under it as a preview; after it, the homework is the one thing (İ1).
  // Measured 2026-09-24 at 10:15: the page led with "OKULDAN SONRA: Matematik"
  // while Işık sat in İngilizce, and on a phone the lesson was below the fold.
  const okulModu = selectedIsToday && dersler.length > 0 && nowMin < sonZil && simdikiYer != null
  const kalanDers = dersler.filter(a => !a.isPast && !a.isActive).length
  const sonraki = simdikiYer ? yerler.find(a => a.startMin > simdikiYer.startMin) : undefined
  const ilkMi = simdikiYer != null && !yerler.some(a => a.isPast || a.isActive)

  // Finished items fold to one line on today's page (İ7): at 16:40 they were
  // a green "program bitti" card over 550px of grey ticks. Another day is
  // being looked at on purpose, so it shows whole.
  const gecmis = selectedIsToday ? agenda.filter(a => a.isPast) : []
  const gorunen = selectedIsToday && !gecmisAcik ? agenda.filter(a => !a.isPast) : agenda

  // Once today's last bell has gone — or, on a day without school, from the
  // usual end of the day — the evening turns to tomorrow's bag.
  const yarinGoster = selectedIsToday && !okulModu && sonrakiGun != null
    && nowMin >= (dersler.length > 0 ? sonZil : SCHOOL_END)

  // Upcoming exams, soonest first. One that falls on the next school day leads
  // the evening's "Yarın" and leaves the list, so it is said once; it never
  // takes the card — at 20:00 the page must not say "start revising" (İ4).
  const yaklasanSinavlar = (examData.exams || [])
    .filter(e => e.status === 'upcoming' && e.date)
    .map(e => ({ e, d: new Date(e.date as string) }))
    .filter(x => !isNaN(x.d.getTime()))
    .sort((a, b) => a.d.getTime() - b.d.getTime())
  const yarinSinavlari = yarinGoster && sonrakiGun
    ? yaklasanSinavlar.filter(x => isSameDay(x.d, sonrakiGun.tarih))
    : []
  const listeSinavlari = yaklasanSinavlar.filter(x => !yarinSinavlari.includes(x)).slice(0, 3)
  const saatDk = (d: Date) =>
    `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`

  const activeItem = agenda.find(a => a.isActive)
  const schoolDayActive = selectedIsToday && nowMin >= SCHOOL_START && nowMin <= SCHOOL_END
  const nowInsertIdx = gorunen.findIndex(a => a.startMin > nowMin)
  const showNowMarker = selectedIsToday && !activeItem && schoolDayActive

  const nowTimeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`

  if (loading) {
    return (
      <div className="today-loading">
        <div className="today-loading__bar" />
        <div className="today-loading__bar today-loading__bar--short" />
        <div className="today-loading__bar" />
        <div className="today-loading__bar today-loading__bar--short" />
      </div>
    )
  }

  const isKarti = nextThing.props.variant === 'work'

  return (
    <div className="today">
      {/* ── Date header ── */}
      <div className="today__header">
        <div className="today__header-main">
          <button
            type="button"
            className="today__nav-btn"
            onClick={() => setDayOffset(v => v - 1)}
            aria-label="Önceki gün"
          >
            <ChevronLeft size={16} />
          </button>
          <div className="today__header-text">
            <span className="today__day-name">{dayName}</span>
            <span className="today__date-str">{dateStr}</span>
          </div>
          <button
            type="button"
            className="today__nav-btn"
            onClick={() => setDayOffset(v => v + 1)}
            aria-label="Sonraki gün"
          >
            <ChevronRight size={16} />
          </button>
        </div>
        {/* The bare "3/7" that sat here said nothing a reader could decode;
            the lesson card now says "4 ders kaldı" in words. */}
        {dayOffset !== 0 && (
          <div className="today__header-meta">
            <button
              type="button"
              className="today__today-btn"
              onClick={() => setDayOffset(0)}
            >
              Bugüne dön
            </button>
          </div>
        )}
      </div>

      <DayStrip
        nowMin={nowMin}
        bedtimeMin={BEDTIME}
        focusEndMin={FOCUS_END}
        anchorMin={nextThing.anchorMin}
      />

      {okulModu && simdikiYer && (
        <SimdiKarti
          yer={simdikiYer}
          sonraki={sonraki}
          kalanDers={kalanDers}
          nowMin={nowMin}
          ilk={ilkMi}
        />
      )}

      <NextThing
        {...nextThing.props}
        quiet={okulModu}
        box={isKarti && kutu.durum !== 'bos' ? kutu : undefined}
        instruction={isKarti ? talimat : undefined}
        attachments={isKarti ? top?.hw.detail?.attachments : undefined}
        onMore={kutu.baslat}
        onStop={() => { kutu.birak(); setKayitDurumu('bos') }}
        onDone={isKarti ? yaptim : undefined}
        doneState={kayitDurumu}
      />

      {sonYapilan && (
        <p className="today-done-note" role="status">
          <Checkmark size={16} />
          <span>Yaptın: {sonYapilan}</span>
        </p>
      )}

      {/* The rest of what is owed, said quietly: names and days, no coloured
          countdown chips competing with the card above (İ6). */}
      {ayricaGoster.length > 0 && (
        <section className="today-also" aria-label="Ayrıca">
          <div className="today-also__head">
            <span className="today-also__title">AYRICA</span>
            {ayricaFazla > 0 && (
              <button
                type="button"
                className="today-also__all"
                onClick={() => navigate('/isler')}
              >
                +{ayricaFazla} iş daha
              </button>
            )}
          </div>
          {ayricaGoster.map(({ hw, deadline }) => (
            <button
              key={`${hw['Ders Adı']}|${hw['Ödev Başlığı']}|${hw['Ödev Son Teslim Tarihi']}`}
              type="button"
              className="today-also__item"
              onClick={() => navigate('/isler')}
            >
              <span className="today-also__name">
                <SubjectLabel course={hw.normalized_course || hw['Ders Adı']}>
                  {[hw.normalized_course || hw['Ders Adı'], hw['Ödev Başlığı']].filter(Boolean).join(' — ')}
                </SubjectLabel>
              </span>
              {deadline && <span className="today-also__due">{kisaTeslim(deadline, now)}</span>}
            </button>
          ))}
        </section>
      )}

      {/* Exams in the same quiet voice as "Ayrıca": what and when, as a day.
          This block had never rendered — every takvim exam came back "past"
          from the API — and was built with countdown chips and per-course
          colour fills, which spend the attention budget and colour a taxonomy
          rather than a state (İ6, İ8). What stays is the subject's 10 px mark,
          the system's quiet form (the name stays neutral text), as on İşler.
          They follow "Ayrıca": exams weeks away sat above homework due in four
          days. */}
      {listeSinavlari.length > 0 && (
        <section className="today-exams" aria-label="Sınavlar">
          <div className="today-also__head">
            <span className="today-also__title">SINAVLAR</span>
          </div>
          {listeSinavlari.map(({ e, d }) => (
            <button
              key={e.id}
              type="button"
              className="today-also__item"
              onClick={() => navigate('/sinavlar')}
            >
              <span className="today-also__name">
                <SubjectLabel course={e.course} family={e.courseFamily}>{e.title || e.rawTitle}</SubjectLabel>
              </span>
              <span className="today-also__due">{kisaTeslim(d, now)}</span>
            </button>
          ))}
        </section>
      )}

      {yarinGoster && sonrakiGun && (
        <section className="today-tomorrow" aria-label="Sıradaki okul günü">
          <span className="today-tomorrow__eyebrow">
            {sonrakiGun.k === 1 ? `YARIN · ${sonrakiGun.gunAdi}` : sonrakiGun.gunAdi}
          </span>
          {yarinSinavlari.map(({ e, d }) => (
            <p key={e.id} className="today-tomorrow__exam">
              SINAV · {saatDk(d)} · <SubjectLabel course={e.course} family={e.courseFamily}>{e.title || e.rawTitle}</SubjectLabel>
            </p>
          ))}
          <p className="today-tomorrow__first">
            İlk ders {sonrakiGun.dersleri[0].time.split('\u2013')[0]} · {sonrakiGun.dersleri[0].name}
          </p>
          <p className="today-tomorrow__line">
            {sonrakiGun.dersleri.length} ders: {[...new Set(sonrakiGun.dersleri.map(d => d.name))].join(' · ')}
          </p>
          {sonrakiGun.etkinlikler.map(e => (
            <p key={`${e.startMin}-${e.name}`} className="today-tomorrow__line">
              {e.time.split('\u2013')[0]} · {e.name}
            </p>
          ))}
        </section>
      )}

      {agenda.length === 0 ? (
        // One line, not a card. The old empty state spent a large decorative
        // sun and ~200px competing with the one thing above it, which is the
        // attention budget spent on the absence of news (İ6, §2.3).
        <EmptyLine>
          {dayName} için planlı ders, ödev teslimi veya etkinlik yok.
        </EmptyLine>
      ) : (
        <>
          {gecmis.length > 0 && (
            <button
              type="button"
              className="today-past-fold"
              aria-expanded={gecmisAcik}
              onClick={() => setGecmisAcik(v => !v)}
            >
              <Checkmark size={16} />
              <span>{bitenOzeti(gecmis)}</span>
              <span className="today-past-fold__action">{gecmisAcik ? 'Gizle' : 'Göster'}</span>
            </button>
          )}

          {/* ── Timeline ── */}
          <div className="today-tl">
            {gorunen.map((item, i) => {
              const cfg = TYPE_CONFIG[item.type]
              const Icon = cfg.icon

              return (
                <div key={`${item.type}-${item.startMin}-${item.name}`}>
                  {showNowMarker && nowInsertIdx === i && (
                    <NowMarker time={nowTimeStr} />
                  )}
                  <div
                    className={[
                      'today-tl__item',
                      subjectClass(item.course),
                      item.isPast && 'today-tl__item--past',
                      item.isActive && 'today-tl__item--active',
                      item.type === 'deadline' && 'today-tl__item--deadline',
                    ].filter(Boolean).join(' ')}
                    onClick={item.type === 'deadline' ? () => navigate('/isler') : undefined}
                  >
                    <div className="today-tl__time">
                      {item.time.split('\u2013')[0]}
                    </div>
                    <div className="today-tl__spine">
                      <div className="today-tl__dot">
                        {item.isPast
                          ? <Checkmark size={10} />
                          : <Icon size={10} />}
                      </div>
                    </div>
                    <div className="today-tl__card">
                      <div className="today-tl__card-top">
                        <span className="today-tl__card-name">{item.name}</span>
                        {item.period != null && (
                          <span className="today-tl__card-period">{item.period}.</span>
                        )}
                      </div>
                      {item.subtitle && (
                        <div className="today-tl__card-sub">{item.subtitle}</div>
                      )}
                      {(cfg.label || item.isActive) && (
                        <div className="today-tl__card-tags">
                          {item.isActive && <Tag type="gray" size="sm">Devam ediyor</Tag>}
                          {cfg.label && <Tag type={cfg.tagType} size="sm">{cfg.label}</Tag>}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
            {showNowMarker && nowInsertIdx === -1 && (
              <NowMarker time={nowTimeStr} />
            )}
          </div>
        </>
      )}
    </div>
  )
}

/* ── Sub-components ────────────────────────────────────────────────────────── */

/** "7 ders, 1 etkinlik bitti": what the folded line is holding, in words. */
function bitenOzeti(items: AgendaItem[]): string {
  const ders = items.filter(a => a.type === 'lesson').length
  const teslim = items.filter(a => a.type === 'deadline').length
  const diger = items.length - ders - teslim
  const parcalar: string[] = []
  if (ders) parcalar.push(`${ders} ders`)
  if (diger) parcalar.push(`${diger} etkinlik`)
  if (teslim) parcalar.push(`${teslim} teslim`)
  return `${parcalar.join(', ')} bitti`
}

/**
 * The one thing while school runs: where to be now, and what comes after.
 *
 * Same shape as the next-thing card, because it is the same idea. It used to
 * be a saturated gradient with a pulsing dot and its own progress bar — the
 * loudest block on the page, one of three time bars, and still fourth in
 * reading order (İ1, İ6). The day strip is the only bar now.
 */
function SimdiKarti({ yer, sonraki, kalanDers, nowMin, ilk }: {
  yer: AgendaItem
  sonraki?: AgendaItem
  kalanDers: number
  nowMin: number
  ilk: boolean
}) {
  const baslar = yer.time.split('\u2013')[0]
  const kala = yer.startMin - nowMin
  const ust = yer.isActive
    ? `ŞU AN · ${yer.endMin - nowMin} dk kaldı`
    : ilk && yer.type === 'lesson'
      ? `İLK DERS · ${baslar}`
      : `SIRADAKİ · ${kala <= 60 ? `${kala} dk sonra` : baslar}`

  return (
    <section className="today-now" aria-label="Şu anki ders">
      <span className="today-now__eyebrow">{ust}</span>
      <h2 className="today-now__title">{yer.name}</h2>
      {yer.subtitle && <p className="today-now__sub">{yer.subtitle}</p>}
      <p className="today-now__next">
        <span>
          {sonraki
            ? `Sonra: ${sonraki.name} ${sonraki.time.split('\u2013')[0]}`
            : 'Bugünün sonuncusu'}
        </span>
        {kalanDers > 0 && <span>{kalanDers} ders kaldı</span>}
      </p>
    </section>
  )
}

function NowMarker({ time }: { time: string }) {
  return (
    <div className="today-tl__now">
      <span className="today-tl__now-time">{time}</span>
      <span className="today-tl__now-line" />
    </div>
  )
}
