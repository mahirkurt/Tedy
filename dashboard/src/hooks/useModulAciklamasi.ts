import { useEffect, useState } from 'react'

/** `/api/modules/…/aciklama`: what was written with AI help and what it rests on (talimatname S41, B71). */
export interface ModulAciklamasi {
  baslik: string | null
  ders: string | null
  sinif: string | null
  /** Estimated minutes, when the compiler kept them (2026-10-19). */
  sure_dk?: number | null
  kazanimlar: string[]
  /** Wording and skill per outcome code; `metin` is null for a build compiled before 2026-10-19. */
  kazanim_ayrintilari?: { kod: string; metin: string | null; beceri: string | null }[]
  kitap: { ad: string | null; sayfalar: string | null } | null
  iddia_durumu: 'ok' | 'kayit_yok' | 'uyusmazlik'
  iddialar: { iddia: string; sayfa: number | null; kaynak: string | null }[]
  medya: { yapay_zeka: number; ders_kitabi: number; fotograf_arsivi: number }
}

export type ModulAciklamaDurumu = { tur: 'yukleniyor' } | { tur: 'hazir'; veri: ModulAciklamasi } | { tur: 'hata' }

/** One fetch of `/api/modules/…/aciklama` for the module page: the head and the AI label read it. */
export function useModulAciklamasi(aciklamaPath: string): ModulAciklamaDurumu {
  const [durum, setDurum] = useState<ModulAciklamaDurumu>({ tur: 'yukleniyor' })
  const [gorulen, setGorulen] = useState(aciklamaPath)
  if (gorulen !== aciklamaPath) {
    setGorulen(aciklamaPath)
    setDurum({ tur: 'yukleniyor' })
  }
  useEffect(() => {
    let iptal = false
    fetch(aciklamaPath, { credentials: 'include' })
      .then(res => (res.ok ? (res.json() as Promise<ModulAciklamasi>) : Promise.reject(new Error(String(res.status)))))
      .then(veri => { if (!iptal) setDurum({ tur: 'hazir', veri }) })
      .catch(() => { if (!iptal) setDurum({ tur: 'hata' }) })
    return () => { iptal = true }
  }, [aciklamaPath])
  return durum
}
