// The three ways TEDY is allowed to show time (design principles §2.1).
// Anything else is a fourth way, and a fourth way is how two durations stop
// being comparable.

const pad = (n: number) => String(n).padStart(2, '0')

/** A moment: "15:45". */
export function clock(minutes: number): string {
  return `${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}`
}

/** A resource: "3 saat 20 dakikan var". Never a countdown to a deadline. */
export function describeRemaining(minutes: number): string {
  if (minutes <= 0) return 'Bugünlük bu kadar'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m} dakikan var`
  if (m === 0) return `${h} saatin var`
  return `${h} saat ${m} dakikan var`
}

/** A distance: "10 gün sonra", "bugün". */
export function describeDaysAhead(target: Date, now: number = Date.now()): string {
  const days = Math.ceil((target.getTime() - now) / 86_400_000)
  if (days <= 0) return 'bugün'
  if (days === 1) return 'yarın'
  return `${days} gün sonra`
}
