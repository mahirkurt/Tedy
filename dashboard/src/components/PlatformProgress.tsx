import { ProgressBar, Tag, InlineNotification, Accordion, AccordionItem, Link } from '@carbon/react'
import { ChartBar, CheckmarkFilled, CloseFilled, Launch } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/FocusModeContext'
import type { ECVideo, A3KLesson, SebitHomework } from '../types'

interface ECData {
  total_videos?: number
  completed_videos?: number
  videos?: ECVideo[]
}

interface A3KData {
  teacher_assigned_count?: number
  teacher_assigned_completed?: number
  dashboard_stats?: { completed?: number; target?: number; firstTryScore?: number }
  lessons?: A3KLesson[]
}

interface SebitData {
  total_homework?: number
  completed_count?: number
  homework?: SebitHomework[]
}

function DifficultyTag({ level }: { level: number }) {
  const type = level <= 2 ? 'green' : level <= 4 ? 'blue' : level <= 6 ? 'warm-gray' : 'red'
  return <Tag type={type} size="sm">Seviye {level}</Tag>
}

export default function PlatformProgress() {
  const { data: ec } = useApi<ECData>('/api/progress/ec', {})
  const { data: a3k } = useApi<A3KData>('/api/progress/a3k', {})
  const { data: sebit } = useApi<SebitData>('/api/sebit', {})
  const { focusMode } = useFocusMode()

  const platforms = [
    { name: 'EnglishCentral', done: ec.completed_videos || 0, total: ec.total_videos || 0 },
    { name: 'Achieve3000', done: a3k.teacher_assigned_completed || 0, total: a3k.teacher_assigned_count || 0 },
    { name: 'SEBIT', done: sebit.completed_count || 0, total: sebit.total_homework || 0 }
  ]

  const allComplete = platforms.every(p => p.total > 0 && p.done >= p.total)

  const ecVideos = ec.videos || []
  const a3kLessons = (a3k.lessons || []).filter(l => l.is_teacher_assigned !== false)
  const sebitItems = sebit.homework || []

  return (
    <div className="dashboard-card">
      <h4 className="dashboard-card__title">
        <ChartBar size={20} />
        Platform İlerleme
      </h4>

      {allComplete && (
        <InlineNotification
          kind="success"
          title="Tüm platformlar tamamlandı!"
          hideCloseButton
          lowContrast
          className="platform-complete-notification"
        />
      )}

      <Accordion className="platform-accordion">
        {/* EnglishCentral */}
        {(!focusMode || platforms[0].done < platforms[0].total || platforms[0].total === 0) && (() => {
          const p = platforms[0]
          const pct = p.total > 0 ? Math.round((p.done / p.total) * 100) : 0
          return (
            <AccordionItem
              title={
                <span className="platform-accordion__header">
                  <span className="platform-accordion__name">{p.name}</span>
                  <Tag type={pct === 100 ? 'green' : pct > 50 ? 'blue' : 'warm-gray'} size="sm">
                    {p.done}/{p.total}
                  </Tag>
                </span> as unknown as string
              }
            >
              <div className="platform-accordion__progress">
                <ProgressBar label={p.name} value={pct} status={pct === 100 ? 'finished' : 'active'} size="small" hideLabel />
              </div>
              {ecVideos.length > 0 ? (
                <div className="platform-detail-list">
                  {ecVideos.map((v, i) => (
                    <div key={i} className="platform-detail-row">
                      <span className="platform-detail-row__status">
                        {v.completed
                          ? <CheckmarkFilled size={16} className="platform-detail-row__icon--done" />
                          : <CloseFilled size={16} className="platform-detail-row__icon--pending" />
                        }
                      </span>
                      <span className="platform-detail-row__title">
                        {v.url
                          ? <Link href={v.url} target="_blank" rel="noopener" renderIcon={Launch}>{v.title}</Link>
                          : v.title
                        }
                      </span>
                      <span className="platform-detail-row__tags">
                        {v.difficulty > 0 && <DifficultyTag level={v.difficulty} />}
                        {v.duration && <span className="platform-detail-row__duration">{v.duration}</span>}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="dashboard-empty-text">Video listesi yükleniyor…</p>
              )}
            </AccordionItem>
          )
        })()}

        {/* Achieve3000 */}
        {(!focusMode || platforms[1].done < platforms[1].total || platforms[1].total === 0) && (() => {
          const p = platforms[1]
          const pct = p.total > 0 ? Math.round((p.done / p.total) * 100) : 0
          return (
            <AccordionItem
              title={
                <span className="platform-accordion__header">
                  <span className="platform-accordion__name">{p.name}</span>
                  <Tag type={pct === 100 ? 'green' : pct > 50 ? 'blue' : 'warm-gray'} size="sm">
                    {p.done}/{p.total}
                  </Tag>
                </span> as unknown as string
              }
            >
              <div className="platform-accordion__progress">
                <ProgressBar label={p.name} value={pct} status={pct === 100 ? 'finished' : 'active'} size="small" hideLabel />
              </div>
              {a3kLessons.length > 0 ? (
                <div className="platform-detail-list">
                  {a3kLessons.map((l, i) => (
                    <div key={i} className="platform-detail-row">
                      <span className="platform-detail-row__status">
                        {l.completed
                          ? <CheckmarkFilled size={16} className="platform-detail-row__icon--done" />
                          : <CloseFilled size={16} className="platform-detail-row__icon--pending" />
                        }
                      </span>
                      <span className="platform-detail-row__title">
                        {l.url
                          ? <Link href={l.url} target="_blank" rel="noopener" renderIcon={Launch}>{l.title}</Link>
                          : l.title
                        }
                      </span>
                      <span className="platform-detail-row__tags">
                        {l.category && <Tag type="teal" size="sm">{l.category}</Tag>}
                        <span className="platform-detail-row__steps">
                          {l.completed_steps}/{l.total_steps} adım
                        </span>
                        {l.score > 0 && (
                          <span className="platform-detail-row__score">{l.score}%</span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="dashboard-empty-text">Ders listesi yükleniyor…</p>
              )}
              {a3k.dashboard_stats?.firstTryScore != null && (
                <div className="platform-a3k-score">
                  <span className="platform-a3k-score__label">A3K İlk Deneme Skoru</span>
                  <div className="platform-a3k-score__gauge">
                    <div
                      className="platform-a3k-score__gauge-fill"
                      style={{ width: `${Math.min(100, a3k.dashboard_stats.firstTryScore)}%` }}
                    />
                  </div>
                  <span className="platform-a3k-score__value">{a3k.dashboard_stats.firstTryScore}</span>
                </div>
              )}
            </AccordionItem>
          )
        })()}

        {/* SEBIT */}
        {(!focusMode || platforms[2].done < platforms[2].total || platforms[2].total === 0) && (() => {
          const p = platforms[2]
          const pct = p.total > 0 ? Math.round((p.done / p.total) * 100) : 0
          return (
            <AccordionItem
              title={
                <span className="platform-accordion__header">
                  <span className="platform-accordion__name">{p.name}</span>
                  <Tag type={pct === 100 ? 'green' : pct > 50 ? 'blue' : 'warm-gray'} size="sm">
                    {p.done}/{p.total}
                  </Tag>
                </span> as unknown as string
              }
            >
              <div className="platform-accordion__progress">
                <ProgressBar label={p.name} value={pct} status={pct === 100 ? 'finished' : 'active'} size="small" hideLabel />
              </div>
              {sebitItems.length > 0 ? (
                <div className="platform-detail-list">
                  {sebitItems.map((s, i) => (
                    <div key={i} className="platform-detail-row platform-detail-row--sebit">
                      <span className="platform-detail-row__status">
                        {s.completed
                          ? <CheckmarkFilled size={16} className="platform-detail-row__icon--done" />
                          : <CloseFilled size={16} className="platform-detail-row__icon--pending" />
                        }
                      </span>
                      <span className="platform-detail-row__title">{s.title}</span>
                      <span className="platform-detail-row__tags">
                        {s.course && <Tag type="purple" size="sm">{s.course}</Tag>}
                        <span className="platform-detail-row__steps">{s.progress}%</span>
                      </span>
                      <div className="platform-detail-row__sebit-meta">
                        {s.teacher && <span className="platform-detail-row__teacher">{s.teacher}</span>}
                        {s.start_date && s.end_date && (
                          <span className="platform-detail-row__dates">{s.start_date} – {s.end_date}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="dashboard-empty-text">Ödev listesi yükleniyor…</p>
              )}
            </AccordionItem>
          )
        })()}
      </Accordion>
    </div>
  )
}
