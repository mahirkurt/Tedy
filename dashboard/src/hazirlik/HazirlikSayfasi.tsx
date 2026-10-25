import { ContainedList, ContainedListItem, InlineNotification, SkeletonText, Tile } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { subjectClass } from '../utils/subject'
import IcBaglanti from '../components/patterns/IcBaglanti'
import DurumGostergesi from './DurumGostergesi'
import { kalanGunMetni, sayisalTarih, sinavAdi, tarihMetni, yaklasanAyrinti } from './hazirlik'
import type { GenelBakis } from './tipler'
import './Hazirlik.scss'

/** Sınav Hazırlığı ana sayfası (spec §3.1, taslak A "önce zaman"): tarihi belli ortak yazılılar geri sayımla,
 *  sonra altı dersin karosu. */
export default function HazirlikSayfasi() {
  const { data, loading, iskelet, hataTuru } = useApi<GenelBakis | null>('/api/hazirlik', null)
  if (loading) {
    return iskelet ? <section className="hazirlik" aria-busy="true"><SkeletonText heading /><SkeletonText paragraph lineCount={4} /></section> : null
  }
  if (!data) {
    const h = apiHataCumlesi(hataTuru ?? 'sunucu', 'Sınav hazırlığı')
    return <section className="hazirlik"><InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title={h.baslik} subtitle={h.ayrinti} /></section>
  }
  const k = data.kaynak
  return (
    <section className="hazirlik" aria-labelledby="hazirlik-baslik">
      <header>
        <h2 id="hazirlik-baslik" className="hazirlik__baslik">Sınav Hazırlığı</h2>
        {k && <p className="hazirlik__kaynak">{`MEB konu-soru dağılım tabloları · ${k.sinif}. sınıf · ${k.donem}. dönem (güncelleme ${sayisalTarih(k.meb_guncelleme)})`}</p>}
      </header>
      {data.durum === 'tablo_eski' && <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi" title="Yeni yılın tabloları bekleniyor." subtitle="MEB bu dönemin konu-soru dağılım tablolarını yayımlayınca burada görünür." />}
      {data.durum === 'tablo_yok' && <InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title="MEB konu-soru dağılım tablosu okunamadı." subtitle="Sayfayı birkaç dakika sonra yeniden aç." />}
      {data.durum === 'hazir' && (
        <>
          {data.yaklasan.length > 0 && (
            <ContainedList kind="on-page" size="lg" label="Yaklaşan Ortak Yazılılar" className="hazirlik-yaklasan">
              {data.yaklasan.map(y => (
                <ContainedListItem key={`${y.anahtar}-${y.sinav_no}`} className={`hazirlik-yaklasan__oge ${subjectClass(y.ders)}`}>
                  <span className="hazirlik-yaklasan__ust">
                    <IcBaglanti href={`/hazirlik/${y.anahtar}?sinav=${y.sinav_no}`}>{`${y.ders} · ${sinavAdi(y.sinav_no)}`}</IcBaglanti>
                    <span className="hazirlik-yaklasan__kalan">{kalanGunMetni(y.durum.kalan_gun)}</span>
                  </span>
                  <span className="hazirlik-yaklasan__ayrinti">{yaklasanAyrinti(y.durum, y.soru)}</span>
                  <DurumGostergesi durum={y.durum} />
                </ContainedListItem>
              ))}
            </ContainedList>
          )}
          <section aria-labelledby="hazirlik-dersler">
            <h3 id="hazirlik-dersler" className="hazirlik__bolum-baslik">Dersler</h3>
            <ul className="hazirlik-dersler">
              {data.dersler.map(d => (
                <li key={d.anahtar}>
                  <Tile className={`hazirlik-karo ${subjectClass(d.ders)}`}>
                    <IcBaglanti href={`/hazirlik/${d.anahtar}`}>{d.ders}</IcBaglanti>
                    {d.sinavlar.map(s => (
                      <span key={s.sinav_no} className="hazirlik-karo__sinav">
                        <span>{`${sinavAdi(s.sinav_no)} · ${s.durum.tur === 'gecti' ? 'geçti' : tarihMetni(s.durum.tarih, false)}`}</span>
                        <DurumGostergesi durum={s.durum} />
                      </span>
                    ))}
                  </Tile>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </section>
  )
}
