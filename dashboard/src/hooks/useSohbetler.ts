import { useCallback, useEffect, useRef, useState } from 'react'
import type { AssistantCitation, Netlestirme } from '../types'
import type { OdevOnerisi } from '../components/OdevOnayKarti'
import type { Yukleme } from '../components/YuklenenEk'
import type { Alistirma } from '../components/AlistirmaKarti'
import { etkinSohbetiOku } from '../asistan/useAsistanOturumu'

export interface Sohbet {
  id: string
  baslik: string
  ogretmen: string
}
export interface KayitliMesaj {
  id: string
  rol: 'user' | 'assistant'
  icerik: string
  atiflar_json: string
  ekler_json: string
  alistirma?: Alistirma[]
  yuklemeler?: Yukleme[]
  netlestirme?: Netlestirme | null
  odev_onerisi?: OdevOnerisi | null
  zaman?: string
  geri_bildirim?: { deger: 'olumlu' | 'olumsuz'; kategori: string | null; metin: string } | null
}
export interface AsistanNotu { id: string; metin: string }
export interface SohbetIcerigi {
  sohbet: Sohbet
  mesajlar: KayitliMesaj[]
  read_only?: boolean
}

export function kayitliAtiflar(mesaj: KayitliMesaj): AssistantCitation[] {
  return JSON.parse(mesaj.atiflar_json || '[]') as AssistantCitation[]
}

async function istek<T>(path: string, method = 'GET', body?: object): Promise<T> {
  const res = await fetch(`/api/assistant/${path}`, {
    method, credentials: 'include',
    ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Sohbetler yüklenemedi.')
  return data as T
}

/** The selected conversation belongs to one signed-in person, never localStorage. */
export function useSohbetler(email: string | undefined, student: boolean) {
  const [liste, setListe] = useState<Sohbet[]>([])
  const [isikListe, setIsikListe] = useState<Sohbet[]>([])
  const [notlar, setNotlar] = useState<AsistanNotu[]>([])
  // Sayfa ile başlatıcı aynı etkin sohbeti açar (sekme oturumunda; yalnız yeni arayüz yazar).
  const [secili, setSecili] = useState<{ id: string; salt: boolean } | null>(() => etkinSohbetiOku(email ?? undefined))
  const [hata, setHata] = useState<string | null>(null)
  const [bekliyor, setBekliyor] = useState(false)
  const nesil = useRef(0)

  const yenile = useCallback(async () => {
    const current = nesil.current
    try {
      const [kendi, ogrenci, not] = await Promise.all([
        istek<{ sohbetler: Sohbet[] }>('sohbetler'),
        student ? Promise.resolve({ sohbetler: [] }) : istek<{ sohbetler: Sohbet[] }>('sohbetler?kisi=ogrenci'),
        student ? Promise.resolve({ notlar: [] }) : istek<{ notlar: AsistanNotu[] }>('notlar'),
      ])
      if (current !== nesil.current) return
      setListe(kendi.sohbetler)
      setIsikListe(ogrenci.sohbetler)
      setNotlar(not.notlar)
      setHata(null)
    } catch {
      if (current === nesil.current) setHata('Sohbetler yüklenemedi.')
    }
  }, [student])

  useEffect(() => {
    nesil.current += 1
    if (email) void yenile()
    return () => { nesil.current += 1 }
  }, [email, yenile])

  async function yeni(ogretmen: string) {
    const result = await istek<{ id: string }>('sohbetler', 'POST', { ogretmen })
    setSecili({ id: result.id, salt: false })
    await yenile()
    return result.id
  }

  async function ac(id: string, salt: boolean): Promise<SohbetIcerigi | null> {
    setBekliyor(true)
    try {
      const result = await istek<SohbetIcerigi>(`sohbetler/${id}`)
      setSecili({ id, salt: result.read_only ?? salt })
      setHata(null)
      return result
    } catch {
      // Açılamayan (silinmiş) sohbet seçili kalmaz: sonraki soru ölü kimliğe gidip 404 almasın.
      setSecili(prev => (prev?.id === id ? null : prev))
      setHata('Sohbetler yüklenemedi.')
      return null
    } finally { setBekliyor(false) }
  }

  async function degistir(id: string, body: { baslik?: string; ogretmen?: string }) {
    await istek(`sohbetler/${id}`, 'PATCH', body)
    await yenile()
  }

  async function sil(id: string) {
    await istek(`sohbetler/${id}`, 'DELETE')
    if (secili?.id === id) setSecili(null)
    await yenile()
  }

  async function notDegistir(id: string, metin?: string) {
    await istek(`notlar/${id}`, metin === undefined ? 'DELETE' : 'PATCH',
      metin === undefined ? undefined : { metin })
    await yenile()
  }

  return { liste, isikListe, notlar, secili, hata, setHata, bekliyor, yenile, yeni, ac, degistir, sil, notDegistir }
}
