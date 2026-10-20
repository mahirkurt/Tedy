import { useCallback, useEffect, useRef, useState } from 'react'
import { planCoz, planHataCumlesi, type PlanHatasi, type PlanYaniti } from '../utils/aksamPlani'

/** Fired after a touch changed tonight's plan, so every reader of it reloads. */
export const PLAN_OLAYI = 'tedy:plan-guncellendi'
const ODEV_OLAYI = 'tedy:homework-updated'
// The card's states turn with the clock (17:00, the end of a break), so the plan is read again each minute.
const YENILEME_MS = 60 * 1000

export type PlanSonucu = { ok: true } | { ok: false; hata: PlanHatasi }

/**
 * Tonight's study plan (spec 2026-10-19 §6.7), read from `/api/plan/bugun`.
 *
 * The flag off answers 404 `{"kapali": true}`: that is not a failure, it is "no
 * plan card", and Bugün keeps its old flow (`kapali`). Bugün does not wait for this
 * read and draws no skeleton for it: the page paints, and the card takes its slot when the plan
 * arrives (R17). Any other failure is `hata` — the page says it could not read everything, never
 * the HTTP text.
 * Every touch answers with the whole plan, which replaces the one on screen.
 */
export function useAksamPlani(): {
  plan: PlanYaniti | null
  /** The flag is off: no card at all. */
  kapali: boolean
  hata: boolean
  basla: (id: string) => Promise<PlanSonucu>
  bitti: (id: string, tamamlandi?: boolean) => Promise<PlanSonucu>
  simdiDegil: (id: string) => Promise<PlanSonucu>
  sureDuzelt: (anahtar: string, dk: number) => Promise<PlanSonucu>
  aksamYok: (aktif: boolean) => Promise<PlanSonucu>
} {
  const [plan, setPlan] = useState<PlanYaniti | null>(null)
  const [kapali, setKapali] = useState(false)
  const [hata, setHata] = useState(false)
  // A read that started before a touch must not overwrite the plan the touch returned.
  const surum = useRef(0)

  const oku = useCallback(async () => {
    const benim = ++surum.current
    try {
      const res = await fetch('/api/plan/bugun', { credentials: 'include' })
      const govde: unknown = (res.headers.get('content-type') || '').includes('application/json')
        ? await res.json().catch(() => null) : null
      if (benim !== surum.current) return
      // The flag answers 404 `{"kapali": true}`; any 404 (a proxy's page, an older server without the
      // route) means the same thing for the page — no plan card — and is not a failure.
      if (res.status === 404) {
        setKapali(true)
        setPlan(null)
        setHata(false)
        return
      }
      const p = res.ok ? planCoz(govde) : null
      setKapali(false)
      setHata(p === null)
      if (p) setPlan(p)
    } catch {
      if (benim === surum.current) setHata(true)
    }
  }, [])

  useEffect(() => {
    // The first read starts on the next tick, like every later one (the timer, the events): the effect
    // itself changes no state.
    const ilk = setTimeout(oku, 0)
    const t = setInterval(oku, YENILEME_MS)
    window.addEventListener(ODEV_OLAYI, oku)
    window.addEventListener(PLAN_OLAYI, oku)
    return () => {
      clearTimeout(ilk)
      clearInterval(t)
      window.removeEventListener(ODEV_OLAYI, oku)
      window.removeEventListener(PLAN_OLAYI, oku)
    }
  }, [oku])

  const gonder = useCallback(async (yol: string, method: 'POST' | 'PUT', govde?: unknown,
    odevDegisti = false): Promise<PlanSonucu> => {
    let res: Response
    try {
      res = await fetch(yol, {
        method, credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(govde ?? {}),
      })
    } catch {
      window.dispatchEvent(new Event(PLAN_OLAYI))
      return { ok: false, hata: planHataCumlesi(null, null) }
    }
    const json: unknown = (res.headers.get('content-type') || '').includes('application/json')
      ? await res.json().catch(() => null) : null
    if (!res.ok) {
      // A refusal means the card was showing something the server no longer holds (another device
      // started a block, the block left the plan): read the plan again so the card catches up.
      window.dispatchEvent(new Event(PLAN_OLAYI))
      return { ok: false, hata: planHataCumlesi(res.status, json) }
    }
    const p = planCoz(json)
    if (p) {
      surum.current++
      setPlan(p)
      setHata(false)
    }
    // "Bitti" on a homework's last part records "Yaptım": İşler, "Ayrıca" and the assistant read it too.
    window.dispatchEvent(new Event(odevDegisti ? ODEV_OLAYI : PLAN_OLAYI))
    return { ok: true }
  }, [])

  const kodla = encodeURIComponent
  return {
    plan, kapali, hata,
    basla: id => gonder(`/api/plan/blok/${kodla(id)}/basla`, 'POST'),
    bitti: (id, tamamlandi) => gonder(`/api/plan/blok/${kodla(id)}/bitti`, 'POST',
      tamamlandi === undefined ? {} : { tamamlandi }, tamamlandi === true),
    simdiDegil: id => gonder(`/api/plan/blok/${kodla(id)}/simdi-degil`, 'POST'),
    sureDuzelt: (anahtar, dk) => gonder(`/api/plan/odev/${kodla(anahtar)}/sure`, 'PUT', { dakika: dk }),
    aksamYok: aktif => gonder('/api/plan/aksam-yok', 'POST', { aktif }),
  }
}
