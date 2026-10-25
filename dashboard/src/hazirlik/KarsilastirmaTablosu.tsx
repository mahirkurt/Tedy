import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Tag } from '@carbon/react'
import type { Matris } from './tipler'
import { tabloParcalari } from './belge'
import './Matris.scss'

/** Senaryo karşılaştırması (spec §3.2, taslak A): satırlar ünite gruplu çıktılar, sütunlar senaryolar; vurgulanan
 *  sütun duyurulan (ya da seçilen) senaryodur; sıfır "–"; toplam satırı. Ekranda satırın çıktısı bir düğmedir
 *  (ayrıntı paneli), kâğıtta düz metin (K11). Aynı bileşen kılavuzun içinde de kullanılır.
 *
 *  `uniteBasina` (Y5): Paged.js bölünen tabloda başlık satırını yinelemez; bu kipte tablo ünite başına ayrı tablolar
 *  olarak çizilir (`kilavuz-matris--unite`, her biri bölünmez, kendi başlık satırıyla), toplam satırı sonda tek
 *  başına. Baskı ve kılavuz kâğıdı bu kipi kullanır; ekranda tek tablo kalır. */
export default function KarsilastirmaTablosu({ matris, vurgu, kip, secili, sec, vurguEtiketi = 'duyurulan', uniteBasina = false }: {
  matris: Matris
  vurgu: number | null
  kip: 'ekran' | 'baski'
  secili?: string | null
  sec?: (kod: string, dugme: HTMLButtonElement) => void
  vurguEtiketi?: string
  uniteBasina?: boolean
}) {
  const sutun = (n: number) => (n === vurgu ? 'kilavuz-matris__vurgu' : undefined)
  const parcalar = tabloParcalari(matris, uniteBasina)
  return (
    <>
      {parcalar.map(p => {
        const ad = p.gruplar.length === 1 ? p.gruplar[0].baslik : 'toplam'
        return (
          <Table key={ad} size="md" className={`kilavuz-matris${uniteBasina ? ' kilavuz-matris--unite' : ''}`}
            aria-label={uniteBasina ? `Senaryo karşılaştırması · ${ad}` : 'Senaryo karşılaştırması'}>
            <TableHead>
              <TableRow>
                <TableHeader scope="col">Öğrenme çıktısı</TableHeader>
                {matris.senaryolar.map(n => (
                  <TableHeader key={n} scope="col" className={sutun(n)}>{n === vurgu ? `S${n} · ${vurguEtiketi}` : `S${n}`}</TableHeader>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {p.gruplar.map(g => [
                <TableRow key={g.baslik} className="kilavuz-matris__grup">
                  {/* Grup satırı başlık hücresi değil: th colgroup tabloyu "karmaşık" yapar, IBM her hücre için headers ister. */}
                  <TableCell colSpan={matris.senaryolar.length + 1}>{g.baslik}</TableCell>
                </TableRow>,
                ...g.satirlar.map(s => (
                  <TableRow key={s.kod} className={s.kod === secili ? 'kilavuz-matris__secili' : undefined}>
                    <th scope="row" className="kilavuz-matris__cikti">
                      {kip === 'ekran' && sec ? (
                        // Yerel düğme: Carbon ghost düğmesinin mavisi tablo hücresinin zemininde AA kontrastı tutmuyor (ölçüldü, axe).
                        <button type="button" className="kilavuz-matris__dugme" aria-expanded={s.kod === secili}
                          onClick={e => sec(s.kod, e.currentTarget)}>
                          <span className="kilavuz-kod">{s.kod}</span> {s.kisa_ad}
                        </button>
                      ) : (
                        <span><span className="kilavuz-kod">{s.kod}</span> {s.kisa_ad}</span>
                      )}
                      {s.her_senaryoda && <Tag type="gray" size="sm" className="kilavuz-matris__her">her senaryoda</Tag>}
                    </th>
                    {matris.senaryolar.map(n => {
                      const sayi = s.sayilar[String(n)] ?? 0
                      return (
                        <TableCell key={n} className={sutun(n)}>
                          {sayi > 0 ? sayi : <><span aria-hidden="true">–</span><span className="cds--visually-hidden">soru yok</span></>}
                        </TableCell>
                      )
                    })}
                  </TableRow>
                )),
              ])}
              {p.toplam && (
                <TableRow className="kilavuz-matris__toplam">
                  <th scope="row">Toplam soru</th>
                  {matris.senaryolar.map(n => <TableCell key={n} className={sutun(n)}>{matris.toplamlar[String(n)]}</TableCell>)}
                </TableRow>
              )}
            </TableBody>
          </Table>
        )
      })}
    </>
  )
}
