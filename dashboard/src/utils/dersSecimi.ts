/**
 * Dersler (B64, surface designs §4.3): a lesson in the timetable opens that course's content on the same page.
 * The two halves come from two endpoints and stay two components; a window event carries the course name
 * from the grid to the content tabs, which select it, scroll to it and move focus there.
 */
export const DERS_AC_OLAYI = 'tedy:ders-ac'

export function dersIceriginiAc(ders: string) {
  window.dispatchEvent(new CustomEvent<string>(DERS_AC_OLAYI, { detail: ders }))
}
