// What the Day Strip draws: the rest of today cut into the parts a
// twelve-year-old already has words for — sabah, okul, yol, ödev zamanı, akşam.
//
// Until 2026-10-19 the strip drew an unnamed grey band (the focus window), a
// blue line (the next thing's anchor) and eight hour ticks; the family read it
// as "anlaşılmaz ve kompleks". A part with a name says what the band meant, so
// the ticks and the separate anchor line are gone: the "ödev zamanı" part is
// where the card's work is anchored (İ3), drawn to scale (İ2).

export type ParcaTuru = 'sabah' | 'okul' | 'yol' | 'odev' | 'aksam'

export interface GunParcasi {
  tur: ParcaTuru
  /** Minutes since midnight, already clipped to [now, bedtime]. */
  bas: number
  bit: number
}

export const PARCA_ADI: Record<ParcaTuru, string> = {
  sabah: 'Sabah',
  okul: 'Okul',
  yol: 'Yol',
  odev: 'Ödev zamanı',
  aksam: 'Akşam',
}

export interface GunGirdisi {
  simdi: number
  yatma: number
  /** When Işık is ready for homework: the "ödev zamanı" part starts here. */
  odeveHazir: number
  /** Where the hard work ends: after it, no hard work is suggested (§1.2). */
  zorIsSonu: number
  /** Today's school, or null on a day without school. */
  okul: { bas: number; bit: number } | null
}

/** The configured homework slot, unclipped — what the caption names. On a day
 *  without school it starts at the same hour (spec 2026-10-19, R2). */
export function odevAraligi(g: GunGirdisi): { bas: number; bit: number } | null {
  const bas = Math.max(g.odeveHazir, g.okul?.bit ?? 0)
  const bit = Math.min(g.zorIsSonu, g.yatma)
  return bit > bas ? { bas, bit } : null
}

/** The parts still ahead, in order, each clipped to [now, bedtime]. */
export function gunParcalari(g: GunGirdisi): GunParcasi[] {
  const odev = odevAraligi(g)
  const sabahSonu = g.okul ? g.okul.bas : (odev?.bas ?? g.odeveHazir)
  const aksamBasi = Math.max(odev?.bit ?? 0, g.okul?.bit ?? 0, g.zorIsSonu)

  const ham: GunParcasi[] = [{ tur: 'sabah', bas: 0, bit: sabahSonu }]
  if (g.okul) ham.push({ tur: 'okul', bas: g.okul.bas, bit: g.okul.bit })
  // The way home and the snack: from the last bell to the hour homework starts.
  if (g.okul && odev && odev.bas > g.okul.bit) ham.push({ tur: 'yol', bas: g.okul.bit, bit: odev.bas })
  if (odev) ham.push({ tur: 'odev', bas: odev.bas, bit: odev.bit })
  ham.push({ tur: 'aksam', bas: aksamBasi, bit: g.yatma })

  return ham
    .map(p => ({ ...p, bas: Math.max(p.bas, g.simdi), bit: Math.min(p.bit, g.yatma) }))
    .filter(p => p.bit > p.bas)
}
