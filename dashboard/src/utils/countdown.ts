export interface CountdownResult {
  days: number
  hours: number
  minutes: number
  text: string
  urgency: 'expired' | 'urgent' | 'soon' | 'normal'
}

export function getCountdown(deadline: Date | null): CountdownResult {
  if (!deadline) return { days: 0, hours: 0, minutes: 0, text: '-', urgency: 'normal' }

  const now = new Date()
  const diff = deadline.getTime() - now.getTime()

  if (diff <= 0) {
    return { days: 0, hours: 0, minutes: 0, text: 'Süresi doldu', urgency: 'expired' }
  }

  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

  let text: string
  if (days > 0) text = `${days}g ${hours}s`
  else if (hours > 0) text = `${hours}s ${minutes}dk`
  else text = `${minutes}dk`

  let urgency: CountdownResult['urgency']
  if (days === 0 && hours < 24) urgency = 'urgent'
  else if (days < 3) urgency = 'soon'
  else urgency = 'normal'

  return { days, hours, minutes, text, urgency }
}
