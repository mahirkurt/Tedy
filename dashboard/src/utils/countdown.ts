export interface CountdownResult {
  days: number
  hours: number
  minutes: number
  text: string
  urgency: 'expired' | 'critical' | 'urgent' | 'soon' | 'normal'
  fraction: number
}

/**
 * `nowMs` lets a caller pin the reference time to a value it already tracks in
 * state, so memoised countdowns have a real dependency to react to instead of
 * an opaque tick counter.
 */
export function getCountdown(deadline: Date | null, nowMs: number = Date.now()): CountdownResult {
  if (!deadline) return { days: 0, hours: 0, minutes: 0, text: '-', urgency: 'normal', fraction: 0 }

  const diff = deadline.getTime() - nowMs

  if (diff <= 0) {
    return { days: 0, hours: 0, minutes: 0, text: 'Süresi doldu', urgency: 'expired', fraction: 1 }
  }

  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

  let text: string
  if (days > 0) text = `${days}g ${hours}s`
  else if (hours > 0) text = `${hours}s ${minutes}dk`
  else text = `${minutes}dk`

  let urgency: CountdownResult['urgency']
  if (days === 0 && hours < 6) urgency = 'critical'
  else if (days === 0 && hours < 24) urgency = 'urgent'
  else if (days < 3) urgency = 'soon'
  else urgency = 'normal'

  // fraction: how much of a 7-day window has elapsed (0.0 = just assigned, 1.0 = deadline)
  const WINDOW_MS = 7 * 24 * 60 * 60 * 1000
  const fraction = Math.min(1, Math.max(0, 1 - diff / WINDOW_MS))

  return { days, hours, minutes, text, urgency, fraction }
}

export function getExamCountdown(examDate: Date | null, nowMs: number = Date.now()): CountdownResult {
  if (!examDate) return { days: 0, hours: 0, minutes: 0, text: '-', urgency: 'normal', fraction: 0 }

  const diff = examDate.getTime() - nowMs

  if (diff <= 0) {
    return { days: 0, hours: 0, minutes: 0, text: 'Geçti', urgency: 'expired', fraction: 1 }
  }

  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

  let text: string
  if (days > 0) text = `${days}g ${hours}s`
  else if (hours > 0) text = `${hours}s ${minutes}dk`
  else text = `${minutes}dk`

  let urgency: CountdownResult['urgency']
  if (days < 2) urgency = 'critical'
  else if (days < 5) urgency = 'urgent'
  else if (days < 14) urgency = 'soon'
  else urgency = 'normal'

  const WINDOW_MS = 30 * 24 * 60 * 60 * 1000
  const fraction = Math.min(1, Math.max(0, 1 - diff / WINDOW_MS))

  return { days, hours, minutes, text, urgency, fraction }
}
