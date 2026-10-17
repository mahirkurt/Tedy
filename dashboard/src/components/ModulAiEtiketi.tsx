import { useEffect, useState } from 'react'
import { AILabel, AILabelContent } from '@carbon/react'
import { useDar } from '../asistan/useDar'

/** `/api/modules/…/aciklama`: what was written with AI help and what it rests on (talimatname S41, B71). */
export interface ModulAciklamasi {
  baslik: string | null
  ders: string | null
  sinif: string | null
  kazanimlar: string[]
  kitap: { ad: string | null; sayfalar: string | null } | null
  iddia_durumu: 'ok' | 'kayit_yok' | 'uyusmazlik'
  iddialar: { iddia: string; sayfa: number | null; kaynak: string | null }[]
  medya: { yapay_zeka: number; ders_kitabi: number; fotograf_arsivi: number }
}

type Durum = { tur: 'yukleniyor' } | { tur: 'hazir'; veri: ModulAciklamasi } | { tur: 'hata' }

const aralik = (s: string) => s.replace(/-/g, '–')

function medyaSatirlari(m: ModulAciklamasi['medya']): string[] {
  const out: string[] = []
  if (m.yapay_zeka > 0) out.push(`${m.yapay_zeka} görsel ya da ses yapay zekâyla üretildi.`)
  if (m.ders_kitabi > 0) out.push(`${m.ders_kitabi} görsel ders kitabından alındı.`)
  if (m.fotograf_arsivi > 0) out.push(`${m.fotograf_arsivi} fotoğraf bir fotoğraf arşivinden seçildi.`)
  return out
}

/** The explanation window: Carbon's four-part template (§6.2) — overview, details, what it rests on. */
export function ModulAiAciklamasi({ durum }: { durum: Durum }) {
  const veri = durum.tur === 'hazir' ? durum.veri : null
  const kitap = veri?.kitap
  const kitapMetni = kitap
    ? [kitap.ad ?? 'Ders kitabı', kitap.sayfalar ? `s. ${aralik(kitap.sayfalar)}` : null].filter(Boolean).join(', ')
    : null
  return (
    <div className="modul-ai">
      <h2 className="modul-ai__baslik">Bu modül yapay zekâ yardımıyla hazırlandı</h2>
      <p className="modul-ai__govde">
        Anlatımı, soruları ve açıklamaları bir yapay zekâ yazdı; aileden biri isteyip yayımladı. Yapay zekâ
        yanılabilir: emin olmadığın bir şey görürsen öğretmenine ya da ailene sor.
      </p>
      {durum.tur === 'yukleniyor' && <p className="modul-ai__govde">Ayrıntılar yükleniyor…</p>}
      {durum.tur === 'hata' && <p className="modul-ai__govde">Ayrıntılar şu an alınamadı.</p>}
      {veri && (
        <>
          <ul className="modul-ai__ayrintilar">
            {(veri.ders || veri.sinif) && <li>{[veri.ders, veri.sinif].filter(Boolean).join(' · ')}</li>}
            {veri.kazanimlar.length > 0 && <li>Kazanım: {veri.kazanimlar.join(', ')}</li>}
            {kitapMetni && <li>Dayandığı kitap: {kitapMetni}</li>}
            {medyaSatirlari(veri.medya).map(s => <li key={s}>{s}</li>)}
          </ul>
          <h3 className="modul-ai__alt-baslik">Kaynağıyla karşılaştırılan bilgiler</h3>
          {veri.iddia_durumu === 'ok' && veri.iddialar.length > 0 ? (
            <ul className="modul-ai__ayrintilar">
              {veri.iddialar.map(c => (
                <li key={c.iddia}>
                  {c.iddia}{' '}
                  <span className="modul-ai__dayanak">
                    ({[c.sayfa ? `ders kitabı s. ${c.sayfa}` : null, c.kaynak].filter(Boolean).join(' · ') || 'kaynak'})
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="modul-ai__govde">Bu sürüm için kayıtlı bir karşılaştırma yok.</p>
          )}
        </>
      )}
    </div>
  )
}

/** The AI label in the module frame's header (S41): a broad label for the whole module, upper right of
 *  the container. Name per B53: `slugLabel=""` + Turkish aria-label → "AI Yapay zekâ hakkında bilgi". The
 *  module itself is untouched (G-VOICE). */
export default function ModulAiEtiketi({ aciklamaPath }: { aciklamaPath: string }) {
  const dar = useDar()
  const [durum, setDurum] = useState<Durum>({ tur: 'yukleniyor' })
  useEffect(() => {
    let iptal = false
    fetch(aciklamaPath, { credentials: 'include' })
      .then(res => (res.ok ? (res.json() as Promise<ModulAciklamasi>) : Promise.reject(new Error(String(res.status)))))
      .then(veri => { if (!iptal) setDurum({ tur: 'hazir', veri }) })
      .catch(() => { if (!iptal) setDurum({ tur: 'hata' }) })
    return () => { iptal = true }
  }, [aciklamaPath])
  return (
    <AILabel kind="default" size={dar ? 'lg' : 'xs'} autoAlign aiText="AI" slugLabel=""
      aria-label="Yapay zekâ hakkında bilgi" align="bottom-right" className="module-viewer__ai">
      <AILabelContent>
        <ModulAiAciklamasi durum={durum} />
      </AILabelContent>
    </AILabel>
  )
}
