import { useId, useState } from 'react'
import { Button, ContainedList, ContainedListItem, Link as CarbonLink, Tag } from '@carbon/react'
import { ArrowRight, CheckmarkFilled, Launch, WarningAltFilled } from '@carbon/icons-react'
import { useNavigate } from 'react-router-dom'
import { useIcGezinme } from '../hooks/useIcGezinme'
import { asistanaSor } from '../asistan/sayfaBaglami'
import { kilavuzGirisi } from '../hazirlik/hazirlik'
import type { ExamItem } from '../types'
import { kisaGun, kisaTeslim } from '../utils/formatters'
import { konuAnahtarlari, konuOzeti, sinavAni, sinavEtiketi, zamanMetni } from '../utils/sinav'
import { senaryoGorunumu } from '../utils/sinavSenaryosu'
import SubjectLabel from './SubjectLabel'
import IcBaglanti from './patterns/IcBaglanti'
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
      <ContainedList kind="on-page" size="lg" label="Yaklaşan Sınav">
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
          <IcBaglanti href={kaynak.baglanti} size="sm">Kaynak: {kaynak.etiket}</IcBaglanti>
        )}
        <IcBaglanti href="/sinavlar#uyarilar" size="sm">Sınav uyarıları</IcBaglanti>
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

/** MEB konu-soru dağılımı (spec 2026-10-19 §5): senaryo doğrulaması ya da tahmini; durum ikon + metin. */
function MebSenaryoBolumu({ exam }: { exam: ExamItem }) {
  const [acik, setAcik] = useState(false)
  const listeId = useId()
  const gezin = useNavigate()
  // Sınav Hazırlığı girişi (spec 2026-10-25 §3.4): kartın ana eylemi, kılavuza (ya da ülke genelinde ders sayfasına) gider.
  const giris = exam.senaryo ? kilavuzGirisi(exam.senaryo) : null
  const girisTikla = useIcGezinme(giris?.href ?? null)
  if (!exam.senaryo) return null
  const g = senaryoGorunumu(exam.senaryo)
  const sor = () => {
    const karsilandi = asistanaSor({ tur: 'sinav', id: exam.id, etiket: `${exam.course} — ${exam.title}` })
    if (!karsilandi) gezin('/asistan?sayfa=sinavlar')
  }
  return (
    <div className="exam-card__section meb-senaryo">
      <div className="exam-card__section-title">MEB konu-soru dağılımı</div>
      {g.cumleler.map((c, i) => (
        <p key={i} className="meb-senaryo__cumle">
          {i === 0 && g.ikon === 'onay' && <CheckmarkFilled size={16} aria-label="Doğrulandı" className="meb-senaryo__ikon" />}
          {i === 0 && g.ikon === 'uyari' && <WarningAltFilled size={16} aria-label="Uyarı" className="meb-senaryo__ikon" />}
          {c}
        </p>
      ))}
      {g.duyuru && <p className="meb-senaryo__duyuru">{g.duyuru}</p>}
      {g.dugme && (
        <>
          <Button kind="ghost" size="sm" aria-expanded={acik} aria-controls={listeId} onClick={() => setAcik(!acik)}>
            {acik ? 'Çıktıları gizle' : g.dugme}
          </Button>
          {acik && (
            <ul id={listeId} className="meb-senaryo__liste">
              {g.satirlar.map(s => (
                <li key={s.metin}>
                  <span>{s.metin}</span>
                  {s.duyuruda && <Tag type="gray" size="sm" className="meb-senaryo__etiket">duyuruda</Tag>}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <p className="meb-senaryo__alt">
        {/* B58: a link that leaves the page says so with Carbon's Launch icon. */}
        <CarbonLink href={exam.senaryo.kaynak} target="_blank" rel="noreferrer" size="sm" renderIcon={Launch}>MEB tablosu ({g.kaynak})</CarbonLink>
      </p>
      {giris && <Button kind="tertiary" size="sm" href={giris.href} renderIcon={ArrowRight} onClick={girisTikla}>{giris.etiket}</Button>}
      <Button kind="ghost" size="sm" onClick={sor}>Örnek sınav için asistana sor</Button>
    </div>
  )
}

/** Sınavlar: kaynaktaki konular ve kaynaklar, kısa alıntıyla (spec §8). */
export function SinavAyrintisi({ exam }: { exam: ExamItem }) {
  const konular = exam.konular ?? []
  const kaynaklar = exam.kaynaklar ?? []
  if (konular.length === 0 && kaynaklar.length === 0 && !exam.tarihBelirsiz && !exam.senaryo) return null
  return (
    <div className="sinav-ayrinti">
      {exam.tarihBelirsiz && <p className="sinav-ayrinti__not">Tarih belirsiz: duyuruda gün yazmıyor.</p>}
      {konular.length > 0 && (
        <div className="exam-card__section">
          <div className="exam-card__section-title">Konular</div>
          <ul className="exam-card__list">
            {konuAnahtarlari(konular).map(({ anahtar, konu }) => <li key={anahtar}><span>{konu}</span></li>)}
          </ul>
        </div>
      )}
      <MebSenaryoBolumu exam={exam} />
      {kaynaklar.length > 0 && (
        <div className="exam-card__section">
          <div className="exam-card__section-title">Kaynaklar</div>
          <ul className="sinav-ayrinti__kaynaklar">
            {kaynaklar.map((k, i) => (
              <li key={i}>
                {k.baglanti ? <IcBaglanti href={k.baglanti}>{k.etiket}</IcBaglanti> : <span>{k.etiket}</span>}
                {k.alinti && <blockquote className="sinav-ayrinti__alinti">{k.alinti}</blockquote>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
