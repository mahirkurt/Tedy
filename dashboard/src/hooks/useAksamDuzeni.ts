import { useMemo } from 'react'
import { useApi } from './useApi'
import { duzenCoz, type AksamDuzeni } from '../utils/bugun'

export interface AileUyesi { email: string; ad: string }

/** The household's evening (talimatname B29, spec 2026-10-19): read from
 *  `/api/aksam-duzeni`, the family's defaults until it arrives or when it
 *  cannot be read. `varsayilan` says the household has not set one;
 *  `aileUyeleri` is who can be told. */
export function useAksamDuzeni(): {
  duzen: AksamDuzeni
  varsayilan: boolean
  aileUyeleri: AileUyesi[]
  loading: boolean
  iskelet: boolean
  error: string | null
  refresh: () => void
} {
  const { data, loading, iskelet, error, refresh } = useApi<unknown>('/api/aksam-duzeni', null)
  const duzen = useMemo(() => duzenCoz(data), [data])
  const varsayilan = !data || typeof data !== 'object' || (data as { varsayilan?: unknown }).varsayilan !== false
  const aileUyeleri = useMemo(() => {
    const ham = data && typeof data === 'object' ? (data as { aile_uyeleri?: unknown }).aile_uyeleri : null
    if (!Array.isArray(ham)) return []
    return ham.flatMap((u): AileUyesi[] => {
      const e = u && typeof u === 'object' ? (u as { email?: unknown; ad?: unknown }) : null
      return e && typeof e.email === 'string' ? [{ email: e.email, ad: typeof e.ad === 'string' ? e.ad : e.email }] : []
    })
  }, [data])
  return { duzen, varsayilan, aileUyeleri, loading, iskelet, error, refresh }
}
