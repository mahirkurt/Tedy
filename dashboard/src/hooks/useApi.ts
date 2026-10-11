import { useState, useEffect, useCallback } from 'react'
import { apiHataTuru, type ApiHataTuru } from '../utils/apiHatasi'

const REFRESH_INTERVAL = 5 * 60 * 1000
const HOMEWORK_UPDATE_EVENT = 'tedy:homework-updated'

/** A first load shorter than this shows nothing; a skeleton that blinks for a
 *  frame is noise (yüzey tasarımları §2.4, talimatname S36, B48). The
 *  threshold is TEDY's, not Carbon's. */
export const YUKLEME_ESIGI_MS = 400

export function useApi<T>(endpoint: string, defaultValue: T): {
  data: T
  /** True until the first answer (or failure) arrives. */
  loading: boolean
  /** True only while still loading once YUKLEME_ESIGI_MS has passed: draw the
   *  skeleton on this, and nothing while `loading` is true without it. */
  iskelet: boolean
  /** Internal text, for logs and tests — never for the page (D4). */
  error: string | null
  /** B43: the failure's kind; a surface turns it into a sentence with `apiHataCumlesi`. */
  hataTuru: ApiHataTuru | null
  refresh: () => void
} {
  const [data, setData] = useState<T>(defaultValue)
  const [loading, setLoading] = useState(true)
  const [esikGecti, setEsikGecti] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hataTuru, setHataTuru] = useState<ApiHataTuru | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setEsikGecti(true), YUKLEME_ESIGI_MS)
    return () => clearTimeout(t)
  }, [])

  const fetchData = useCallback(async () => {
    try {
      let res: Response
      try {
        res = await fetch(endpoint, { credentials: 'include' })
      } catch {
        setHataTuru(apiHataTuru(null))
        throw new Error('Fetch error')
      }
      if (!res.ok) {
        setHataTuru(apiHataTuru(res.status))
        throw new Error(`HTTP ${res.status}`)
      }
      const text = await res.text()
      const ct = res.headers.get('content-type') || ''
      if (!ct.includes('application/json')) {
        setHataTuru(apiHataTuru(res.status, true))
        throw new Error(`Non-JSON response (HTTP ${res.status})`)
      }
      let json: T
      try {
        json = JSON.parse(text) as T
      } catch {
        setHataTuru(apiHataTuru(res.status, true))
        throw new Error(`Invalid JSON response (HTTP ${res.status})`)
      }
      setData(json)
      setError(null)
      setHataTuru(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fetch error')
    } finally {
      setLoading(false)
    }
  }, [endpoint])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, REFRESH_INTERVAL)
    const onHomeworkUpdate = () => {
      fetchData()
    }
    window.addEventListener(HOMEWORK_UPDATE_EVENT, onHomeworkUpdate)
    return () => {
      clearInterval(interval)
      window.removeEventListener(HOMEWORK_UPDATE_EVENT, onHomeworkUpdate)
    }
  }, [fetchData])

  return { data, loading, iskelet: loading && esikGecti, error, hataTuru, refresh: fetchData }
}
