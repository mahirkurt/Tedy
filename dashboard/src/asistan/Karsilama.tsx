import { Button } from '@carbon/react'
import type { ChatInstance } from '@carbon/ai-chat'
import { useAsistanDurumu } from './asistanDeposu.ts'

/** Boş sohbette karşılama ve hızlı sorular (eski arayüzdeki gibi giriş alanının üstünde). Carbon'un başlangıç
 *  ekranı yerine: o ekran ayrı bir giriş alanı kullanıyor ve yüklenen geçmişte açık kalıyor. */
export default function Karsilama({ inst, karsilama, hizliSorular }: {
  inst: () => ChatInstance | null; karsilama: string; hizliSorular: { metin: string }[]
}) {
  const mesajVar = useAsistanDurumu(d => d.mesajVar)
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  if (mesajVar) return null
  return <div className="asistan__karsilama">
    <p className="asistan__karsilama-metni">{karsilama}</p>
    <div className="asistan__hizli-sorular">
      {hizliSorular.map((s, i) => <Button key={s.metin} kind={i === 0 ? 'primary' : 'tertiary'} size="sm"
        disabled={salt || yukleniyor} onClick={() => { void inst()?.send(s.metin) }}>{s.metin}</Button>)}
    </div>
  </div>
}
