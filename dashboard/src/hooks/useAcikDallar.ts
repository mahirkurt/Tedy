import { useCallback, useState } from 'react'

/**
 * Müfredat ağacında açık dallar.
 *
 * Seçim kullanıcı değiştirene dek kalır (İ5): okur bir üniteyi açtıysa sayfayı yenilediğinde
 * ya da başka bir sayfadan döndüğünde onu açık bulur. `localStorage` okunamayan ortamlarda
 * (gizli pencere, kapatılmış site verisi, önizleme) sessizce oturum içi çalışır — sayfa yine
 * çizilir; depolama her okuma ve yazmada try/catch ile sarılıdır.
 */
const ANAHTAR = 'tedy-mufredat-acik'

function yukle(): Set<string> {
  try {
    const ham = window.localStorage.getItem(ANAHTAR)
    const dizi = ham ? (JSON.parse(ham) as unknown) : []
    return new Set(Array.isArray(dizi) ? dizi.filter((d): d is string => typeof d === 'string') : [])
  } catch {
    return new Set()
  }
}

export function useAcikDallar(): { acik: Set<string>; degistir: (id: string) => void } {
  const [acik, setAcik] = useState<Set<string>>(yukle)
  const degistir = useCallback((id: string) => {
    setAcik(onceki => {
      const sonraki = new Set(onceki)
      if (!sonraki.delete(id)) sonraki.add(id)
      try {
        window.localStorage.setItem(ANAHTAR, JSON.stringify([...sonraki]))
      } catch { /* depolama yoksa seçim oturum içinde kalır */ }
      return sonraki
    })
  }, [])
  return { acik, degistir }
}
