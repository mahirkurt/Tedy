import { Fragment, useState, useEffect, useMemo, type MouseEvent } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import {
  Button, ContainedList, ContainedListItem, IconButton, InlineNotification,
  SkeletonPlaceholder, SkeletonText, Tag,
} from '@carbon/react'
import { Bookmark, Checkmark, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Education, EventSchedule, InProgress, Task as TaskIcon, UserAvatar } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import {
  parseDeadline, cleanTeacherNames, normalizeCourseDisplayName, htmlToText, kisaTeslim, kisaGun,
} from '../utils/formatters'
import { getCountdown } from '../utils/countdown'
import { dayColumns } from '../utils/schedule'
import {
  SCHOOL_START, DAYS_TR, MONTHS_TR,
  bitenOzeti, compareCalendarDay, isSameDay, okulGunuMu, sonrakiOkulGunu, simdiUstu,
  toMinutes, windowVoice, yarinBasligi, yerMi, yerSec, type AgendaSlot,
} from '../utils/bugun'
import { DayStrip } from './DayStrip'
import { NextThing } from './NextThing'
import { useBookProgress } from '../hooks/useBookReader'
import { useZamanKutusu } from '../hooks/useZamanKutusu'
import { yaptimIsaretle, yaptimGeriAl } from '../utils/odevYaptim'
import { useOdakPenceresi } from '../hooks/useOdakPenceresi'
import { YaptinSatiri, type GeriAlDurumu } from './patterns/YaptinSatiri'
import type { BookSummary } from '../types'
import type { HomeworkItem, CalendarEvent, OgepSession, ExamsApiResponse } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import { Rakamli } from './patterns/Rakamli'
import SubjectLabel from './SubjectLabel'
import { subjectClass } from '../utils/subject'
import { enYakinSinav, sinavAni, yerelAni } from '../utils/sinav'
import { SinavOnizleme } from './SinavKarti'

interface ScheduleData {
  latest: { schedule?: { rows: string[][] } }
  today: string
}

interface AgendaItem extends AgendaSlot {
  time: string
  name: string
  subtitle: string
  /** The course, when the item has one: its mark colours the dot. */
  course?: string
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
// Labels are sentence case (S38).
const TYPE_CONFIG: Record<AgendaItem['type'], {
  tagType: 'gray' | 'red'
  label: string
  icon: IconComponent
}> = {
  lesson:         { tagType: 'gray', label: '',          icon: Education },
  ogep:           { tagType: 'gray', label: 'ÖGEP',      icon: Bookmark },
  deadline:       { tagType: 'red',  label: 'Teslim',    icon: TaskIcon },
  private_lesson: { tagType: 'gray', label: 'Özel ders', icon: UserAvatar },
  event:          { tagType: 'gray', label: 'Etkinlik',  icon: EventSchedule },
}

const ZAMAN_CIZELGESI_ID = 'bugun-zaman-cizelgesi'

/** An event's second line: its description as text, unless that only says
 *  the title again, in which case the location, or nothing. */
function altBaslik(baslik: string, aciklama?: string, yer?: string): string {
  const esit = (a: string, b: string) =>
    a.replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr') === b.replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr')
  const metin = htmlToText(aciklama)
  if (metin && !esit(metin, baslik || '')) return metin
  return htmlToText(yer)
}

function parseTurkishDate(s?: string | null): Date | null {
  if (!s) return null
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!m) return null
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5])
}

const iki = (n: number) => String(n).padStart(2, '0')
const saatDk = (d: Date) => `${iki(d.getHours())}:${iki(d.getMinutes())}`

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
        time: `${timeMatch[1]}:${timeMatch[2]}–${timeMatch[3]}:${timeMatch[4]}`,
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
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const endMin = end ? toMinutes(end.getHours(), end.getMinutes()) : startMin + 40
    const timeState = getTemporalState(startMin, endMin)
    items.push({
      time: `${saatDk(d)}–${saatDk(end ?? d)}`,
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
      time: saatDk(d),
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
    // A date-only start ("2026-09-24") is that local day, not UTC midnight (C20).
    const d = yerelAni(ev.start)
    if (!d || !isSameDay(d, targetDate)) continue
    const end = yerelAni(ev.end) ?? d
    const startMin = toMinutes(d.getHours(), d.getMinutes())
    const endMin = toMinutes(end.getHours(), end.getMinutes())
    const timeState = getTemporalState(startMin, endMin)
    const ozelDers = ev.extendedProps?.kind === 'private_lesson'
    items.push({
      time: `${saatDk(d)}–${saatDk(end)}`,
      startMin, endMin,
      name: ev.title,
      // The portal sends the description as HTML, and it usually repeats the
      // title; printed as-is it read "<p>…</p>" under the event (D4).
      subtitle: altBaslik(ev.title, ev.extendedProps?.description, ev.extendedProps?.location),
      type: ozelDers ? 'private_lesson' : 'event',
      // A private lesson carries its course (/api/calendar sends it); Takvim
      // already coloured it, Bugün drew it grey.
      course: ozelDers ? ev.extendedProps?.course : undefined,
      isActive: timeState.isActive,
      isPast: timeState.isPast,
    })
  }

  return items.sort((a, b) => a.startMin - b.startMin)
}

export default function TodaySchedule() {
  const navigate = useNavigate()
  const { data: scheduleData, loading, iskelet: programIskeleti, error: programHatasi } = useApi<ScheduleData>(
    '/api/schedule', { latest: {}, today: '' }
  )
  const { data: teamsData } = useApi<{ ogep: OgepSession[] }>(
    '/api/teams', { ogep: [] }
  )
  const { data: hwData, error: odevHatasi } = useApi<{ homework: HomeworkItem[] }>(
    '/api/homework', { homework: [] }
  )
  const { data: calData, error: takvimHatasi } = useApi<{ events: CalendarEvent[] }>(
    '/api/calendar', { events: [] }
  )
  const { data: examData, error: sinavHatasi } = useApi<ExamsApiResponse>(
    '/api/exams', { exams: [], stats: { upcoming: 0, past: 0, averageGrade: null } }
  )
  const [dayOffset, setDayOffset] = useState(0)
  const [gecmisAcik, setGecmisAcik] = useState(false)
  const [kayitDurumu, setKayitDurumu] = useState<'bos' | 'kaydediliyor' | 'hata'>('bos')
  // The work "Yaptım" just recorded, kept so "Geri al" can send the same record (B63).
  const [sonYapilan, setSonYapilan] = useState<{ ad: string; hw: HomeworkItem } | null>(null)
  const [geriAlDurumu, setGeriAlDurumu] = useState<GeriAlDurumu>('bos')
  // The household's focus window (B29): today's values until it loads.
  const { pencere, loading: pencereYukleniyor, iskelet: pencereIskeleti } = useOdakPenceresi()

  // Reference time for every countdown on this page, refreshed each minute.
  const [nowMs, setNowMs] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 60_000)
    return () => clearInterval(t)
  }, [])

  const selectedDate = useMemo(() => {
    const d = new Date(nowMs)
    d.setHours(0, 0, 0, 0)
    d.setDate(d.getDate() + dayOffset)
    return d
  }, [dayOffset, nowMs])

  const agenda = useMemo(
    () => buildAgenda(scheduleData, teamsData, hwData, calData, selectedDate, nowMs),
    [scheduleData, teamsData, hwData, calData, selectedDate, nowMs]
  )
  // The card speaks about today whichever day the arrows show.
  const bugunAjandasi = useMemo(() => {
    if (dayOffset === 0) return agenda
    const bugun = new Date(nowMs)
    bugun.setHours(0, 0, 0, 0)
    return buildAgenda(scheduleData, teamsData, hwData, calData, bugun, nowMs)
  }, [agenda, dayOffset, scheduleData, teamsData, hwData, calData, nowMs])

  const activeHomework = useMemo<ActiveHomeworkItem[]>(() => {
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
  // same item is never said twice (İ1).
  const top = activeHomework[0]
  const digerOdevler = activeHomework.slice(1)
  const ayricaGoster = digerOdevler.slice(0, 2)
  const ayricaFazla = digerOdevler.length - ayricaGoster.length

  const now = new Date(nowMs)
  const nowMin = toMinutes(now.getHours(), now.getMinutes())

  // Is there school today? The timetable says so when there is one; the
  // voice of the card depends on it (a Saturday is not "after school").
  const okulGunu = useMemo(() => okulGunuMu(
    bugunAjandasi.filter(a => a.type === 'lesson').length,
    new Date(nowMs),
    (scheduleData.latest?.schedule?.rows?.length ?? 0) > 1,
  ), [bugunAjandasi, nowMs, scheduleData])

  // Today's school for the Day Strip, whatever day the page is showing: the
  // strip is always today. The last bell is the timetable's when there is one
  // (Friday runs later), the household setting otherwise.
  const seritOkulu = useMemo(() => {
    if (!okulGunu) return null
    const dersler = bugunAjandasi.filter(a => a.type === 'lesson')
    const bas = dersler.length ? Math.min(...dersler.map(a => a.startMin)) : SCHOOL_START
    const bit = dersler.length ? Math.max(...dersler.map(a => a.endMin)) : pencere.okulBitisi
    return { bas, bit }
  }, [okulGunu, bugunAjandasi, pencere.okulBitisi])

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
    const d = new Date(nowMs)
    const minutes = toMinutes(d.getHours(), d.getMinutes())
    if (top) {
      // The normalised name, as "Ayrıca" and İşler print it (İ9).
      const course = String(top.hw.normalized_course || top.hw['Ders Adı'] || '').trim()
      const title = String(top.hw['Ödev Başlığı'] || '').trim()
      const voice = windowVoice(minutes, 'work', okulGunu, pencere)
      return {
        anchorMin: voice.anchorMin,
        props: {
          eyebrow: voice.eyebrow,
          title: [course, title].filter(Boolean).join(' — ') || 'Ödev',
          course: course || undefined,
          stepMinutes: 10,
          actionLabel: 'Başla',
          // Opens the box here, so "Başla" starts something (İ5).
          onAction: baslat,
          variant: 'work' as const,
          hint: voice.hint,
          due: top.deadline ? `Teslim ${kisaTeslim(top.deadline, d)}` : undefined,
        },
      }
    }
    // Nothing is owed, so reading takes the slot: what remains when there is
    // no school work, never louder than it.
    const resumeId = bookProgress.lastChapterId
    const target = firstBook
      ? (resumeId ? `/kitaplar/${firstBook.slug}/${resumeId}` : `/kitaplar/${firstBook.slug}`)
      : '/kitaplar'
    const voice = windowVoice(minutes, 'reading', okulGunu, pencere)
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
  }, [top, nowMs, okulGunu, pencere, firstBook, bookProgress.lastChapterId, navigate, baslat])

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
      setSonYapilan({ ad, hw: top.hw })
      setGeriAlDurumu('bos')
      setKayitDurumu('bos')
    } else {
      setKayitDurumu('hata')
    }
  }

  // "Geri al" on the same line (S40, B63): the mark goes, the homework reloads
  // everywhere and comes back as the card's work. A failure keeps the line
  // and says so (D3).
  const geriAl = async () => {
    if (!sonYapilan) return
    setGeriAlDurumu('aliniyor')
    if (await yaptimGeriAl(sonYapilan.hw)) {
      setSonYapilan(null)
      setGeriAlDurumu('bos')
    } else {
      setGeriAlDurumu('hata')
    }
  }

  // The next school day, for the evening: where to be, not what is owed —
  // the card and "Ayrıca" already name the work with its day.
  const sonrakiGun = useMemo(() => {
    const ajandaOf = (gun: Date) => buildAgenda(scheduleData, teamsData, hwData, calData, gun, nowMs)
    const bulunan = sonrakiOkulGunu(new Date(nowMs), gun => ajandaOf(gun).some(a => a.type === 'lesson'))
    if (!bulunan) return null
    const ajanda = ajandaOf(bulunan.tarih)
    return {
      ...bulunan,
      dersleri: ajanda.filter(a => a.type === 'lesson'),
      etkinlikler: ajanda.filter(a => a.type !== 'lesson' && a.type !== 'deadline'),
    }
  }, [scheduleData, teamsData, hwData, calData, nowMs])

  // The teacher's own words for the work in the box, one paragraph per line.
  const talimat = (top?.hw.detail?.description || '')
    .split('\n').map(l => l.trim()).filter(Boolean)

  const selectedIsToday = dayOffset === 0
  const dayName = DAYS_TR[selectedDate.getDay()]
  const dateStr = `${selectedDate.getDate()} ${MONTHS_TR[selectedDate.getMonth()]}`

  // Where to be: a lesson, ÖGEP or a private lesson. Deadlines are points in
  // time and calendar events stay on the timeline — neither takes the card.
  const yer = yerSec(agenda)
  const simdikiYer = yer.simdiki
  // Until the last bell the lesson is the one thing and the homework waits
  // under it as a preview; after it, the homework is the one thing (İ1).
  const okulModu = selectedIsToday && yer.dersSayisi > 0 && nowMin < yer.sonZil && simdikiYer != null

  // Finished items fold to one line on today's page (İ7). Another day is
  // being looked at on purpose, so it shows whole.
  const gecmis = selectedIsToday ? agenda.filter(a => a.isPast) : []
  const gorunen = selectedIsToday && !gecmisAcik ? agenda.filter(a => !a.isPast) : agenda

  // Once today's last bell has gone — or, on a day without school, from the
  // usual end of the day — the evening turns to tomorrow's bag.
  const yarinGoster = selectedIsToday && !okulModu && sonrakiGun != null
    && nowMin >= (yer.dersSayisi > 0 ? yer.sonZil : pencere.okulBitisi)

  // Upcoming exams, soonest first. One that falls on the next school day leads
  // the evening's "Yarın" and leaves the list, so it is said once; it never
  // takes the card — at 20:00 the page must not say "start revising" (İ4).
  const yaklasanSinavlar = (examData.exams || [])
    .filter(e => e.status === 'upcoming' && e.date)
    .map(e => ({ e, d: sinavAni(e) }))
    .filter((x): x is { e: typeof x.e; d: Date } => x.d !== null)
    .sort((a, b) => a.d.getTime() - b.d.getTime())
  const yarinSinavlari = yarinGoster && sonrakiGun
    ? yaklasanSinavlar.filter(x => isSameDay(x.d, sonrakiGun.tarih))
    : []
  // The nearest exam within a week gets a line of its own with its topics — the
  // same quiet voice as "Ayrıca"; one the evening's "Yarın" already leads with
  // is not said twice (İ4), and it leaves the list below.
  const onizleme = enYakinSinav(examData.exams || [], nowMs, new Set(yarinSinavlari.map(x => x.e.id)))
  const listeSinavlari = yaklasanSinavlar
    .filter(x => !yarinSinavlari.includes(x) && x.e.id !== onizleme?.id).slice(0, 3)

  // The now line sits between places, never inside one; a calendar event
  // running all day does not hide it.
  const activePlace = agenda.find(a => a.isActive && (yerMi(a) || a.type === 'deadline'))
  const nowInsertIdx = gorunen.findIndex(a => a.startMin > nowMin)
  const showNowMarker = selectedIsToday && !activePlace && okulModu && nowMin >= SCHOOL_START

  // D3: a fetch that failed must not look like an empty day. The sentence is
  // the reader's, never the HTTP status (D4).
  const arizali = Boolean(programHatasi || odevHatasi || takvimHatasi || sinavHatasi)

  const git = (yol: string) => (e: MouseEvent) => {
    e.preventDefault()
    navigate(yol)
  }

  if (loading || pencereYukleniyor) {
    // A load shorter than 400 ms shows nothing (S36, B48): a skeleton that
    // blinks for a frame is noise. Past it, the page's own shape in Carbon
    // skeletons (§5.2, B5): day line, strip, card and a few rows. One set,
    // nothing else moves.
    if (!programIskeleti && !pencereIskeleti) return null
    return (
      <div className="today today--yukleniyor" aria-busy="true">
        <span className="cds--visually-hidden" role="status">Bugün yükleniyor</span>
        <SkeletonText heading width="40%" className="today-skeleton__day" />
        <SkeletonPlaceholder className="today-skeleton__strip" />
        <SkeletonPlaceholder className="today-skeleton__card" />
        <SkeletonText paragraph lineCount={3} width="100%" />
      </div>
    )
  }

  const isKarti = nextThing.props.variant === 'work'

  return (
    <div className="today">
      {arizali && (
        <InlineNotification
          className="today-ariza"
          kind="warning"
          lowContrast
          hideCloseButton
          role="status"
          statusIconDescription="Uyarı"
          title="Bazı bilgiler şu an alınamadı"
          subtitle="Sayfa birkaç dakika içinde kendini yeniler."
        />
      )}

      {/* ── Day line: outside every container, the page's only expressive
          type (S16). Not a heading — the page's h1 lives on the shell. ── */}
      <div className="today__header">
        <IconButton
          kind="ghost"
          size="lg"
          align="bottom"
          label="Önceki gün"
          className="today__nav-btn"
          onClick={() => setDayOffset(v => v - 1)}
        >
          <ChevronLeft size={16} />
        </IconButton>
        <p className="today__day">
          <span className="today__day-name">{dayName}</span>{' '}
          <span className="today__date-str">{dateStr}</span>
        </p>
        <IconButton
          kind="ghost"
          size="lg"
          align="bottom"
          label="Sonraki gün"
          className="today__nav-btn"
          onClick={() => setDayOffset(v => v + 1)}
        >
          <ChevronRight size={16} />
        </IconButton>
        {dayOffset !== 0 && (
          <Button kind="ghost" size="lg" className="today__today-btn" onClick={() => setDayOffset(0)}>
            Bugüne dön
          </Button>
        )}
      </div>

      <DayStrip
        nowMin={nowMin}
        bedtimeMin={pencere.yatma}
        focusEndMin={pencere.odakSonu}
        dayStartMin={SCHOOL_START}
        school={seritOkulu}
      />

      {okulModu && simdikiYer && (
        <SimdiKarti
          yer={simdikiYer}
          sonraki={yer.sonraki}
          kalanDers={yer.kalanDers}
          nowMin={nowMin}
          ilk={yer.ilk}
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
        <YaptinSatiri className="today-done-note" ad={sonYapilan.ad} durum={geriAlDurumu} onGeriAl={geriAl} />
      )}

      {/* The rest of what is owed, said quietly: names and days, no coloured
          countdown chips competing with the card above (İ6). Carbon's on-page
          contained list at lg, so every row is a 48px target (B8). */}
      {ayricaGoster.length > 0 && (
        <ContainedList
          className="today-also"
          kind="on-page"
          size="lg"
          label="Ayrıca"
          action={ayricaFazla > 0 ? (
            <Button kind="ghost" size="lg" href="/isler" onClick={git('/isler')}>
              {`+${ayricaFazla} iş daha`}
            </Button>
          ) : undefined}
        >
          {ayricaGoster.map(({ hw, deadline }) => (
            <ContainedListItem
              key={`${hw['Ders Adı']}|${hw['Ödev Başlığı']}|${hw['Ödev Son Teslim Tarihi']}`}
              onClick={() => navigate('/isler')}
            >
              <span className="today-also__row">
                <span className="today-also__name">
                  <SubjectLabel course={hw.normalized_course || hw['Ders Adı']}>
                    {[hw.normalized_course || hw['Ders Adı'], hw['Ödev Başlığı']].filter(Boolean).join(' — ')}
                  </SubjectLabel>
                </span>
                {deadline && <span className="today-also__due"><Rakamli metin={kisaTeslim(deadline, now)} /></span>}
              </span>
            </ContainedListItem>
          ))}
        </ContainedList>
      )}

      {/* Exams in the same quiet voice as "Ayrıca": what and when, as a day,
          with the subject's 10px mark. They follow "Ayrıca": exams weeks away
          sat above homework due in four days. */}
      {onizleme && <SinavOnizleme exam={onizleme} now={now} onAc={() => navigate(`/sinavlar?sinav=${onizleme.id}`)} />}

      {listeSinavlari.length > 0 && (
        <ContainedList className="today-exams" kind="on-page" size="lg" label="Sınavlar">
          {listeSinavlari.map(({ e, d }) => (
            <ContainedListItem key={e.id} onClick={() => navigate('/sinavlar')}>
              <span className="today-also__row">
                <span className="today-also__name">
                  <SubjectLabel course={e.course} family={e.courseFamily}>{e.title || e.rawTitle}</SubjectLabel>
                </span>
                <span className="today-also__due"><Rakamli metin={e.allDay ? kisaGun(d, now) : kisaTeslim(d, now)} /></span>
              </span>
            </ContainedListItem>
          ))}
        </ContainedList>
      )}

      {yarinGoster && sonrakiGun && (
        <section className="today-tomorrow" aria-labelledby="bugun-yarin-baslik">
          <h2 id="bugun-yarin-baslik" className="today-tomorrow__title">
            {yarinBasligi(sonrakiGun.k, sonrakiGun.tarih)}
          </h2>
          {yarinSinavlari.map(({ e, d }) => (
            <p key={e.id} className="today-tomorrow__exam">
              Sınav ·{' '}
              {!e.allDay && <><span className="tedy-time">{saatDk(d)}</span> ·{' '}</>}
              <SubjectLabel course={e.course} family={e.courseFamily}>{e.title || e.rawTitle}</SubjectLabel>
            </p>
          ))}
          <p className="today-tomorrow__first">
            İlk ders <span className="tedy-time">{sonrakiGun.dersleri[0].time.split('–')[0]}</span>
            {' · '}{sonrakiGun.dersleri[0].name}
          </p>
          <p className="today-tomorrow__line">
            <span className="tedy-time">{sonrakiGun.dersleri.length}</span>
            {` ders: ${[...new Set(sonrakiGun.dersleri.map(d => d.name))].join(' · ')}`}
          </p>
          {sonrakiGun.etkinlikler.map(e => (
            <p key={`${e.startMin}-${e.name}`} className="today-tomorrow__line">
              <span className="tedy-time">{e.time.split('–')[0]}</span> · {e.name}
            </p>
          ))}
        </section>
      )}

      {agenda.length === 0 ? (
        // One line, not a card (İ6, §5.1).
        <EmptyLine>
          {dayName} için planlı ders, ödev teslimi veya etkinlik yok.
        </EmptyLine>
      ) : (
        <div className="today-day">
          {gecmis.length > 0 && (
            <Button
              kind="ghost"
              size="lg"
              className="today-past-fold"
              aria-expanded={gecmisAcik}
              aria-controls={ZAMAN_CIZELGESI_ID}
              renderIcon={gecmisAcik ? ChevronUp : ChevronDown}
              onClick={() => setGecmisAcik(v => !v)}
            >
              {`${bitenOzeti(gecmis)} · ${gecmisAcik ? 'Gizle' : 'Göster'}`}
            </Button>
          )}

          {/* ── Timeline: an ordered list, one item per place or deadline ── */}
          <ol className="today-tl" id={ZAMAN_CIZELGESI_ID} aria-label="Günün akışı">
            {gorunen.map((item, i) => {
              const cfg = TYPE_CONFIG[item.type]
              const Icon = cfg.icon
              const kart = (
                <>
                  <span className="today-tl__card-top">
                    <span className="today-tl__card-name">{item.name}</span>
                    {item.period != null && (
                      <span className="today-tl__card-period"><span className="tedy-time">{item.period}</span>.</span>
                    )}
                  </span>
                  {item.subtitle && (
                    <span className="today-tl__card-sub">{item.subtitle}</span>
                  )}
                  {(cfg.label || item.isActive) && (
                    <span className="today-tl__card-tags">
                      {item.isActive && <Tag as="span" type="gray" size="sm"><InProgress size={16} /> Devam ediyor</Tag>}
                      {cfg.label && <Tag as="span" type={cfg.tagType} size="sm"><cfg.icon size={16} /> {cfg.label}</Tag>}
                    </span>
                  )}
                </>
              )

              return (
                <Fragment key={`${item.type}-${item.startMin}-${item.name}`}>
                  {showNowMarker && nowInsertIdx === i && <NowMarker nowMin={nowMin} />}
                  <li
                    className={[
                      'today-tl__item',
                      subjectClass(item.course),
                      item.isPast && 'today-tl__item--past',
                      item.isActive && 'today-tl__item--active',
                      item.type === 'deadline' && 'today-tl__item--deadline',
                    ].filter(Boolean).join(' ')}
                  >
                    <span className="today-tl__time tedy-time">{item.time.split('–')[0]}</span>
                    <span className="today-tl__spine" aria-hidden="true">
                      <span className="today-tl__dot">
                        {item.isPast ? <Checkmark size={16} /> : <Icon size={16} />}
                      </span>
                    </span>
                    {item.type === 'deadline' ? (
                      // A real link: the keyboard reaches İşler too (B7).
                      <RouterLink to="/isler" className="today-tl__card today-tl__card--link">
                        {kart}
                      </RouterLink>
                    ) : (
                      <span className="today-tl__card">{kart}</span>
                    )}
                  </li>
                </Fragment>
              )
            })}
            {showNowMarker && nowInsertIdx === -1 && <NowMarker nowMin={nowMin} />}
          </ol>
        </div>
      )}
    </div>
  )
}

/* ── Sub-components ────────────────────────────────────────────────────────── */

/**
 * The one thing while school runs: where to be now, and what comes after.
 *
 * The view's one subject panel (İ8.3): the lesson's step-10 ground, its
 * step-30 border and a 4px accent edge. ÖGEP and other places without a
 * course stay neutral. Before 2026-09-24 this was a saturated gradient with a
 * pulsing dot and its own progress bar (İ1, İ6); the Day Strip is the only bar.
 */
function SimdiKarti({ yer, sonraki, kalanDers, nowMin, ilk }: {
  yer: AgendaItem
  sonraki?: AgendaItem
  kalanDers: number
  nowMin: number
  ilk: boolean
}) {
  return (
    <section
      className={['today-now', yer.course ? subjectClass(yer.course) : 'today-now--neutral'].join(' ')}
      aria-label="Şu anki ders"
    >
      <span className="today-now__eyebrow"><Rakamli metin={simdiUstu(yer, nowMin, ilk)} /></span>
      <h2 className="today-now__title">{yer.name}</h2>
      {yer.subtitle && <p className="today-now__sub">{yer.subtitle}</p>}
      <p className="today-now__next">
        <span>
          {sonraki
            ? <Rakamli metin={`Sonra: ${sonraki.name} ${sonraki.time.split('–')[0]}`} />
            : 'Bugünün sonuncusu'}
        </span>
        {kalanDers > 0 && <span><Rakamli metin={`${kalanDers} ders kaldı`} /></span>}
      </p>
    </section>
  )
}

/** The present moment on the line, said in words as well as drawn. */
function NowMarker({ nowMin }: { nowMin: number }) {
  const saat = `${iki(Math.floor(nowMin / 60))}:${iki(nowMin % 60)}`
  return (
    <li className="today-tl__now">
      <span className="today-tl__now-time">
        <span className="cds--visually-hidden">Şimdi </span>
        <span className="tedy-time">{saat}</span>
      </span>
      <span className="today-tl__now-line" aria-hidden="true" />
    </li>
  )
}
