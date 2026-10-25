import { useCallback, useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Breadcrumb, BreadcrumbItem, Button, ContentSwitcher, InlineNotification, RadioButton, RadioButtonGroup,
         SkeletonText, Switch } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { uygulamaIcindeAc } from '../utils/gezinme'
import { subjectClass } from '../utils/subject'
import Kaydirilabilir from '../components/Kaydirilabilir'
import KarsilastirmaTablosu from './KarsilastirmaTablosu'
import CiktiAyrintisi from './CiktiAyrintisi'
import DurumGostergesi from './DurumGostergesi'
import Uyarilar from './Uyarilar'
import { hazirlikUyarilari } from './belge'
import { kilavuzAdresi, sinavAdi, tarihMetni } from './hazirlik'
import type { DersOzeti } from './tipler'
import './Hazirlik.scss'

/** Duyurunun durumuna göre sayfanın tek bildirimi (spec §3.2): kesin yeşil ve öğretmenin sözü aynen. Olası kipte
 *  duyuru cümlesi alıntılanmaz: hiçbir senaryo "bu" diye sunulmaz (K8). */
function DuyuruBildirimi({ oz }: { oz: DersOzeti }) {
  const d = oz.durum
  if (d.tur === 'kesin') {
    return <InlineNotification kind="success" lowContrast hideCloseButton statusIconDescription="Onay"
      title={`Okul ${d.senaryo}. senaryoyu duyurdu.`} subtitle={d.duyuru ? `«${d.duyuru}»` : undefined} />
  }
  if (d.tur === 'ulke_geneli') {
    return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi"
      title="Bu yazılı ülke genelinde ortak yapılır; senaryo yok." subtitle={oz.not ?? undefined} />
  }
  if (d.tur === 'gecti') {
    return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi" title="Bu yazılı geçti." />
  }
  if (d.uyari === 'senaryo_yok') {
    return <InlineNotification kind="warning" lowContrast hideCloseButton statusIconDescription="Uyarı"
      title={`Duyuru ${d.anilan.join(', ')}. senaryo diyor; MEB tablosunda bu yazılı için 1–${d.senaryo_sayisi} var.`} />
  }
  return <InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi" title="Senaryo duyurulmadı."
    subtitle="Tablodan bir senaryo seçebilir ya da kılavuzu bütün senaryolarla açabilirsin." />
}

/** Ders sayfası (spec §3.2, taslak A "karşılaştırma tablosu"): yazılı seçici, duyuru, tablo, satır ayrıntısı,
 *  kılavuza geçiş. Kitap haritası olmayan ders senaryo verisiyle açılır (spec §7). */
export default function HazirlikDersSayfasi() {
  const { ders: anahtar = '' } = useParams()
  const [arama, setArama] = useSearchParams()
  const gezin = useNavigate()
  const no = arama.get('sinav') === '2' ? 2 : 1
  const { data, loading, iskelet, hataTuru, hataDurumu, hataMesaji } = useApi<DersOzeti | null>(`/api/hazirlik/${anahtar}/${no}`, null)
  const [secili, setSecili] = useState<string | null>(null)
  const [secim, setSecim] = useState<string>('olasi')
  const satirDugmesi = useRef<HTMLButtonElement | null>(null)
  const kapat = useCallback(() => { setSecili(null); satirDugmesi.current?.focus() }, [])
  if (loading) {
    return iskelet ? <section className="hazirlik-ders" aria-busy="true"><SkeletonText heading /><SkeletonText paragraph lineCount={6} /></section> : null
  }
  // useApi uç değişince eski veriyi tutar: başka bir ders ya da yazılının verisi bu yazılının adı altında çizilmez.
  const oz = data && data.anahtar === anahtar && data.sinav_no === no ? data : null
  const sinavlar = data && data.anahtar === anahtar ? data.sinavlar : null
  // Seçici, ders yüklenirken de yerinde kalır (anahtarlı: odak, yeni yazılı yüklenince düşmesin).
  const yazili = (n: number) => { setSecili(null); setSecim('olasi'); setArama({ sinav: String(n) }) }
  const yazililar = sinavlar && (
    <ContentSwitcher key="yazililar" size="lg" selectedIndex={no - 1} onChange={({ index }) => yazili((index ?? 0) + 1)}
      aria-label="Yazılı seçimi" className="hazirlik-ders__yazililar">
      {sinavlar.map(s => (
        <Switch key={s.sinav_no} name={String(s.sinav_no)} text={`${sinavAdi(s.sinav_no)} · ${tarihMetni(s.durum.tarih, false)}`} />
      ))}
    </ContentSwitcher>
  )
  if (!oz && hataTuru) {
    // D15: sunucu kendi cümlesini gönderdiyse (409 "Yeni yılın tabloları bekleniyor.") bildirim onu söyler.
    if (hataDurumu === 409 && hataMesaji) {
      return <section className="hazirlik-ders"><InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi"
        title={hataMesaji} subtitle="MEB bu dönemin konu-soru dağılım tablolarını yayımlayınca burada görünür." /></section>
    }
    const h = apiHataCumlesi(hataTuru, 'Ders sayfası')
    return <section className="hazirlik-ders">
      {yazililar}
      <InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata" title={h.baslik} subtitle={hataMesaji ?? h.ayrinti} />
    </section>
  }
  if (!oz) return <section className="hazirlik-ders" aria-busy="true">{yazililar}</section>
  const duyurulan = oz.duyurulan
  const secilen = duyurulan ?? (oz.senaryolar.includes(Number(secim)) ? Number(secim) : null)
  const vurgu = secilen ?? (oz.durum.tur === 'gecti' ? oz.durum.senaryo : null)
  const kilavuz = kilavuzAdresi(anahtar, no, duyurulan === null ? secilen : null)
  const ek = duyurulan !== null ? ` (${duyurulan}. senaryo)` : secilen !== null ? ` (${secilen}. senaryo, olası)` : ' (bütün senaryolar)'
  const satir = oz.gruplar.flatMap(g => g.satirlar).find(s => s.kod === secili) ?? null
  const kilavuzaGit = (e: MouseEvent<HTMLElement>) => {
    if (!uygulamaIcindeAc(e, kilavuz, e.currentTarget.getAttribute('target'))) return
    e.preventDefault()
    gezin(kilavuz)
  }
  return (
    <section className={`hazirlik-ders ${subjectClass(oz.ders)}`} aria-labelledby="hazirlik-ders-baslik">
      <Breadcrumb aria-label="Konum">
        <BreadcrumbItem href="/hazirlik" onClick={(e: MouseEvent<HTMLElement>) => {
          // Ctrl/orta tık/yeni sekme tarayıcıya kalır (C13).
          if (!uygulamaIcindeAc(e, '/hazirlik', e.currentTarget.getAttribute('target'))) return
          e.preventDefault()
          gezin('/hazirlik')
        }}>Sınav hazırlığı</BreadcrumbItem>
      </Breadcrumb>
      <h2 id="hazirlik-ders-baslik" className="hazirlik-ders__baslik">{oz.ders}</h2>
      {yazililar}
      <DurumGostergesi durum={oz.durum} />
      <DuyuruBildirimi oz={oz} />
      <Uyarilar metinler={hazirlikUyarilari(oz)} kip="ekran" />
      {oz.tur === 'senaryolu' && duyurulan === null && oz.durum.tur !== 'gecti' && (
        // K8: seçilen senaryo duyurulmuş gibi sunulmaz.
        <RadioButtonGroup legendText="Kılavuzun senaryosu" name="kilavuz-senaryosu" orientation="horizontal"
          valueSelected={secilen === null ? 'olasi' : String(secilen)} onChange={v => setSecim(String(v))}
          helperText={secilen !== null ? `Seçtiğin ${secilen}. senaryo (duyurulmadı)` : undefined}>
          {[<RadioButton key="olasi" id="senaryo-olasi" value="olasi" labelText="Bütün senaryolar (olası)" />,
            ...oz.senaryolar.map(n => <RadioButton key={n} id={`senaryo-${n}`} value={String(n)} labelText={`${n}. senaryo`} />)]}
        </RadioButtonGroup>
      )}
      {oz.tur === 'senaryolu' && (
        <div className={`hazirlik-ders__govde${satir ? ' hazirlik-ders__govde--acik' : ''}`}>
          <Kaydirilabilir className="hazirlik-ders__tablo" etiket="Senaryo karşılaştırması tablosu">
            <KarsilastirmaTablosu matris={oz} vurgu={vurgu} kip="ekran" secili={secili}
              vurguEtiketi={duyurulan !== null ? 'duyurulan' : oz.durum.tur === 'gecti' ? 'yapılan' : 'seçilen'}
              sec={(kod, dugme) => { satirDugmesi.current = dugme; setSecili(kod === secili ? null : kod) }} />
          </Kaydirilabilir>
          {satir && <CiktiAyrintisi satir={satir} kilavuz={kilavuz} kapat={kapat} />}
        </div>
      )}
      {oz.tur === 'senaryolu' && (
        <div className="hazirlik-ders__eylemler">
          {/* Başka sayfaya götürdüğü için bağlantı (adresi var, yeni sekmede açılır); Carbon birincil düğme biçiminde. */}
          <Button kind="primary" size="lg" href={kilavuz} onClick={kilavuzaGit}>{`Kapsam kılavuzunu aç${ek}`}</Button>
        </div>
      )}
    </section>
  )
}
