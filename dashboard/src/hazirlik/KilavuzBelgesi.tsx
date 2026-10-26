import { Checkbox, InlineNotification, Link as CarbonLink, Tag } from '@carbon/react'
import { Checkbox as KutuIkonu, CheckboxChecked, Launch } from '@carbon/icons-react'
import IcBaglanti from '../components/patterns/IcBaglanti'
import Kaydirilabilir from '../components/Kaydirilabilir'
import { subjectClass } from '../utils/subject'
import DurumGostergesi from './DurumGostergesi'
import KarsilastirmaTablosu from './KarsilastirmaTablosu'
import Uyarilar from './Uyarilar'
import { BOLUM, bolumler, damgaMetni, hazirlikUyarilari, ustBilgi } from './belge'
import { BASLIK_TURU, baslikMetni, ciktiKimligi, ebeveynCumleleri, kalanGunMetni, sayfaMetni,
         soruMetni, tarihMetni } from './hazirlik'
import type { Blok, IsaretDurumu, KilavuzModeli, KitapYolu } from './tipler'
import type { IsaretHatasi } from './useIsaretler'
import './Kilavuz.scss'

type Kip = 'ekran' | 'baski'
type Isaretle = (kod: string, durum: IsaretDurumu, onceki: IsaretDurumu) => void

function KagitKutusu({ dolu, ad }: { dolu: boolean; ad: string }) {
  return (
    <span className="kilavuz-isaret__kutu">
      {dolu ? <CheckboxChecked size={16} aria-hidden="true" /> : <KutuIkonu size={16} aria-hidden="true" />}
      {ad}{dolu && <span className="cds--visually-hidden"> (işaretli)</span>}
    </span>
  )
}

/** Kitap yolu, kitaptaki adlarıyla (K1); son öğe (konu, yoksa çerçeve) kalın — metni `kitapYoluMetni` ile aynı. */
function YolMetni({ y }: { y: KitapYolu }) {
  const once = y.konu ? [y.kitap, y.unite, y.cerceve] : [y.kitap, y.unite]
  // Tek kutu: Carbon bağlantısı esnek kutudur; metin ve kalın konu ayrı öğe olursa yan yana iki sütuna bölünür.
  return <span className="kilavuz-yol__metin">{`${once.join(' › ')} › `}<strong>{y.konu ?? y.cerceve}</strong></span>
}

/** Hazırlık işareti: ekranda iki Carbon onay kutusu (biri seçilince öteki kalkar), kâğıtta durağan karşılığı (K11).
 *  Kaydedilemeyen işaretin bildirimi, okurun dokunduğu bloğun içinde çizilir (spec §7). */
function IsaretAlani({ b, kip, isaret, isaretle, hata, hatayiKapat }: {
  b: Blok; kip: Kip; isaret: IsaretDurumu; isaretle?: Isaretle; hata?: IsaretHatasi | null; hatayiKapat?: () => void
}) {
  if (kip === 'baski' || !isaretle) {
    return <p className="kilavuz-isaret"><KagitKutusu dolu={isaret === 'hazirim'} ad="Hazırım" /><KagitKutusu dolu={isaret === 'tekrar'} ad="Tekrar" /></p>
  }
  const kimlik = ciktiKimligi(b.kod)
  return (
    <div className="kilavuz-isaret">
      <fieldset className="kilavuz-isaret__kutular">
        <legend className="cds--visually-hidden">{`${b.kod} hazırlık işareti`}</legend>
        <Checkbox id={`isaret-${kimlik}-hazirim`} labelText="Hazırım" checked={isaret === 'hazirim'}
          onChange={(_, { checked }) => isaretle(b.kod, checked ? 'hazirim' : null, isaret)} />
        <Checkbox id={`isaret-${kimlik}-tekrar`} labelText="Tekrar" checked={isaret === 'tekrar'}
          onChange={(_, { checked }) => isaretle(b.kod, checked ? 'tekrar' : null, isaret)} />
      </fieldset>
      {hata?.kod === b.kod && (
        <InlineNotification kind="error" lowContrast role="alert" statusIconDescription="Hata" aria-label="Bildirimi kapat"
          title={hata.metin} onCloseButtonClick={hatayiKapat} />
      )}
    </div>
  )
}

/** Çıktı bloğu (K2, sıra sabit): kod, soru, MEB metni, Kitapta, ele alınanlar, ders kartı haftası, ödev/modül,
 *  işaret. Çıktının adı MEB metninin kendisidir (K1): başlık yalnız kodu taşır, metin bir kez, alıntıda yazılır.
 *  Başlık düzeyi çizilen yapıdan gelir — çerçeve başlığı varsa h5, yoksa h4 (U4: düzey sıçramaz). */
function CiktiBlogu({ b, m, kip, duzey, isaret, isaretle, hata, hatayiKapat }: {
  b: Blok; m: KilavuzModeli; kip: Kip; duzey: 4 | 5; isaret: IsaretDurumu; isaretle?: Isaretle
  hata?: IsaretHatasi | null; hatayiKapat?: () => void
}) {
  if (!b.senaryoda) {
    return <p id={ciktiKimligi(b.kod)} className="kilavuz-blok kilavuz-blok--soluk">{`${b.kod} ${b.kisa_ad} · ${m.senaryo}. senaryoda yok`}</p>
  }
  return (
    <div id={ciktiKimligi(b.kod)} className="kilavuz-blok" data-baslik={b.kod}>
      {/* İki dal açıkça yazılı: kapılar başlığı kaynakta görür. h4 S38'e girer (başlık düzeni), h5 girmez (B41, cümle
          düzeni); gizli önek yalnız ekran okuyucu içindir, harf büyüklüğü okunuşu değiştirmez. */}
      {duzey === 5
        ? <h5 className="kilavuz-blok__ust"><span className="cds--visually-hidden">Öğrenme çıktısı </span><span className="kilavuz-kod">{b.kod}</span></h5>
        : <h4 className="kilavuz-blok__ust"><span className="cds--visually-hidden">Öğrenme Çıktısı </span><span className="kilavuz-kod">{b.kod}</span></h4>}
      <p className="kilavuz-blok__soru">
        <span className="kilavuz-blok__sayi">{soruMetni(b, m.kip === 'olasi' ? m.senaryo : null)}</span>
        {b.her_senaryoda && <Tag type="gray" size="sm" className="kilavuz-blok__her">her senaryoda</Tag>}
      </p>
      <blockquote className="kilavuz-blok__meb">{`MEB: “${b.metin}”`}</blockquote>
      <p className="kilavuz-blok__etiket">Kitapta</p>
      {b.kitap_durumu === 'var' ? (
        // Kitapta ve "Bu bölümde ele alınanlar" tek iç içe liste (düzeltme 1): her yol bir satır, hemen altında o
        // konunun başlıkları. Liste düzenidir, başlık düzeyi değil.
        <ul className="kilavuz-blok__yollar">
          {b.kitapta.map((y, i) => (
            <li key={`${i}-${y.cerceve}-${y.konu}`} className="kilavuz-yol">
              <div className="kilavuz-yol__satir">
                {kip === 'ekran'
                  ? <CarbonLink href={y.baglanti} target="_blank" rel="noreferrer" renderIcon={Launch}><YolMetni y={y} /></CarbonLink>
                  : <span><YolMetni y={y} /></span>}
                <span className="kilavuz-sayfa-no"><span className="cds--visually-hidden"> · </span>{sayfaMetni(y.sayfa, y.son_sayfa)}</span>
              </div>
              {y.basliklar.length > 0 && (
                <>
                  <p className="kilavuz-yol__etiket">Bu bölümde ele alınanlar</p>
                  <ul className="kilavuz-basliklar">
                    {y.basliklar.map((h, j) => (
                      <li key={j}>
                        <span className="kilavuz-basliklar__tur">{BASLIK_TURU[h.tur]}</span>
                        <span className="kilavuz-basliklar__ad">{` ${baslikMetni(h)}`}</span>
                        <span className="kilavuz-sayfa-no"><span className="cds--visually-hidden"> · </span>{`s. ${h.sayfa}`}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="kilavuz-blok__yok">{b.kitap_durumu === 'bulunamadi' ? 'Kitapta karşılığı bulunamadı.' : 'Kitap bölümleri henüz eklenmedi.'}</p>
      )}
      {/* Karar: alan "ders kartında geçtiği hafta"dır; "işlendi" denmez, hafta yoksa "işlenmedi" de denmez. */}
      <p className="kilavuz-blok__baglam">{`Ders kartında geçtiği hafta: ${b.okulda.map(h => h.hafta).join(', ') || 'bulunamadı'}`}</p>
      {b.odevler.length > 0 && <p className="kilavuz-blok__baglam">{`Ödev: ${b.odevler.map(o => o.baslik).join(', ')}`}</p>}
      {b.moduller.length > 0 && (
        <p className="kilavuz-blok__baglam">
          {'Modül: '}
          {b.moduller.map((md, i) => (
            <span key={md.yol}>{i > 0 && ', '}{kip === 'ekran' ? <IcBaglanti href={md.yol} inline>{md.baslik}</IcBaglanti> : md.baslik}</span>
          ))}
        </p>
      )}
      <IsaretAlani b={b} kip={kip} isaret={isaret} isaretle={isaretle} hata={hata} hatayiKapat={hatayiKapat} />
    </div>
  )
}

/** Kapsam kılavuzu (spec §4): ekranda ve kâğıtta aynı bileşen, aynı sıra (K11). Kâğıt kipinde içindekiler eklenir,
 *  karşılaştırma tablosu ünite başına bölünür (Y5) ve bölümler adlı sayfa sınıflarını taşır (sayfa.css, D14). */
export default function KilavuzBelgesi({ model: m, kip, isaretler = {}, isaretle, isaretHatasi, hatayiKapat }: {
  model: KilavuzModeli
  kip: Kip
  isaretler?: Record<string, IsaretDurumu>
  isaretle?: Isaretle
  isaretHatasi?: IsaretHatasi | null
  hatayiKapat?: () => void
}) {
  const bloklar = m.uniteler.flatMap(u => u.cerceveler.flatMap(c => c.bloklar))
  const adi = (kod: string) => bloklar.find(b => b.kod === kod)?.kisa_ad ?? kod
  const kodlu = (kodlar: string[]) => kodlar.map(k => `${k} ${adi(k)}`).join('; ')
  // Duyurunun konusu MEB metninin kendisiyse metin ikinci kez yazılmaz; yalnız kod (metin blokta, K1).
  const ayni = (a: string, b: string) => a.trim().toLocaleLowerCase('tr') === b.trim().toLocaleLowerCase('tr')
  const karsilik = (konu: string, kodlar: string[]) => kodlar.map(k => (ayni(konu, adi(k)) ? k : `${k} ${adi(k)}`)).join('; ')
  const kalan = kalanGunMetni(m.durum.kalan_gun)
  // K8: seçilen ama duyurulmamış senaryo "bu senaryo" diye sunulmaz; öyle olduğu açıkça yazılır.
  const secilen = m.kip === 'olasi' && m.senaryo !== null
  const notlar = [
    ...(m.secilen_duyurulan_degil && m.duyurulan !== null ? [`Okul ${m.duyurulan}. senaryoyu duyurdu; bu kılavuz seçtiğin ${m.senaryo}. senaryoya göre.`] : []),
    ...(m.kip === 'kesin' && m.durum.uyari === 'kismen' ? ['Duyurudaki bazı konular bu senaryoda yok; Duyuru Doğrulaması bölümüne bak.'] : []),
    ...hazirlikUyarilari(m),
    ...(m.kip === 'ulke_geneli' && m.not ? [m.not] : []),
  ]
  // K8: olası kipte seçilen senaryonun sayıları o senaryoyla nitelenir ("3. senaryoda toplam 8 soru").
  const nitelik = m.kip === 'olasi' ? m.senaryo : null
  const toplam = m.ozet.toplam_soru !== null
    ? (nitelik !== null ? `${nitelik}. senaryoda toplam ${m.ozet.toplam_soru} soru` : m.ozet.toplam_soru)
    : (m.ozet.soru_araligi ? `senaryoya göre ${m.ozet.soru_araligi[0]}–${m.ozet.soru_araligi[1]}` : '–')
  const sahip = m.secenekler.isaret ? m.isaret_sahibi : null
  // Kâğıdın üst bilgi ve damga kaynağı (sayfa.css string-set): ilk bölümün (ebeveyn özeti, yoksa özet) ilk öğesi, görünmez.
  // Bölümlerin dışında dursaydı Paged.js onu adsız bir sayfaya koyar, kapaktan önce boş bir sayfa açılırdı (ölçüldü).
  const kagitBilgisi = kip === 'baski' && (
    <div className="kilavuz-kagit-bilgi" aria-hidden="true">
      <span className="kilavuz-kagit-bilgi__ust">{ustBilgi(m)}</span>
      <span className="kilavuz-kagit-bilgi__damga">{damgaMetni(m)}</span>
    </div>
  )
  return (
    <article className={`kilavuz-belge kilavuz-belge--${kip} ${subjectClass(m.ders)}`} lang="tr">
      {m.ebeveyn && (
        <section id="bolum-ebeveyn" className="kilavuz-ebeveyn" aria-labelledby="baslik-ebeveyn">
          {kagitBilgisi}
          <h2 id="baslik-ebeveyn" className="kilavuz-ebeveyn__baslik">{BOLUM.ebeveyn}</h2>
          <ul className="kilavuz-liste">{ebeveynCumleleri(m).map(c => <li key={c}>{c}</li>)}</ul>
          {m.ebeveyn.isaret_sahibi && <p className="kilavuz-ebeveyn__sahip">{`İşaretlerin sahibi: ${m.ebeveyn.isaret_sahibi}`}</p>}
          {/* K8: sayı taşımaz; "en çok N soru gelebilir" diye okunmasın. */}
          {m.ebeveyn.en_agir.length > 0 && <p>{`Soru ağırlığı en yüksek çıktılar: ${kodlu(m.ebeveyn.en_agir)}`}</p>}
        </section>
      )}
      <section id="bolum-ozet" className="kilavuz-ozet" aria-labelledby="baslik-ozet">
        {!m.ebeveyn && kagitBilgisi}
        <h2 id="baslik-ozet" className="kilavuz-baslik">{BOLUM.kilavuz}</h2>
        <p className="kilavuz-baslik__alt">{ustBilgi(m)}</p>
        {secilen && <p className="kilavuz-ozet__secim">{`Seçtiğin ${m.senaryo}. senaryo (duyurulmadı)`}</p>}
        <p className="kilavuz-ozet__zaman">{m.durum.tarih === null ? 'Tarihi henüz belli değil'
          : `${tarihMetni(m.durum.tarih)}${kalan ? ` · ${kalan}${m.durum.kalan_gun && m.durum.kalan_gun > 1 ? ' kaldı' : ''}` : ''}`}</p>
        <DurumGostergesi durum={m.durum} />
        <Uyarilar metinler={notlar} kip={kip} />
        <dl className="kilavuz-ozet__sayilar">
          <div className="kilavuz-ozet__sayi"><dt>Toplam soru</dt><dd>{toplam}</dd></div>
          <div className="kilavuz-ozet__sayi"><dt>{m.kip === 'olasi' ? 'Olası öğrenme çıktısı' : 'Öğrenme çıktısı'}</dt><dd>{m.ozet.cikti_sayisi}</dd></div>
          <div className="kilavuz-ozet__her"><dt>Her senaryoda</dt><dd>{kodlu(m.ozet.her_senaryoda) || '–'}</dd></div>
        </dl>
        {bloklar.some(b => b.senaryoda) && (
          <>
            <p className="kilavuz-etiket">Çıktılara göre soru</p>
            <ul className="kilavuz-ozet__dagilim">
              {bloklar.filter(b => b.senaryoda).map(b => (
                <li key={b.kod}>
                  <span className="kilavuz-kod">{b.kod}</span>
                  <span className="kilavuz-ozet__metin">{b.kisa_ad}</span>
                  <span className="kilavuz-ozet__soru">{soruMetni(b, nitelik)}</span>
                </li>
              ))}
            </ul>
          </>
        )}
        {kip === 'baski' && sahip && <p className="kilavuz-ozet__sahip">{`Hazırlık işaretlerinin sahibi: ${sahip}`}</p>}
        {/* Kâğıtta damga her sayfanın alt bilgisindedir (K12); içerikte ikinci kez basılmaz. */}
        {kip === 'ekran' && <p className="kilavuz-damga">{damgaMetni(m)}</p>}
      </section>
      {kip === 'baski' && (
        <nav id="bolum-icindekiler" className="kilavuz-icindekiler" aria-labelledby="baslik-icindekiler">
          <h3 id="baslik-icindekiler">{BOLUM.icindekiler}</h3>
          <ol>{bolumler(m).map(b => <li key={b.id}><a className="kilavuz-icindekiler__baglanti" href={`#${b.id}`}>{b.ad}</a></li>)}</ol>
        </nav>
      )}
      {m.matris.senaryolar.length > 0 && (
        <section id="bolum-karsilastirma" className="kilavuz-govde" aria-labelledby="baslik-karsilastirma">
          <h3 id="baslik-karsilastirma">{BOLUM.karsilastirma}</h3>
          {kip === 'ekran' ? (
            <Kaydirilabilir className="kilavuz-belge__tablo" etiket="Senaryo karşılaştırması tablosu">
              <KarsilastirmaTablosu matris={m.matris} vurgu={m.senaryo} kip="baski" vurguEtiketi={m.kip === 'kesin' ? 'duyurulan' : 'seçilen'} />
            </Kaydirilabilir>
          ) : (
            <KarsilastirmaTablosu matris={m.matris} vurgu={m.senaryo} kip="baski" uniteBasina
              vurguEtiketi={m.kip === 'kesin' ? 'duyurulan' : 'seçilen'} />
          )}
        </section>
      )}
      {m.uniteler.map((u, i) => (
        <section key={`${i}-${u.baslik}`} id={`bolum-unite-${i + 1}`} className="kilavuz-govde kilavuz-unite" aria-labelledby={`baslik-unite-${i + 1}`}>
          <h3 id={`baslik-unite-${i + 1}`}>{u.baslik}</h3>
          {u.cerceveler.map((c, j) => (
            <div key={`${j}-${c.baslik ?? ''}`} className="kilavuz-cerceve">
              {c.baslik && (
                <h4 className="kilavuz-cerceve__baslik">
                  {c.baslik}
                  {c.sayfa !== null && c.son_sayfa !== null && <span className="kilavuz-cerceve__sayfa">{` · ${sayfaMetni(c.sayfa, c.son_sayfa)}`}</span>}
                </h4>
              )}
              {c.bloklar.map(b => (
                <CiktiBlogu key={b.kod} b={b} m={m} kip={kip} duzey={c.baslik ? 5 : 4} isaret={isaretler[b.kod] ?? b.isaret}
                  isaretle={isaretle} hata={isaretHatasi} hatayiKapat={hatayiKapat} />
              ))}
            </div>
          ))}
        </section>
      ))}
      {m.dogrulama && (
        <section id="bolum-dogrulama" className="kilavuz-ek" aria-labelledby="baslik-dogrulama">
          <h3 id="baslik-dogrulama">{BOLUM.dogrulama}</h3>
          {/* Karar: doğrulama duyuruya göredir ve öyle etiketlenir. */}
          <p className="kilavuz-etiket">Duyuruya göre</p>
          <ul className="kilavuz-liste">
            {m.dogrulama.duyurulan_konular.map((d, i) => (
              <li key={`${i}-${d.konu}`}>{`«${d.konu}» → ${d.kodlar.length ? karsilik(d.konu, d.kodlar) : 'MEB tablosunda karşılığı bulunamadı'}`}</li>
            ))}
          </ul>
          {m.dogrulama.senaryo_disi.length > 0 && <p className="kilavuz-paragraf">{`Duyurulan senaryoda olmayan konular: ${m.dogrulama.senaryo_disi.join('; ')}`}</p>}
          {m.dogrulama.duyurunun_saymadigi.length > 0 && <p className="kilavuz-paragraf">{`Senaryoda olup duyurunun saymadığı çıktılar: ${kodlu(m.dogrulama.duyurunun_saymadigi)}`}</p>}
        </section>
      )}
      {m.plan && (
        <section id="bolum-plan" className="kilavuz-ek" aria-labelledby="baslik-plan">
          <h3 id="baslik-plan">{BOLUM.plan}</h3>
          <ol className="kilavuz-plan">
            {m.plan.gunler.map(g => (
              <li key={g.tarih}>
                <span className="kilavuz-plan__gun">{tarihMetni(g.tarih)}</span>
                {/* Genel tekrar günü önceki günlerin çıktılarını sayar: adları yukarıda, burada yalnız kodlar. */}
                <span>{g.genel_tekrar ? `Genel tekrar: ${g.ciktilar.join(', ')}` : kodlu(g.ciktilar)}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
      <section id="bolum-kaynaklar" className="kilavuz-ek" aria-labelledby="baslik-kaynaklar">
        <h3 id="baslik-kaynaklar">{BOLUM.kaynaklar}</h3>
        <ul className="kilavuz-liste">
          {m.kaynaklar.map(k => (
            <li key={k.adres}>{kip === 'ekran'
              ? <CarbonLink href={k.adres} target="_blank" rel="noreferrer" renderIcon={Launch}>{k.etiket}</CarbonLink>
              : `${k.etiket} — ${k.adres}`}</li>
          ))}
        </ul>
      </section>
    </article>
  )
}
