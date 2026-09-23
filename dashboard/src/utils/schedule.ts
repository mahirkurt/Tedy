/** Reading the portal's weekly grid.
 *
 *  The grid is not one table. The portal lays the week out as two blocks side
 *  by side, each with its own time column, because the bells differ: measured
 *  2026-09-23, Monday's second lesson starts at 08:55 and Friday's at 09:00,
 *  and the gap grows to ten minutes by the fifth. A day's times therefore have
 *  to be read from the time column belonging to that day's block, not from
 *  column 0 — using column 0 for Friday puts every lesson five to ten minutes
 *  early, which is worse than showing nothing (D3).
 *
 *  `schedule.headers` is empty in the scraped data, so the day names live in
 *  row 0, and the blank cells in that row are exactly the time columns.
 */

/** Uppercase for matching, with the dotted İ folded onto I.
 *
 *  Not `toLocaleUpperCase('tr')`: that maps "Pazartesi" to "PAZARTESİ" with a
 *  dotted İ while the portal writes a dotless one, so Monday — the one day
 *  with an i — silently failed to match. */
export const normDay = (s: string) => (s || '').trim().toUpperCase().replace(/İ/g, 'I')

export interface DayColumn {
  day: string
  /** Index of the day's lesson column in each row. */
  idx: number
  /** Index of the time column governing that day. */
  timeIdx: number
}

/** The time column governing a day: the nearest blank header at or before it.
 *  Falls back to 0 for a single-block grid, which is what the old code assumed. */
export function timeColumnFor(headerRow: string[], dayIdx: number): number {
  for (let i = dayIdx - 1; i >= 0; i--) {
    if (!(headerRow[i] || '').trim()) return i
  }
  return 0
}

/** Locates each requested day in the header row, paired with its own time
 *  column. Days the grid does not publish are dropped; the pairing means a
 *  missing day cannot shift the days after it. */
export function dayColumns(headerRow: string[], days: readonly string[]): DayColumn[] {
  return days
    .map(day => {
      const idx = headerRow.findIndex(h => normDay(h) === normDay(day))
      return { day, idx, timeIdx: timeColumnFor(headerRow, idx) }
    })
    .filter(d => d.idx >= 0)
}
