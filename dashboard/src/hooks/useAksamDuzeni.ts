import { useMemo } from 'react'
import { useApi } from './useApi'
import { duzenOku, VARSAYILAN_DUZEN, type AksamDuzeni } from '../utils/bugun'

export interface AileUyesi { email: string; ad: string }

/** The household's evening (talimatname B29, spec 2026-10-19): read from
 *  `/api/aksam-duzeni`, the family's defaults until it arrives or when it
 *  cannot be read. `varsayilan` says the household has not set one;
 *  `aileUyeleri` is who can be told (the server sends that roster only to a
 *  signed-in family member). `okundu` is true once a well-formed evening came
 *  from the server — only then does Profil show a form, so the defaults never
 *  pass for the real setting; `okunamadi` says the latest read failed, and
 *  saving waits until a read succeeds (R28 I3). */
export function useAksamDuzeni(): {
  duzen: AksamDuzeni
  varsayilan: boolean
  aileUyeleri: AileUyesi[]
  okundu: boolean
  okunamadi: boolean
  loading: boolean
  iskelet: boolean
  error: string | null
  refresh: () => void
} {
  const { data, loading, iskelet, error, refresh } = useApi<unknown>('/api/aksam-duzeni', null)
  const okunan = useMemo(() => duzenOku(data), [data])
  const duzen = okunan ?? VARSAYILAN_DUZEN
  const varsayilan = !data || typeof data !== 'object' || (data as { varsayilan?: unknown }).varsayilan !== false
  const aileUyeleri = useMemo(() => {
    const ham = data && typeof data === 'object' ? (data as { aile_uyeleri?: unknown }).aile_uyeleri : null
    if (!Array.isArray(ham)) return []
    return ham.flatMap((u): AileUyesi[] => {
      const e = u && typeof u === 'object' ? (u as { email?: unknown; ad?: unknown }) : null
      return e && typeof e.email === 'string' ? [{ email: e.email, ad: typeof e.ad === 'string' ? e.ad : e.email }] : []
    })
  }, [data])
  return {
    duzen, varsayilan, aileUyeleri, okundu: okunan !== null, okunamadi: !loading && (error !== null || okunan === null),
    loading, iskelet, error, refresh,
  }
}
