import { ContainedList, ContainedListItem, Link as CarbonLink, Tag } from '@carbon/react'
import { useNavigate } from 'react-router-dom'
import type { ExamItem } from '../types'
import { kisaGun, kisaTeslim } from '../utils/formatters'
import { konuOzeti, sinavAni, sinavEtiketi, zamanMetni } from '../utils/sinav'
import SubjectLabel from './SubjectLabel'
import { Rakamli } from './patterns/Rakamli'
import './SinavKarti.scss'

/** Bugün: 7 gün içindeki en yakın sınav — sessiz, tek satırlık özet (İ1, İ6).
 *  "Ayrıca" ve "Sınavlar" gibi Carbon'un sayfa içi listesi; başlık cümle düzeninde (S38, B70). */
export function SinavOnizleme({ exam, now, onAc }: { exam: ExamItem; now: Date; onAc: () => void }) {
  const konu = konuOzeti(exam.konular)
  const kaynak = exam.kaynaklar?.find(k => k.tur !== 'takvim')
  const ani = sinavAni(exam)
  return (
    <div className="sinav-onizleme">
      <ContainedList kind="on-page" size="lg" label="Yaklaşan sınav">
        <ContainedListItem onClick={onAc}>
          <span className="today-also__row">
            <span className="today-also__name">
              <SubjectLabel course={exam.course} family={exam.courseFamily}>{exam.title || exam.rawTitle}</SubjectLabel>
            </span>
            <span className="today-also__due">
              <Rakamli metin={ani ? (exam.allDay ? kisaGun(ani, now) : kisaTeslim(ani, now)) : zamanMetni(exam)} />
            </span>
          </span>
        </ContainedListItem>
      </ContainedList>
      {konu && <p className="sinav-onizleme__konular">Konular: {konu}</p>}
      <p className="sinav-onizleme__baglantilar">
        {kaynak?.baglanti && (
          <CarbonLink href={kaynak.baglanti} size="sm">Kaynak: {kaynak.etiket}</CarbonLink>
        )}
        <CarbonLink href="/sinavlar#uyarilar" size="sm">Sınav uyarıları</CarbonLink>
      </p>
    </div>
  )
}

/** Son tespit turunda okunamayan duyuru varsa liste eksik olabilir; sessizce eksik kalmaz. */
export function IncelenmediNotu({ tespit }: { tespit?: { incelenmedi: number } | null }) {
  if ((tespit?.incelenmedi ?? 0) <= 0) return null
  return <p className="exams-ahead__not">Bazı ders duyuruları incelenemedi; sınav listesi eksik olabilir.</p>
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
