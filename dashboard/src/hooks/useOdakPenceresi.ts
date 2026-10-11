import { useMemo } from 'react'
import { useApi } from './useApi'
import { pencereCoz, type OdakPenceresi } from '../utils/bugun'

/** The household's focus window (talimatname B29): read from
 *  `/api/odak-penceresi`, today's values until it arrives or when it cannot be
 *  read. `varsayilan` says the household has not set one. */
export function useOdakPenceresi(): {
  pencere: OdakPenceresi
  varsayilan: boolean
  loading: boolean
  iskelet: boolean
  error: string | null
  refresh: () => void
} {
  const { data, loading, iskelet, error, refresh } = useApi<unknown>('/api/odak-penceresi', null)
  const pencere = useMemo(() => pencereCoz(data), [data])
  const varsayilan = !data || typeof data !== 'object' || (data as { varsayilan?: unknown }).varsayilan !== false
  return { pencere, varsayilan, loading, iskelet, error, refresh }
}
