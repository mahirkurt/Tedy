import { Button } from '@carbon/react'
import type { ChatInstance } from '@carbon/ai-chat'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { YUKLEME_SINIRLARI } from './ekler.ts'
import { useDar } from './useDar.ts'

/** Boş sohbette karşılama ve hızlı sorular, giriş alanının üstünde (Carbon'un başlangıç ekranı ayrı bir giriş alanı
 *  kullanıyor ve yüklenen geçmişte açık kalıyor). Tek cümle + en çok üç soru; hiçbiri birincil değil — ekranın tek
 *  birincil eylemi "Gönder" (S12). Yükleme sınırları ilk açılışta söylenir (B59): dosya seçilmeden önce. */
export default function Karsilama({ inst, karsilama, hizliSorular }: {
  inst: () => ChatInstance | null; karsilama: string; hizliSorular: { metin: string }[]
}) {
  const mesajVar = useAsistanDurumu(d => d.mesajVar)
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const dar = useDar()
  if (mesajVar) return null
  return <div className="asistan__karsilama">
    <p className="asistan__karsilama-metni">{karsilama}</p>
    {!salt && <div className="asistan__hizli-sorular">
      {hizliSorular.slice(0, 3).map(s => <Button key={s.metin} kind="tertiary" size={dar ? 'lg' : 'md'}
        disabled={yukleniyor} onClick={() => { void inst()?.send(s.metin) }}>{s.metin}</Button>)}
    </div>}
    {!salt && <p className="asistan__sinirlar">{YUKLEME_SINIRLARI}</p>}
  </div>
}
