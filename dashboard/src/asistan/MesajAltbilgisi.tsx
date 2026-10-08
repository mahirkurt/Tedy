import { Button, IconButton, Tag } from '@carbon/react'
import { Copy, Renew, Search, Book } from '@carbon/icons-react'
import type { ChatInstance, MessageResponse } from '@carbon/ai-chat'
import { okunacakMetin } from '../utils/ses'
import type { AltbilgiVerisi } from './olayEslemesi.ts'
import { useAsistanDurumu, asistanDeposu } from './asistanDeposu.ts'
import { kaynaklariAc, soruyuYeniden } from './istek.ts'

const BAYRAK: Record<string, string> = {
  'warning:limited_confidence': 'Kaynaksız cevap', 'warning:stale_context': 'Veriler güncel olmayabilir',
  'error:model_unavailable': 'Asistana ulaşılamadı', 'warning:yerel_yedek': 'Yedek modelden',
}
const KAYNAK: Record<string, string> = {
  'maarif-mufredat': 'Müfredat kaynağına ulaşılamadı', 'egitim-kaynak': 'Açık eğitim kaynağına ulaşılamadı',
  'modul-katalogu': 'Modül kataloğu okunamadı',
}

/** Bu cevabı doğuran kullanıcı sorusu: döküm sırasında bu cevaptan önceki son kullanıcı turu. */
function soru(metin: string): string | null {
  const dokum = asistanDeposu.al().dokum
  const i = dokum.map(m => m.role === 'assistant' && m.content === metin).lastIndexOf(true)
  for (let j = (i < 0 ? dokum.length : i) - 1; j >= 0; j -= 1) if (dokum[j].role === 'user') return dokum[j].content
  return null
}

export default function MesajAltbilgisi({ veri, mesaj, inst }: { veri: AltbilgiVerisi; mesaj: MessageResponse; inst: ChatInstance }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const ses = useAsistanDurumu(d => d.ses)
  const kapali = yukleniyor || salt
  return (
    <div className="asistan__altbilgi" data-tedy-altbilgi>
      {(veri.kaynakSorunlari.length > 0 || veri.bayraklar.length > 0) && <div className="asistan__rozetler">
        {veri.kaynakSorunlari.map(s => <Tag key={s} type="gray" size="sm">{KAYNAK[s] ?? `Kaynağa ulaşılamadı: ${s}`}</Tag>)}
        {veri.bayraklar.map(f => <Tag key={f} type={f.startsWith('risk:') ? 'red' : 'gray'} size="sm">{BAYRAK[f] ?? f}</Tag>)}
      </div>}
      <div className="asistan__eylemler">
        {veri.atiflar.length > 0 && <Button kind="ghost" size="sm" renderIcon={Book}
          onClick={() => void kaynaklariAc(inst, veri.atiflar, null)}>Kaynak ayrıntıları</Button>}
        <IconButton kind="ghost" size="sm" label="Kopyala" onClick={() => void navigator.clipboard.writeText(veri.metin)}><Copy /></IconButton>
        <IconButton kind="ghost" size="sm" label="Yeniden üret" disabled={kapali} onClick={async () => {
          const s = soru(veri.metin); if (!s) return
          await inst.messaging.removeMessages([mesaj.id!]); await soruyuYeniden(inst, s, { transient: true })
        }}><Renew /></IconButton>
        <Button kind="ghost" size="sm" renderIcon={Search} disabled={kapali}
          onClick={() => { const s = soru(veri.metin); if (s) void soruyuYeniden(inst, s, { deep: true }) }}>Daha derine in</Button>
        {ses?.var && okunacakMetin(veri.metin) && <Button kind="ghost" size="sm" aria-pressed={ses.okunan === mesaj.id}
          onClick={() => ses.oku(mesaj.id!, veri.metin)}>{ses.okunan === mesaj.id ? 'Durdur' : 'Sesli oku'}</Button>}
      </div>
    </div>
  )
}
