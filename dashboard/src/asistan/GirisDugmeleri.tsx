import { IconButton, OverflowMenu, OverflowMenuItem } from '@carbon/react'
import { CalendarHeatMap, Microphone, StopFilledAlt, Task } from '@carbon/icons-react'
import type { ChatInstance } from '@carbon/ai-chat'
import YuklemeAlani from '../components/YuklemeAlani'
import { useApi } from '../hooks/useApi'
import type { HomeworkItem } from '../types'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { soruyuYeniden, tekrariDurdur } from './istek.ts'
import { dosyalariEkle } from './ekler.ts'
import { acikOdevler, odevAdi } from './odevler.ts'

/** Giriş satırının eylemleri (genişletilmiş girişin eylem satırı, PROMPT_LINE_ACTIONS_END): dosya, fotoğraf (dokunmatik),
 *  ödeve bağla, sesle sor, çalışma planı. Hepsi ghost 48 px (telefonda ≥ 44 px); salt okunur sohbette hiçbiri yok
 *  (yapılamayacak eylem gizlenir, B42). Seçilen ödev giriş üstündeki bağlam çipi olur (BaglamCipi). */
export function GirisEylemleri({ inst, mikrofon }: { inst: () => ChatInstance | null; mikrofon: { var: boolean; dinliyor: boolean; bas: () => void } }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const bos = useAsistanDurumu(d => d.girisBos)
  const odevKey = useAsistanDurumu(d => d.odevKey)
  const { data } = useApi<{ homework: HomeworkItem[] }>('/api/homework', { homework: [] })
  if (salt) return null
  const odevler = acikOdevler(data.homework)
  return <div className="asistan__giris-eylemleri">
    <YuklemeAlani onDosyalar={dosyalariEkle} disabled={yukleniyor} />
    {odevler.length > 0 && <OverflowMenu size="lg" renderIcon={Task} iconDescription="Ödeve bağla" aria-label="Ödeve bağla"
      menuOptionsClass="asistan__odev-menusu" direction="top" flipped>
      {odevler.map(hw => <OverflowMenuItem key={hw.homework_key} itemText={odevAdi(hw)} requireTitle
        onClick={() => asistanDeposu.ayarla({ odevKey: hw.homework_key || '' })}
        disabled={yukleniyor} aria-current={hw.homework_key === odevKey ? 'true' : undefined} />)}
    </OverflowMenu>}
    {mikrofon.var && <IconButton kind="ghost" size="lg" label={mikrofon.dinliyor ? 'Dinlemeyi bitir' : 'Mikrofonu aç'}
      disabled={yukleniyor} onClick={mikrofon.bas}><Microphone /></IconButton>}
    <IconButton kind="ghost" size="lg" label="Çalışma planı iste" disabled={yukleniyor || bos} onClick={() => {
      const i = inst(); const metin = i?.getState().input.rawValue.trim() ?? ''
      if (i && metin) { i.input.updateRawValue(() => ''); void soruyuYeniden(i, metin, { plan: true }) }
    }}><CalendarHeatMap /></IconButton>
  </div>
}

/** Gönder düğmesinin hemen önü (PROMPT_LINE_SEND_BUTTON_START): "Tekrar dene" Carbon'un gönderimi değildir,
 *  Carbon'un durdur düğmesi çıkmaz; bu onun yerini tutar. */
export default function GirisDugmeleri() {
  const tekrar = useAsistanDurumu(d => d.tekrarSuruyor)
  if (!tekrar) return null
  return <IconButton kind="ghost" size="lg" label="Yanıtı durdur" onClick={tekrariDurdur}><StopFilledAlt /></IconButton>
}
