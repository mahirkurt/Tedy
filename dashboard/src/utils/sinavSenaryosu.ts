import type { SinavSenaryosu } from '../types'

export interface SenaryoGorunumu {
  ikon: 'onay' | 'uyari' | null
  cumleler: string[]
  /** Duyurunun kendi cümlesi: "Duyuru: «…»" (yalnız doğrulandı, kısmen ve senaryo yok durumlarında). */
  duyuru: string | null
  satirlar: { metin: string; duyuruda: boolean }[]
  dugme: string | null
  kaynak: string
}

/** [3] → "3.", [3, 4] → "3. ve 4.", [2, 3, 4] → "2., 3. ve 4." */
export function siraListesi(sayilar: number[]): string {
  const p = sayilar.map(s => `${s}.`)
  return p.length <= 1 ? (p[0] ?? '') : `${p.slice(0, -1).join(', ')} ve ${p.at(-1)}`
}

function mebTarihi(iso: string): string {
  const [y, a, g] = iso.slice(0, 10).split('-')
  return `MEB, ${g}.${a}.${y}`
}

/** Kartın "MEB konu-soru dağılımı" bölümü, bloktan (spec 2026-10-19 §5). Saf: test edilir. */
export function senaryoGorunumu(s: SinavSenaryosu): SenaryoGorunumu {
  const cumleler: string[] = []
  let ikon: SenaryoGorunumu['ikon'] = null
  let dugme: string | null = null
  if (s.durum === 'dogrulandi' || s.durum === 'kismen') {
    const ic = s.eslesen_konu_sayisi - s.senaryo_disi_konular.length
    const bas = s.anilan.length > 1
      ? `Duyuru ${siraListesi(s.anilan)} senaryo diyor; ${s.senaryo}. senaryo MEB tablosunda var: ${s.toplam} soru.`
      : `Duyurudaki ${s.senaryo}. senaryo MEB tablosunda var: ${s.toplam} soru.`
    cumleler.push(ic > 0 ? `${bas} Duyurudaki ${ic} konu bu senaryoda.` : bas)
    if (s.durum === 'kismen') cumleler.push(`Şu konu ${s.senaryo}. senaryoda yok: ${s.senaryo_disi_konular.join('; ')}.`)
    ikon = s.durum === 'kismen' ? 'uyari' : 'onay'
    dugme = `Senaryonun ${s.dagilim.length} çıktısını göster`
  } else if (s.durum === 'senaryo_yok') {
    ikon = 'uyari'
    cumleler.push(`Duyuru ${siraListesi(s.anilan)} senaryo diyor; MEB tablosunda bu sınav için 1–${s.senaryo_sayisi} var.`)
  } else if (s.durum === 'ulke_geneli') {
    cumleler.push('Bu sınav ülke genelinde ortak yapılır; senaryo yok.')
  } else {
    cumleler.push(`Duyuruda senaryo belirtilmedi · MEB tablosunda ${s.senaryo_sayisi} senaryo var.`)
    if (s.adaylar.length > 0) {
      const ek = s.adaylar.length > 1 ? 'senaryolarla' : 'senaryoyla'
      cumleler.push(`Duyurudaki konular ${siraListesi(s.adaylar)} ${ek} uyumlu (TEDY’nin tahmini).`)
    }
  }
  if (s.eslesmeyen_konular.length > 0) {
    cumleler.push(`MEB tablosunda karşılığı bulunamayan konu: ${s.eslesmeyen_konular.join('; ')}.`)
  }
  // "Ağırlıklı" gibi nüans kaybolmasın (spec §3.2/§10): öğretmenin sözü aynen, tırnaklı.
  const sozu = s.cumle?.trim()
  const duyuru = sozu && (s.durum === 'dogrulandi' || s.durum === 'kismen' || s.durum === 'senaryo_yok')
    ? `Duyuru: «${sozu}»` : null
  return {
    ikon, cumleler, duyuru, dugme, kaynak: mebTarihi(s.meb_guncelleme),
    satirlar: s.dagilim.map(d => ({ metin: `${d.soru} soru · ${d.kod} ${d.metin}`, duyuruda: d.duyuruda })),
  }
}
