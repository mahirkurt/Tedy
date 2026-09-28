import { useState } from 'react'
import { useApi } from './useApi'
import type { Ogretmen, OgretmenListesi } from '../types'

export const GENEL = 'genel'
const BOS: OgretmenListesi = { varsayilan: GENEL, ogretmenler: [] }

/** One key per person: two people sharing a device keep their own teacher. */
export function ogretmenAnahtari(email: string | null | undefined): string {
  return `tedy-asistan-ogretmen::${(email ?? '').trim().toLowerCase()}`
}

function hatirlanan(anahtar: string): string {
  try {
    return localStorage.getItem(anahtar) || GENEL
  } catch {
    return GENEL
  }
}

/**
 * The assistant's teacher (spec §1 "Seçici ve tema"): the list the backend serves, the one
 * this person chose last (localStorage), and a setter that remembers the choice.
 *
 * A remembered id the list does not carry — a teacher removed since, the list not loaded yet
 * or failed — reads as Genel; it is not erased, so it comes back when the list does.
 */
export function useOgretmen(email: string | null | undefined) {
  const { data, loading, error } = useApi<OgretmenListesi>('/api/assistant/ogretmenler', BOS)
  const anahtar = ogretmenAnahtari(email)
  // Kept with its key: the session can settle after the first render, and a choice made
  // under one person's key must not be read as another's.
  const [secim, setSecim] = useState<{ anahtar: string; id: string } | null>(null)
  const istenen = secim?.anahtar === anahtar ? secim.id : hatirlanan(anahtar)
  const liste: Ogretmen[] = data.ogretmenler ?? []
  const secili = liste.find(o => o.id === istenen) ?? null

  function sec(id: string) {
    setSecim({ anahtar, id })
    try {
      localStorage.setItem(anahtar, id)
    } catch {
      // Private browsing: the choice lasts this visit.
    }
  }

  return { liste, secili, id: secili ? secili.id : GENEL, sec, yukleniyor: loading, hata: error }
}
