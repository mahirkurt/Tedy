import { Link as CarbonLink, Tag } from '@carbon/react'
import { useNavigate } from 'react-router-dom'
import type { ExamItem } from '../types'
import { kisaTeslim } from '../utils/formatters'
import { konuOzeti, sinavEtiketi, zamanMetni } from '../utils/sinav'
import SubjectLabel from './SubjectLabel'
import './SinavKarti.scss'

/** Bugün: 7 gün içindeki en yakın sınav — sessiz, tek satırlık özet (İ1, İ6). */
export function SinavOnizleme({ exam, now, onAc }: { exam: ExamItem; now: Date; onAc: () => void }) {
  const konu = konuOzeti(exam.konular)
  const kaynak = exam.kaynaklar?.find(k => k.tur !== 'takvim')
  return (
    <section className="sinav-onizleme" aria-label="Yaklaşan sınav">
      <div className="today-also__head">
        <span className="today-also__title">YAKLAŞAN SINAV</span>
      </div>
      <button type="button" className="today-also__item" onClick={onAc}>
        <span className="today-also__name">
          <SubjectLabel course={exam.course} family={exam.courseFamily}>{exam.title || exam.rawTitle}</SubjectLabel>
        </span>
        <span className="today-also__due">{exam.date ? kisaTeslim(new Date(exam.date), now) : zamanMetni(exam)}</span>
      </button>
      {konu && <p className="sinav-onizleme__konular">Konular: {konu}</p>}
      <p className="sinav-onizleme__baglantilar">
        {kaynak?.baglanti && (
          <CarbonLink href={kaynak.baglanti} size="sm">Kaynak: {kaynak.etiket}</CarbonLink>
        )}
        <CarbonLink href="/sinavlar#uyarilar" size="sm">Sınav uyarıları</CarbonLink>
      </p>
    </section>
  )
}

/** İşler: son 48 saatte bulunan ya da değişen sınav için gri, metinli etiket. */
export function SinavEtiketi({ exam, nowMs }: { exam: ExamItem; nowMs: number }) {
  const etiket = sinavEtiketi(exam, nowMs)
  return etiket ? <Tag type="gray" size="sm" className="sinav-etiketi">{etiket}</Tag> : null
}

/** Sınavlar: kaynaktaki konular ve kaynaklar, kısa alıntıyla (spec §8). */
export function SinavAyrintisi({ exam }: { exam: ExamItem }) {
  const navigate = useNavigate()
  const konular = exam.konular ?? []
  const kaynaklar = exam.kaynaklar ?? []
  if (konular.length === 0 && kaynaklar.length === 0 && !exam.tarihBelirsiz) return null
  return (
    <div className="sinav-ayrinti">
      {exam.tarihBelirsiz && <p className="sinav-ayrinti__not">Tarih belirsiz: duyuruda gün yazmıyor.</p>}
      {konular.length > 0 && (
        <div className="exam-card__section">
          <div className="exam-card__section-title">Konular</div>
          <ul className="exam-card__list">{konular.map(k => <li key={k}><span>{k}</span></li>)}</ul>
        </div>
      )}
      {kaynaklar.length > 0 && (
        <div className="exam-card__section">
          <div className="exam-card__section-title">Kaynaklar</div>
          <ul className="sinav-ayrinti__kaynaklar">
            {kaynaklar.map((k, i) => (
              <li key={i}>
                {k.baglanti ? (
                  <CarbonLink href={k.baglanti} onClick={e => {
                    if (k.baglanti?.startsWith('/') && !k.baglanti.startsWith('/api/')) {
                      e.preventDefault(); navigate(k.baglanti)
                    }
                  }}>{k.etiket}</CarbonLink>
                ) : <span>{k.etiket}</span>}
                {k.alinti && <blockquote className="sinav-ayrinti__alinti">{k.alinti}</blockquote>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
