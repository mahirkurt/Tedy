import { ProgressBar, Tag, InlineNotification, Accordion, AccordionItem, Link, SkeletonText } from '@carbon/react'
import { ChartBar, CheckmarkFilled, CloseFilled, Launch } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import type { ECVideo, A3KLesson, SebitHomework } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import SubjectLabel from './SubjectLabel'
import './AlistirmaKarti.scss'

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

interface Gunluk {
  zayif: { konu: string; kazanim_kodu: string | null; dogru: number; toplam: number }[]
  calisilan: { id: string; kazanim_kodu: string | null; sayfa_basligi: string | null; ogretmen: string }[]
  degerlendirmeler: { id: string; guclu_yanlar: string; duzeyler: 'baslangic' | 'gelisiyor' | 'yeterli'; sonraki_adim: string }[]
  hafta: { baslangic: string; sohbet: { ogretmen: string; sayi: number }[]; alistirma: number; puan: { dogru: number; toplam: number } }
  /** Asistan cevaplarına verilen geri bildirim (aileye öğrencinin, öğrenciye kendisinin). */
  geri_bildirim?: { hafta: { olumlu: number; olumsuz: number }; son_olumsuz: { kategori: string | null; metin: string; zaman: string }[] }
}

const OGRETMEN_ADLARI: Record<string, string> = { genel: 'Genel', turkce: 'Türkçe', fen: 'Fen', sosyal: 'Sosyal', matematik: 'Matematik' }
const DUZEY_ADLARI = { baslangic: 'Başlangıç', gelisiyor: 'Gelişiyor', yeterli: 'Yeterli' }

function OgrenmeGunlugu() {
  const { data, loading, error } = useApi<Gunluk | null>('/api/assistant/ogrenme-gunlugu', null)
  if (error === 'HTTP 403') return null
  return <section className="ogrenme-gunlugu" aria-labelledby="ogrenme-gunlugu-baslik">
    <h3 id="ogrenme-gunlugu-baslik">Öğrenme günlüğü</h3>
    {loading ? <SkeletonText paragraph lineCount={3} /> : error ? <p>Öğrenme günlüğü alınamadı.</p> : data && <>
      <div>
        <h4>Bu hafta</h4>
        {data.hafta.sohbet.length === 0 ? <p>Sohbet · 0</p> : data.hafta.sohbet.map(s =>
          <p key={s.ogretmen}>{OGRETMEN_ADLARI[s.ogretmen] || s.ogretmen} · {s.sayi}</p>)}
        <p>Alıştırma · {data.hafta.alistirma}</p>
        {data.hafta.puan.toplam > 0 && <p>Puan · {data.hafta.puan.dogru}/{data.hafta.puan.toplam}</p>}
      </div>
      <div>
        <h4>Zorlanılan konular</h4>
        {data.zayif.length === 0 ? <p>Henüz deneme yok. Bir alıştırma bitince burada görünür.</p> :
          <ul>{data.zayif.map(s => <li key={`${s.konu}-${s.kazanim_kodu || ''}`}>
            <span>{s.konu}</span> · {s.dogru}/{s.toplam}{s.kazanim_kodu && ` · ${s.kazanim_kodu}`}
          </li>)}</ul>}
      </div>
      {data.calisilan.length > 0 && <div>
        <h4>Son çalışılan konular</h4>
        <ul>{data.calisilan.map((s, i) => <li key={s.id || i}>
          {s.kazanim_kodu || s.sayfa_basligi}
        </li>)}</ul>
      </div>}
      {data.degerlendirmeler.length > 0 && <div>
        <h4>Çalışma değerlendirmeleri</h4>
        <ul>{data.degerlendirmeler.map(s => <li key={s.id}>
          <p><strong>{DUZEY_ADLARI[s.duzeyler]}</strong></p>
          <p>{s.guclu_yanlar}</p>
          <p>{s.sonraki_adim}</p>
        </li>)}</ul>
      </div>}
      {data.geri_bildirim && <div className="ogrenme-gunlugu__geri-bildirim">
        <h4>Asistana geri bildirim</h4>
        <p>Asistan cevapları: {data.geri_bildirim.hafta.olumlu} beğenildi, {data.geri_bildirim.hafta.olumsuz} beğenilmedi</p>
        {data.geri_bildirim.son_olumsuz.length > 0 && <ul>{data.geri_bildirim.son_olumsuz.map(n => (
          <li key={n.zaman}>{[n.kategori, n.metin].filter(Boolean).join(' — ')}</li>))}</ul>}
      </div>}
    </>}
  </section>
}

function DifficultyTag({ level }: { level: number }) {
  const type = level <= 2 ? 'green' : level <= 4 ? 'blue' : level <= 6 ? 'warm-gray' : 'red'
  return <Tag type={type} size="sm">Seviye {level}</Tag>
}


export default function PlatformProgress() {
  const { data: ec, loading: ecLoading } = useApi<ECData>('/api/progress/ec', {})
  const { data: a3k, loading: a3kLoading } = useApi<A3KData>('/api/progress/a3k', {})
  const { data: sebit, loading: sebitLoading } = useApi<SebitData>('/api/sebit', {})
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
      <h2 className="dashboard-card__title">
        <ChartBar size={20} />
        Platform İlerleme
      </h2>

      {allComplete && (
        <InlineNotification
          kind="success"
          title="Tüm platformlar tamamlandı!"
          hideCloseButton
          lowContrast
          className="platform-complete-notification"
        />
      )}

      <OgrenmeGunlugu />

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
                  <span className="platform-accordion__count">{p.done}/{p.total}</span>
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
                ecLoading ? (
                  <SkeletonText paragraph lineCount={3} />
                ) : (
                  <EmptyLine>Henüz izlenmiş video yok.</EmptyLine>
                )
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
                  <span className="platform-accordion__count">{p.done}/{p.total}</span>
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
                        {l.category && <Tag type="cool-gray" size="sm">{l.category}</Tag>}
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
                a3kLoading ? (
                  <SkeletonText paragraph lineCount={3} />
                ) : (
                  <EmptyLine>Henüz tamamlanmış ders yok.</EmptyLine>
                )
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
                  <span className="platform-accordion__count">{p.done}/{p.total}</span>
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
                        {s.course && <SubjectLabel className="platform-detail-row__course" course={s.course} />}
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
                sebitLoading ? (
                  <SkeletonText paragraph lineCount={3} />
                ) : (
                  <EmptyLine>Henüz ödev yok.</EmptyLine>
                )
              )}
            </AccordionItem>
          )
        })()}
      </Accordion>
    </div>
  )
}
