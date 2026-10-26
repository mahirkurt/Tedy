import { useEffect } from 'react'
import type { MouseEvent } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Accordion, AccordionItem, Breadcrumb, BreadcrumbItem, Button, InlineNotification, SkeletonText } from '@carbon/react'
import { Launch } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useSession } from '../contexts/session'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { uygulamaIcindeAc } from '../utils/gezinme'
import { asistanaSor } from '../asistan/sayfaBaglami'
import KilavuzBelgesi from './KilavuzBelgesi'
import PdfSecenekleri from './PdfSecenekleri'
import { BOLUM, bolumler, ustBilgi } from './belge'
import { baskiAdresi, modelAdresi } from './hazirlik'
import { usePdfPenceresi, usePdfSecenekleri } from './usePdfSecenekleri'
import { useIsaretler } from './useIsaretler'
import type { KilavuzModeli } from './tipler'
import './Hazirlik.scss'

/** Kapsam kılavuzu ekranı (spec §3.3): yapışkan yan içindekiler, belge, işaretler, asistana sor. */
export default function KilavuzSayfasi() {
  const { ders: anahtar = '', sinav = '1' } = useParams()
  const [arama] = useSearchParams()
  const { hash } = useLocation()
  const gezin = useNavigate()
  const no = sinav === '2' ? 2 : 1
  const ham = arama.get('senaryo')
  const senaryo = ham && /^\d{1,2}$/.test(ham) ? Number(ham) : null
  const { data, loading, iskelet, hataTuru, hataDurumu, hataMesaji } = useApi<KilavuzModeli | null>(
    modelAdresi(anahtar, no, senaryo, { ebeveyn: false, isaret: true }), null)
  // useApi uç değişince eski veriyi tutar: başka bir dersin, yazılının ya da istenen senaryonun kılavuzu bu adresin adı
  // altında çizilmez. Ülke geneli ortak sınavda sunucu istenen senaryoyu yok sayar (senaryo: null); o kip her
  // ?senaryo=N adresinin yanıtıdır.
  const m = data && data.anahtar === anahtar && data.sinav_no === no
    && (senaryo === null || data.senaryo === senaryo || data.kip === 'ulke_geneli') ? data : null
  const { isaretler, isaretle, hata, hatayiKapat } = useIsaretler(anahtar, m)
  const { acik: pdfAcik, ac: pdfAc, kapat: pdfKapat, dugme: pdfDugmesi } = usePdfPenceresi()
  const pdfSecimi = usePdfSecenekleri(useSession()?.email ?? '')
  const cizildi = m !== null
  // D21: ders sayfasındaki "Kılavuzda aç" #cikti-… ile gelir; belge çizilince o öğeye kaydırılır.
  useEffect(() => {
    if (!cizildi || !hash) return
    document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView({ block: 'start' })
  }, [cizildi, hash])
  if (loading) {
    return iskelet ? <section className="kilavuz-sayfa" aria-busy="true"><SkeletonText heading /><SkeletonText paragraph lineCount={8} /></section> : null
  }
  if (!m) {
    // D15: sunucu kendi cümlesini gönderdiyse (409 "Yeni yılın tabloları bekleniyor.") bildirim onu söyler.
    if (hataDurumu === 409 && hataMesaji) {
      return <section className="kilavuz-sayfa"><InlineNotification kind="info" lowContrast hideCloseButton statusIconDescription="Bilgi"
        title={hataMesaji} subtitle="MEB bu dönemin konu-soru dağılım tablolarını yayımlayınca burada görünür." /></section>
    }
    if (!hataTuru) return <section className="kilavuz-sayfa" aria-busy="true" />
    const h = apiHataCumlesi(hataTuru, 'Kapsam kılavuzu')
    return <section className="kilavuz-sayfa"><InlineNotification kind="error" lowContrast hideCloseButton statusIconDescription="Hata"
      title={h.baslik} subtitle={hataMesaji ?? h.ayrinti} /></section>
  }
  // D11: soru sınavı ve senaryoyu sabitler — etiket ders · yazılı · senaryo taşır (olası kipte "olası" der, K8).
  // Sınav kaydı yoksa aynı bağlam ders + yazılı + senaryo kimliğiyle kurulur.
  const sor = () => {
    const kimlik = m.durum.sinav_id ?? `hazirlik:${anahtar}:${no}:${m.senaryo ?? 'olasi'}`
    if (!asistanaSor({ tur: 'sinav', id: kimlik, etiket: ustBilgi(m), kilavuz: { kip: m.kip, senaryo: m.kip === 'ulke_geneli' ? null : m.senaryo } })) gezin('/asistan?sayfa=sinavlar')
  }
  const icGezinme = (yol: string) => (e: MouseEvent<HTMLElement>) => {
    // Ctrl/orta tık/yeni sekme tarayıcıya kalır (C13).
    if (!uygulamaIcindeAc(e, yol, e.currentTarget.getAttribute('target'))) return
    e.preventDefault()
    gezin(yol)
  }
  const dersSayfasi = `/hazirlik/${anahtar}?sinav=${no}`
  const icindekiler = bolumler(m).map(b => <li key={b.id}><a href={`#${b.id}`}>{b.ad}</a></li>)
  return (
    <div className="kilavuz-sayfa">
      <div className="kilavuz-sayfa__ust">
        <Breadcrumb aria-label="Konum" noTrailingSlash>
          <BreadcrumbItem href="/hazirlik" onClick={icGezinme('/hazirlik')}>Sınav hazırlığı</BreadcrumbItem>
          <BreadcrumbItem href={dersSayfasi} onClick={icGezinme(dersSayfasi)}>{m.ders}</BreadcrumbItem>
          <BreadcrumbItem isCurrentPage aria-current="page">{BOLUM.kilavuz}</BreadcrumbItem>
        </Breadcrumb>
        <div className="kilavuz-sayfa__eylemler">
          <Button kind="primary" size="lg" ref={pdfDugmesi} onClick={pdfAc}>PDF olarak indir</Button>
          {/* PDF'in birebir önizlemesi: aynı seçimle, baskı görünümü yeni sekmede (sayfadan çıktığını ikon söyler, B58). */}
          <Button kind="ghost" size="lg" renderIcon={Launch} href={baskiAdresi(anahtar, no, m.senaryo, pdfSecimi)}
            target="_blank" rel="noreferrer">A4 önizleme</Button>
          <Button kind="ghost" size="lg" onClick={sor}>Asistana sor</Button>
        </div>
      </div>
      {pdfAcik && <PdfSecenekleri anahtar={anahtar} no={no} senaryo={m.senaryo} kapat={pdfKapat} />}
      {/* Telefonda (lg altı) yan içindekiler yok: bölümlere aynı bağlantılarla açılır bir menüden atlanır. Kâğıda
          girmez — KilavuzBelgesi'nin değil, ekran sayfasının parçasıdır. */}
      <Accordion className="kilavuz-sayfa__bolumler" size="lg">
        <AccordionItem title="Bölümler">
          <nav aria-label="Kılavuzun bölümleri">
            <ul>{icindekiler}</ul>
          </nav>
        </AccordionItem>
      </Accordion>
      <div className="kilavuz-sayfa__duzen">
        <nav className="kilavuz-sayfa__icindekiler" aria-label="Kılavuzun bölümleri">
          <ul>{icindekiler}</ul>
        </nav>
        <KilavuzBelgesi model={m} kip="ekran" isaretler={isaretler} isaretle={isaretle} isaretHatasi={hata} hatayiKapat={hatayiKapat} />
      </div>
    </div>
  )
}
