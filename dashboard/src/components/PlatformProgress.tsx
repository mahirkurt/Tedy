import { Tag, Accordion, AccordionItem, Link, SkeletonText, ContainedList, ContainedListItem } from '@carbon/react'
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
  /** SEBİT is switched off (TEDY_SEBIT=0): nothing is read, the old reading is not shown. */
  pasif?: boolean
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
  const { data, loading, iskelet, error } = useApi<Gunluk | null>('/api/assistant/ogrenme-gunlugu', null)
  if (error === 'HTTP 403') return null
  return <section className="ogrenme-gunlugu" aria-labelledby="ogrenme-gunlugu-baslik">
    <h3 id="ogrenme-gunlugu-baslik">Öğrenme Günlüğü</h3>
    {loading ? (iskelet ? <div aria-busy="true"><SkeletonText paragraph lineCount={3} /></div> : null) : error ? <p role="alert">Öğrenme günlüğü alınamadı.</p> : data && <>
      <div>
        <h4>Bu Hafta</h4>
        {data.hafta.sohbet.length === 0 ? <p>Sohbet · 0</p> : data.hafta.sohbet.map(s =>
          <p key={s.ogretmen}>{OGRETMEN_ADLARI[s.ogretmen] || s.ogretmen} · {s.sayi}</p>)}
        <p>Alıştırma · {data.hafta.alistirma}</p>
        {data.hafta.puan.toplam > 0 && <p>Puan · {data.hafta.puan.dogru}/{data.hafta.puan.toplam}</p>}
      </div>
      <div>
        <h4>Zorlanılan Konular</h4>
        {data.zayif.length === 0 ? <p>Henüz deneme yok. Bir alıştırma bitince burada görünür.</p> :
          <ul>{data.zayif.map(s => <li key={`${s.konu}-${s.kazanim_kodu || ''}`}>
            <span>{s.konu}</span> · {s.dogru}/{s.toplam}{s.kazanim_kodu && ` · ${s.kazanim_kodu}`}
          </li>)}</ul>}
      </div>
      {data.calisilan.length > 0 && <div>
        <h4>Son Çalışılan Konular</h4>
        <ul>{data.calisilan.map((s, i) => <li key={s.id || i}>
          {s.kazanim_kodu || s.sayfa_basligi}
        </li>)}</ul>
      </div>}
      {data.degerlendirmeler.length > 0 && <div>
        <h4>Çalışma Değerlendirmeleri</h4>
        <ul>{data.degerlendirmeler.map(s => <li key={s.id}>
          <p><strong>{DUZEY_ADLARI[s.duzeyler]}</strong></p>
          <p>{s.guclu_yanlar}</p>
          <p>{s.sonraki_adim}</p>
        </li>)}</ul>
      </div>}
      {data.geri_bildirim && <div className="ogrenme-gunlugu__geri-bildirim">
        <h4>Asistana Geri Bildirim</h4>
        <p>Asistan cevapları: {data.geri_bildirim.hafta.olumlu} beğenildi, {data.geri_bildirim.hafta.olumsuz} beğenilmedi</p>
        {data.geri_bildirim.son_olumsuz.length > 0 && <ul>{data.geri_bildirim.son_olumsuz.map(n => (
          <li key={n.zaman}>{[n.kategori, n.metin].filter(Boolean).join(' — ')}</li>))}</ul>}
      </div>}
    </>}
  </section>
}

function DifficultyTag({ level }: { level: number }) {
  // B21: sıralı veri durum ya da ders rengiyle boyanmaz; seviye sayının kendisidir.
  return <Tag type="gray" size="sm">Seviye {level}</Tag>
}


type Platform = { ad: string; birim: string; done: number; total: number; durum?: string }

/** One line per platform, said in words (B51, §8.7): a Carbon ProgressBar is for progress the system makes,
 *  not a count of what the reader finished — and a finished platform is a fact, not a celebration. */
function platformDurumu(p: Platform): string {
  if (p.durum) return p.durum
  if (p.total === 0) return 'Atanmış iş yok'
  if (p.done >= p.total) return `Tamamlandı · ${p.done}/${p.total} ${p.birim}`
  return `${p.done}/${p.total} ${p.birim}`
}

function Durum({ tamam }: { tamam: boolean }) {
  return tamam
    ? <CheckmarkFilled size={16} className="platform-detail-row__icon--done" aria-label="Tamamlandı" />
    : <CloseFilled size={16} className="platform-detail-row__icon--pending" aria-label="Bekliyor" />
}

export default function PlatformProgress() {
  const { data: ec, loading: ecLoading, iskelet: ecIskelet } = useApi<ECData>('/api/progress/ec', {})
  const { data: a3k, loading: a3kLoading, iskelet: a3kIskelet } = useApi<A3KData>('/api/progress/a3k', {})
  const { data: sebit, loading: sebitLoading, iskelet: sebitIskelet } = useApi<SebitData>('/api/sebit', {})
  const { focusMode } = useFocusMode()

  const platforms: Platform[] = [
    { ad: 'EnglishCentral', birim: 'video', done: ec.completed_videos || 0, total: ec.total_videos || 0 },
    { ad: 'Achieve3000', birim: 'ders', done: a3k.teacher_assigned_completed || 0, total: a3k.teacher_assigned_count || 0 },
    sebit.pasif
      ? { ad: 'SEBIT', birim: 'ödev', done: 0, total: 0, durum: 'Takip edilmiyor' }
      : { ad: 'SEBIT', birim: 'ödev', done: sebit.completed_count || 0, total: sebit.total_homework || 0 },
  ]
  // Focus mode keeps what is still owed.
  const gorunur = (p: Platform) => !focusMode || p.total === 0 || p.done < p.total

  const ecVideos = ec.videos || []
  const a3kLessons = (a3k.lessons || []).filter(l => l.is_teacher_assigned !== false)
  const sebitItems = sebit.homework || []
  // B66 (§4.7, İ6): one list and one skeleton — three panels each loading on their own drew three at once.
  const yukleniyor = ecLoading || a3kLoading || sebitLoading
  const iskelet = ecIskelet || a3kIskelet || sebitIskelet

  return (
    <div className="dashboard-card">
      <h2 className="dashboard-card__title">
        <ChartBar size={20} />
        Platform İlerlemesi
      </h2>

      <OgrenmeGunlugu />

      {yukleniyor ? (
        iskelet ? <div aria-busy="true"><SkeletonText paragraph lineCount={3} /></div> : null
      ) : (<>
        <ContainedList label="Platformlar" kind="on-page" size="lg" className="platform-list">
          {platforms.filter(gorunur).map(p => (
            <ContainedListItem key={p.ad}>
              <span className="platform-list__row">
                <span className="platform-list__name">{p.ad}</span>
                <span className="platform-list__state">{platformDurumu(p)}</span>
              </span>
            </ContainedListItem>
          ))}
        </ContainedList>

        {/* The detail, one accordion, closed (§4.7). */}
        <Accordion className="platform-accordion">
          {gorunur(platforms[0]) && (
            <AccordionItem title="EnglishCentral videoları">
              {ecVideos.length > 0 ? (
                <ul className="platform-detail-list">
                  {ecVideos.map((v, i) => (
                    <li key={i} className="platform-detail-row">
                      <span className="platform-detail-row__status"><Durum tamam={!!v.completed} /></span>
                      <span className="platform-detail-row__title" title={v.title}>
                        {v.url
                          ? <Link href={v.url} target="_blank" rel="noopener" renderIcon={Launch}>{v.title}</Link>
                          : v.title}
                      </span>
                      <span className="platform-detail-row__tags">
                        {v.difficulty > 0 && <DifficultyTag level={v.difficulty} />}
                        {v.duration && <span className="platform-detail-row__duration tedy-time">{v.duration}</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : <EmptyLine>Henüz izlenmiş video yok.</EmptyLine>}
            </AccordionItem>
          )}

          {gorunur(platforms[1]) && (
            <AccordionItem title="Achieve3000 dersleri">
              {a3kLessons.length > 0 ? (
                <ul className="platform-detail-list">
                  {a3kLessons.map((l, i) => (
                    <li key={i} className="platform-detail-row">
                      <span className="platform-detail-row__status"><Durum tamam={!!l.completed} /></span>
                      <span className="platform-detail-row__title" title={l.title}>
                        {l.url
                          ? <Link href={l.url} target="_blank" rel="noopener" renderIcon={Launch}>{l.title}</Link>
                          : l.title}
                      </span>
                      <span className="platform-detail-row__tags">
                        {l.category && <Tag type="cool-gray" size="sm">{l.category}</Tag>}
                        <span className="platform-detail-row__steps">{l.completed_steps}/{l.total_steps} adım</span>
                        {l.score > 0 && <span className="platform-detail-row__score">{l.score}%</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : <EmptyLine>Henüz tamamlanmış ders yok.</EmptyLine>}
              {/* A score, said as a figure (B51): the gauge drew a bar beside the number it repeated. */}
              {a3k.dashboard_stats?.firstTryScore != null && (
                <p className="platform-a3k-score">
                  Achieve3000 ilk deneme puanı <span className="tedy-time">{a3k.dashboard_stats.firstTryScore}</span>
                </p>
              )}
            </AccordionItem>
          )}

          {!sebit.pasif && gorunur(platforms[2]) && (
            <AccordionItem title="SEBIT ödevleri">
              {sebitItems.length > 0 ? (
                <ul className="platform-detail-list">
                  {sebitItems.map((s, i) => (
                    <li key={i} className="platform-detail-row platform-detail-row--sebit">
                      <span className="platform-detail-row__status"><Durum tamam={!!s.completed} /></span>
                      <span className="platform-detail-row__title" title={s.title}>{s.title}</span>
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
                    </li>
                  ))}
                </ul>
              ) : <EmptyLine>Henüz ödev yok.</EmptyLine>}
            </AccordionItem>
          )}
        </Accordion>
      </>)}
    </div>
  )
}
