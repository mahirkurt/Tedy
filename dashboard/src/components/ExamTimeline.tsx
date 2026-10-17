import { useState, useMemo, useEffect } from 'react'
import { Tag, Tile, Button } from '@carbon/react'
import { ChevronDown, ChevronUp, Task as TaskIcon } from '@carbon/icons-react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import type { ExamItem, ExamsApiResponse } from '../types'
import { countdownTagType, getExamCountdown } from '../utils/countdown'
import { subjectClass } from '../utils/subject'
import { MONTHS_SHORT, gradeColor } from '../utils/formatters'
import { EmptyLine } from './patterns/EmptyLine'
import { acikOgeAc } from '../asistan/sayfaBaglami'
import SinavUyarilari from './SinavUyarilari'
import { SinavAyrintisi, IncelenmediNotu } from './SinavKarti'
import { yerelAni, zamanMetni } from '../utils/sinav'

const EMPTY_RESPONSE: ExamsApiResponse = { exams: [], stats: { upcoming: 0, past: 0, averageGrade: null } }

function urgencyModifier(urgency: string): string {
  switch (urgency) {
    case 'critical': return 'exam-card--critical'
    case 'urgent': return 'exam-card--urgent'
    case 'soon': return 'exam-card--soon'
    default: return 'exam-card--normal'
  }
}

function formatExamDate(dateStr: string | null): string {
  if (!dateStr) return 'Tarih bilinmiyor'
  try {
    const d = yerelAni(dateStr)
    if (!d) return dateStr
    const day = d.getDate()
    const month = MONTHS_SHORT[d.getMonth()]
    const hours = d.getHours().toString().padStart(2, '0')
    const mins = d.getMinutes().toString().padStart(2, '0')
    if (hours === '00' && mins === '00') return `${day} ${month}`
    return `${day} ${month} ${hours}:${mins}`
  } catch {
    return dateStr
  }
}

function ExamCard({ exam, showCountdown, focusMode, baslangicAcik }: {
  exam: ExamItem
  showCountdown: boolean
  focusMode: boolean
  baslangicAcik?: boolean
}) {
  const [expanded, setExpanded] = useState(baslangicAcik ?? false)
  // Her kart kendi kaydını bırakır: iki kart açıkken biri kapanınca öbürü bağlam olarak kalır.
  useEffect(() => (expanded ? acikOgeAc({ tur: 'sinav', id: exam.id, etiket: exam.title }) : undefined),
    [expanded, exam.id, exam.title])
  const countdown = useMemo(
    () => showCountdown && exam.date ? getExamCountdown(yerelAni(exam.date)) : null,
    [exam.date, showCountdown]
  )

  const hasDetails = !focusMode && (
    exam.relatedHomework.length > 0 || (exam.konular?.length ?? 0) > 0
    || (exam.kaynaklar?.length ?? 0) > 0 || !!exam.tarihBelirsiz
  )

  const gradeStyle = !showCountdown && exam.grade ? gradeColor(exam.grade) : ''

  const cardClass = [
    'exam-card',
    showCountdown ? 'exam-card--upcoming' : 'exam-card--past',
    showCountdown && countdown ? urgencyModifier(countdown.urgency) : '',
    !showCountdown && exam.grade ? 'exam-card--graded' : '',
  ].filter(Boolean).join(' ')

  const detailsId = `exam-details-${exam.id}`

  return (
    <Tile id={`sinav-${exam.id}`} className={`${cardClass} ${subjectClass(exam.course, exam.courseFamily)}`}>
      <div className="exam-card__header">
        <div className="exam-card__info">
          {/* Live titles often carry the course already ("Özdebir … GİS ·
              İzleme Sınavı"); the kicker said it a second time. İşler drops it
              by the same rule. The left edge still carries the subject. */}
          {!(exam.title || exam.rawTitle || '').startsWith(exam.course) && (
            <span className="exam-card__course">{exam.course}</span>
          )}
          <span className="exam-card__title">{exam.title || exam.rawTitle}</span>
          {/* No line when the portal gives no date: the graded exams come from
              the grade table, which carries none, and "Tarih bilinmiyor" under
              every one of 25 cards was the same sentence 25 times (İ6). */}
          {exam.date
            ? <span className="exam-card__date">{exam.allDay ? zamanMetni(exam) : formatExamDate(exam.date)}</span>
            : (exam.hafta || exam.tarihBelirsiz) && <span className="exam-card__date">{zamanMetni(exam)}</span>}
        </div>
        <div className="exam-card__badges">
          {showCountdown && countdown && (
            <Tag type={countdownTagType(countdown.urgency)} size="sm">
              {countdown.text}
            </Tag>
          )}
          {!showCountdown && exam.grade && (
            <span className="exam-card__grade" style={gradeStyle ? { color: gradeStyle } : undefined}>
              {exam.grade}
            </span>
          )}
          {!showCountdown && !exam.grade && (
            <Tag type="gray" size="sm">Henüz girilmedi</Tag>
          )}
        </div>
      </div>

      {showCountdown && countdown && (
        <div className="exam-card__countdown-bar">
          <div
            className="exam-card__countdown-fill"
            style={{ width: `${countdown.fraction * 100}%` }}
          />
        </div>
      )}

      {hasDetails && (
        <Button
          kind="ghost"
          size="sm"
          className="exam-card__expand-btn"
          onClick={() => setExpanded(!expanded)}
          renderIcon={expanded ? ChevronUp : ChevronDown}
          aria-expanded={expanded}
          aria-controls={detailsId}
        >
          {expanded ? 'Gizle' : 'Detaylar'}
        </Button>
      )}

      {expanded && hasDetails && (
        <div className="exam-card__details" id={detailsId} role="region" aria-label={`${exam.rawTitle} detayları`}>
          {exam.relatedHomework.length > 0 && (
            <div className="exam-card__section">
              <div className="exam-card__section-title">
                <TaskIcon size={14} /> İlgili Ödevler
              </div>
              <ul className="exam-card__list">
                {exam.relatedHomework.map((hw, i) => (
                  <li key={i}>
                    <span>{hw.title}</span>
                    <Tag type={hw.status === 'Yaptı' ? 'green' : 'gray'} size="sm">{hw.status || 'Bekliyor'}</Tag>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <SinavAyrintisi exam={exam} />
        </div>
      )}
    </Tile>
  )
}

export default function ExamTimeline() {
  const { data } = useApi<ExamsApiResponse>('/api/exams', EMPTY_RESPONSE)
  const { focusMode } = useFocusMode()
  const [, setTick] = useState(0)
  const [searchParams] = useSearchParams()
  const acilacak = searchParams.get('sinav')
  const { hash } = useLocation()

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 60000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    const hedef = acilacak ? document.getElementById(`sinav-${acilacak}`) : hash === '#uyarilar' ? document.getElementById('uyarilar') : null
    hedef?.scrollIntoView({ block: 'start' })
  }, [acilacak, hash, data.exams.length])

  const upcoming = useMemo(() => data.exams.filter(e => e.status === 'upcoming'), [data.exams])
  const past = useMemo(() => data.exams.filter(e => e.status === 'past'), [data.exams])

  if (data.exams.length === 0) {
    return (
      <>
        <SinavUyarilari />
        <IncelenmediNotu tespit={data.tespit} />
        <EmptyLine>Takvimde henüz sınav yok.</EmptyLine>
      </>
    )
  }

  return (
    <div className="exam-timeline">
      <SinavUyarilari />
      <IncelenmediNotu tespit={data.tespit} />
      <div className="exam-stats" role="region" aria-label="Sınav istatistikleri">
        <div className="exam-stats__item">
          <span className="exam-stats__value">{data.stats.upcoming}</span>
          <span className="exam-stats__label">Yaklaşan</span>
        </div>
        <div className="exam-stats__item">
          <span className="exam-stats__value">{data.stats.past}</span>
          <span className="exam-stats__label">Geçmiş</span>
        </div>
        {data.stats.averageGrade !== null && (
          <div className="exam-stats__item">
            <span className="exam-stats__value exam-stats__value--grade">
              {data.stats.averageGrade}
            </span>
            <span className="exam-stats__label">Ortalama</span>
          </div>
        )}
      </div>

      {upcoming.length > 0 && (
        <div className="exam-section">
          <h2 className="exam-section__title">Yaklaşan Sınavlar</h2>
          <div className="exam-section__list">
            {upcoming.map(exam => (
              <ExamCard key={exam.id} exam={exam} showCountdown focusMode={focusMode} baslangicAcik={exam.id === acilacak} />
            ))}
          </div>
        </div>
      )}

      {past.length > 0 && (
        <>
          <div className="exam-divider">
            <span>Geçmiş Sınavlar</span>
          </div>
          <div className="exam-section">
            <div className="exam-section__list">
              {past.map(exam => (
                <ExamCard key={exam.id} exam={exam} showCountdown={false} focusMode={focusMode} baslangicAcik={exam.id === acilacak} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
