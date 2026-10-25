import { Checkbox } from '@carbon/icons-react'

// Yoklama belgesi (spec §5.4): gerçek Fen taslağı — özet, içindekiler, uzun karşılaştırma tablosu ve iki ünitenin
// çıktı blokları. Amaç sayfalamayı ölçmek: tablo bölünmesi, (devam), yetim başlık, target-counter, yazı tipi gömme.
// ☐ karakteri Plex'te yok: işaret kutusu Carbon ikonu (SVG) olarak basılır (K11, Y1).
const UST = 'Fen Bilimleri · 1. yazılı · 2. senaryo'
const ZAMAN = '3 Kasım Salı · 9 gün kaldı · Kesin: 2. senaryo · 7 soru'
const DAMGA = 'TEDY · MEB tablosu 10.09.2026 · kitap 2026-2027 · üretim 25.10.2026'
const BOLUM = { kilavuz: 'Kapsam Kılavuzu', karsilastirma: 'Senaryo Karşılaştırması', kaynaklar: 'Kaynaklar' }
const UNITELER = ['1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim']
const KAYNAKLAR = ['MEB ÖDSGM · 1. Dönem Konu Soru Dağılım Tabloları (2026-2027)', 'Fen Bilimleri 7 (1. Kitap) (EBA PDF)']
const SATIRLAR: [string, string, string, number[], string][] = [
  [UNITELER[0], 'FB.7.1.1', 'Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme', [2, 2, 2, 0], 'Uzay Teknolojileri; Teknoloji ile Uzay Araştırmaları Arasındaki İlişki · s. 16–33'],
  [UNITELER[0], 'FB.7.1.3', 'Uzay araştırmalarının yol açabileceği problemleri çözebilme', [0, 1, 1, 1], 'Teknoloji ile Uzay Araştırmaları Arasındaki İlişki · s. 24–33'],
  [UNITELER[0], 'FB.7.1.4', 'Yıldızların yaşamını açıklayarak yapılandırabilme', [1, 0, 1, 1], 'Yıldız Oluşumu · s. 35–49'],
  [UNITELER[0], 'FB.7.1.5', 'Yıldız, galaksi ve evren kavramlarını açıklayarak yapılandırabilme', [1, 1, 0, 1], 'Yıldız Oluşumu · s. 35–49'],
  [UNITELER[1], 'FB.7.2.1', 'Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme', [3, 3, 2, 2], 'Fiziksel Anlamda İş · s. 60–63'],
  [UNITELER[1], 'FB.7.2.2', 'Enerji çeşitlerinden kinetik ve potansiyel enerjiyi karşılaştırabilme', [2, 0, 2, 1], 'Enerji ve Enerji Çeşitleri · s. 64–70'],
]
type B = [string, string, number]
const BLOKLAR: { unite: string; cerceve: string; baslik: string; meb: string; yol: string; basliklar: B[] }[] = [
  { unite: UNITELER[0], cerceve: '1. Türkiye ve Uzay Araştırmaları', baslik: 'FB.7.1.1 Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme · 2 soru',
    meb: 'MEB: “Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme”',
    yol: 'Kitapta: Fen Bilimleri 7 (1. Kitap) › 1. Ünite › 1. Türkiye ve Uzay Araştırmaları › Uzay Teknolojileri · s. 16–24',
    basliklar: [['Etkinlik', 'Keşif Noktası: Uzay Teknolojileri', 17], ['Kontrol', 'Kontrol Noktası', 19], ['Konu', 'Türkiye’nin Yapay Uyduları', 20],
      ['Konu', 'Teleskop Çeşitleri', 22], ['Konu', 'A- Uzay Teleskopları', 22], ['Konu', 'B- Yer Tabanlı Teleskoplar', 23], ['Bağlantı', 'Bağlantı Noktası', 23], ['Kontrol', 'Kontrol Noktası', 24]] },
  { unite: UNITELER[0], cerceve: '1. Türkiye ve Uzay Araştırmaları', baslik: 'FB.7.1.3 Teknoloji ile Uzay Araştırmaları Arasındaki İlişki · 1 soru',
    meb: 'MEB: “Uzay araştırmalarının yol açabileceği problemleri çözebilme”',
    yol: 'Kitapta: Fen Bilimleri 7 (1. Kitap) › 1. Ünite › 1. Türkiye ve Uzay Araştırmaları › Teknoloji ile Uzay Araştırmaları Arasındaki İlişki · s. 24–33',
    basliklar: [['Bağlantı', 'Bağlantı Noktası', 25], ['Bağlantı', 'Bağlantı Noktası', 26], ['Tanım', 'Astronomi (Gök bilimi)', 26], ['Tanım', 'Astronot', 26],
      ['Etkinlik', 'Performans Görevi: Uzay Gözlem Araçları Modeli — Uzay gözlem araçları ile ilgili bilimsel model oluşturma', 29], ['Konu', 'Uzay Kirliliği', 30],
      ['Etkinlik', 'Performans Görevi: Uzayda Neler Oluyor? — Uzay araştırmalarının yol açabileceği problemlerin çözümüne yönelik rapor oluşturma', 31], ['Özet', 'Neler Öğrendik?', 33]] },
  { unite: UNITELER[0], cerceve: '2. Uzayda Neler Var?', baslik: 'FB.7.1.5 Yıldız Oluşumu · 1 soru',
    meb: 'MEB: “Yıldız, galaksi ve evren kavramlarını açıklayarak yapılandırabilme”',
    yol: 'Kitapta: Fen Bilimleri 7 (1. Kitap) › 1. Ünite › 2. Uzayda Neler Var? › Yıldız Oluşumu · s. 35–49',
    basliklar: [['Etkinlik', 'Keşif Noktası: Yıldızların Oluşumunu Araştıralım', 35], ['Etkinlik', 'Etkinlik Noktası-1 — Yıldızların yaşam sürecine ilişkin kavramlar arasındaki ilişkileri açıklama', 36],
      ['Etkinlik', 'Performans Görevi: Yıldızların Yaşam Süreci Posterim', 37], ['Etkinlik', 'Etkinlik Noktası-2 — Yıldız, galaksi ve evren kavramlarını açıklayarak yapılandırma', 46],
      ['Kontrol', 'Kontrol Noktası', 47], ['Konu', 'Galaksiler', 48], ['Kontrol', 'Kontrol Noktası', 48], ['Özet', 'Neler Öğrendik?', 49]] },
  { unite: UNITELER[1], cerceve: '1. Kuvvet, İş ve Enerji İlişkisi', baslik: 'FB.7.2.1 Fiziksel Anlamda İş · 3 soru',
    meb: 'MEB: “Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme”',
    yol: 'Kitapta: Fen Bilimleri 7 (1. Kitap) › 2. Ünite › 1. Kuvvet, İş ve Enerji İlişkisi › Fiziksel Anlamda İş · s. 60–63',
    basliklar: [['Etkinlik', 'Etkinlik Noktası-1 — Fiziksel anlamda yapılan işin niteliklerini tanımlama', 60],
      ['Etkinlik', 'Etkinlik Noktası-2 — Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme', 60], ['Bağlantı', 'Bağlantı Noktası', 62], ['Kontrol', 'Kontrol Noktası', 63]] },
]

export default function YoklamaBelgesi() {
  return (
    <article className="kilavuz-belge" lang="tr">
      <section className="kilavuz-ozet" id="bolum-ozet">
        <h1 className="kilavuz-baslik">{BOLUM.kilavuz}</h1>
        <p className="kilavuz-baslik__alt">{UST}</p>
        <p>{ZAMAN}</p>
        <p className="kilavuz-damga">{DAMGA}</p>
      </section>
      <nav className="kilavuz-icindekiler" id="bolum-icindekiler" aria-labelledby="yoklama-icindekiler">
        <h2 id="yoklama-icindekiler">İçindekiler</h2>
        <ol>
          <li><a className="kilavuz-icindekiler__baglanti" href="#bolum-karsilastirma">{BOLUM.karsilastirma}</a></li>
          {UNITELER.map((u, i) => <li key={u}><a className="kilavuz-icindekiler__baglanti" href={`#bolum-unite-${i + 1}`}>{u}</a></li>)}
          <li><a className="kilavuz-icindekiler__baglanti" href="#bolum-kaynaklar">{BOLUM.kaynaklar}</a></li>
        </ol>
      </nav>
      <section className="kilavuz-govde" id="bolum-karsilastirma">
        <h2>{BOLUM.karsilastirma}</h2>
        <table className="kilavuz-matris">
          <thead><tr><th scope="col">Öğrenme çıktısı</th><th scope="col">S1</th><th scope="col">S2 · duyurulan</th><th scope="col">S3</th><th scope="col">S4</th><th scope="col">Kitapta</th></tr></thead>
          <tbody>
            {[0, 1, 2, 3].flatMap(tur => SATIRLAR.map(([, kod, metin, sayilar, yol]) => (
              <tr key={`${tur}-${kod}`}>
                <th scope="row">{kod} {metin}</th>
                {sayilar.map((s, i) => <td key={i}>{s || '–'}</td>)}
                <td>{yol}</td>
              </tr>
            )))}
          </tbody>
        </table>
      </section>
      {UNITELER.map((unite, ui) => (
        <section className="kilavuz-govde" key={unite} id={`bolum-unite-${ui + 1}`}>
          <h2>{unite}</h2>
          {BLOKLAR.filter(b => b.unite === unite).map(b => (
            <div key={b.baslik} className="kilavuz-blok" data-baslik={b.baslik}>
              <h3 className="kilavuz-blok__ust">{b.cerceve}</h3>
              <h4>{b.baslik}</h4>
              <p>{b.meb}</p>
              <p>{b.yol}</p>
              <p>Bu bölümde ele alınanlar</p>
              <ul className="kilavuz-basliklar">
                {b.basliklar.map(([tur, ad, s], i) => <li key={i}>{`${tur} · ${ad} · s. ${s}`}</li>)}
              </ul>
              <p><Checkbox size={16} aria-hidden="true" /> Hazırım <Checkbox size={16} aria-hidden="true" /> Tekrar</p>
            </div>
          ))}
        </section>
      ))}
      <section className="kilavuz-ek" id="bolum-kaynaklar">
        <h2>{BOLUM.kaynaklar}</h2>
        {KAYNAKLAR.map(k => <p key={k}>{k}</p>)}
      </section>
    </article>
  )
}
