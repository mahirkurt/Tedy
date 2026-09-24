import { useState, useMemo, useEffect } from 'react'
import { Tag, Tile, Button } from '@carbon/react'
import { ChevronDown, ChevronUp, Document, Task as TaskIcon } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import type { ExamItem, ExamsApiResponse } from '../types'
import { countdownTagType, getExamCountdown } from '../utils/countdown'
import { subjectClass } from '../utils/subject'
import { MONTHS_SHORT, gradeColor } from '../utils/formatters'
import { EmptyLine } from './patterns/EmptyLine'

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
    const d = new Date(dateStr)
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

function ExamCard({ exam, showCountdown, focusMode }: {
  exam: ExamItem
  showCountdown: boolean
  focusMode: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const countdown = useMemo(
    () => showCountdown && exam.date ? getExamCountdown(new Date(exam.date)) : null,
    [exam.date, showCountdown]
  )

  const hasDetails = !focusMode && (
    exam.aiSummary || exam.studyGuide ||
    exam.relatedHomework.length > 0 || exam.relatedContent.length > 0
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
    <Tile className={`${cardClass} ${subjectClass(exam.course, exam.courseFamily)}`}>
      <div className="exam-card__header">
        <div className="exam-card__info">
          <span className="exam-card__course">{exam.course}</span>
          <span className="exam-card__title">{exam.title || exam.rawTitle}</span>
          <span className="exam-card__date">{formatExamDate(exam.date)}</span>
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
          {exam.aiSummary && (
            <div className="exam-card__section">
              <div className="exam-card__section-title">🤖 Çalışma Özeti</div>
              <p className="exam-card__section-text">{exam.aiSummary}</p>
            </div>
          )}
          {exam.studyGuide && (
            <div className="exam-card__section">
              <div className="exam-card__section-title">🤖 Sınav Rehberi</div>
              <p className="exam-card__section-text">{exam.studyGuide}</p>
            </div>
          )}
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
          {exam.relatedContent.length > 0 && (
            <div className="exam-card__section">
              <div className="exam-card__section-title">
                <Document size={14} /> İlgili Ders İçerikleri
              </div>
              <ul className="exam-card__list">
                {exam.relatedContent.map((c, i) => (
                  <li key={i}><span>{c.title}</span></li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Tile>
  )
}

export default function ExamTimeline() {
  const { data } = useApi<ExamsApiResponse>('/api/exams', EMPTY_RESPONSE)
  const { focusMode } = useFocusMode()
  const [, setTick] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 60000)
    return () => clearInterval(t)
  }, [])

  const upcoming = useMemo(() => data.exams.filter(e => e.status === 'upcoming'), [data.exams])
  const past = useMemo(() => data.exams.filter(e => e.status === 'past'), [data.exams])

  if (data.exams.length === 0) {
    return (
      <EmptyLine>Takvimde henüz sınav yok.</EmptyLine>
    )
  }

  return (
    <div className="exam-timeline">
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
          <h3 className="exam-section__title">Yaklaşan Sınavlar</h3>
          <div className="exam-section__list">
            {upcoming.map(exam => (
              <ExamCard key={exam.id} exam={exam} showCountdown focusMode={focusMode} />
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
                <ExamCard key={exam.id} exam={exam} showCountdown={false} focusMode={focusMode} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
