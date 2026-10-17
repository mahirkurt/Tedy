import { useEffect, useState } from 'react'
import { Button, IconButton } from '@carbon/react'
import { Copy, Renew, Search, Book, ErrorFilled, InformationFilled, WarningAltFilled } from '@carbon/icons-react'
import type { ChatInstance, MessageResponse } from '@carbon/ai-chat'
import { okunacakMetin } from '../utils/ses'
import type { AltbilgiVerisi } from './olayEslemesi.ts'
import { useAsistanDurumu, asistanDeposu } from './asistanDeposu.ts'
import { kaynaklariAc, soruyuYeniden } from './istek.ts'
import { useDar } from './useDar.ts'

const BAYRAK: Record<string, string> = {
  'warning:limited_confidence': 'Kaynaksız cevap', 'warning:stale_context': 'Veriler güncel olmayabilir',
  'error:model_unavailable': 'Asistana ulaşılamadı', 'warning:yerel_yedek': 'Yedek modelden',
}
const KAYNAK: Record<string, string> = {
  'maarif-mufredat': 'Müfredat kaynağına ulaşılamadı', 'egitim-kaynak': 'Açık eğitim kaynağına ulaşılamadı',
  'modul-katalogu': 'Modül kataloğu okunamadı',
}

type Tur = 'uyari' | 'hata' | 'bilgi'
const IKON = { uyari: WarningAltFilled, hata: ErrorFilled, bilgi: InformationFilled }
const IKON_ADI: Record<Tur, string> = { uyari: 'Uyarı', hata: 'Hata', bilgi: 'Bilgi' }
/** Bayrağın türü (S45): kısmi/bayat okuma ve yedek model uyarı; kaynaksız cevap bilgi; erişilemeyen asistan ve
 *  risk hata. Gri hiçbir zaman bir arızayı işaretlemez. */
function bayrakTuru(f: string): Tur {
  if (f.startsWith('risk:') || f.startsWith('error:')) return 'hata'
  return f === 'warning:limited_confidence' ? 'bilgi' : 'uyari'
}

/** Durum göstergesi: ikon + metin (renk tek başına taşımaz, İ8; ikonun adı ekran okuyucuya türü söyler). */
function Durum({ tur, metin }: { tur: Tur; metin: string }) {
  const Ikon = IKON[tur]
  return <li className={`asistan__durum asistan__durum--${tur}`}>
    <Ikon size={16} aria-label={IKON_ADI[tur]} className="asistan__durum-ikon" />
    <span>{metin}</span>
  </li>
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
  // Telefonda 48 px (≥ 44 px dokunma hedefi); masaüstünde Carbon'un küçük düğmesi.
  const boy = useDar() ? 'lg' : 'sm'
  // Kopyalama onaylanır (B41): düğmenin adı ve canlı bölge "Kopyalandı" der; pano reddederse "Kopyalanamadı".
  const [kopya, setKopya] = useState<'' | 'Kopyalandı' | 'Kopyalanamadı'>('')
  useEffect(() => { if (!kopya) return; const t = setTimeout(() => setKopya(''), 3000); return () => clearTimeout(t) }, [kopya])
  const kopyala = () => navigator.clipboard.writeText(veri.metin).then(() => setKopya('Kopyalandı'), () => setKopya('Kopyalanamadı'))
  return (
    <div className="asistan__altbilgi" data-tedy-altbilgi>
      {(veri.kaynakSorunlari.length > 0 || veri.bayraklar.length > 0) && <ul className="asistan__durumlar">
        {veri.kaynakSorunlari.map(s => <Durum key={s} tur="uyari" metin={KAYNAK[s] ?? `Kaynağa ulaşılamadı: ${s}`} />)}
        {veri.bayraklar.map(f => <Durum key={f} tur={bayrakTuru(f)} metin={BAYRAK[f] ?? f} />)}
      </ul>}
      <div className="asistan__eylemler">
        {veri.atiflar.length > 0 && <Button kind="ghost" size={boy} renderIcon={Book}
          onClick={e => void kaynaklariAc(inst, veri.atiflar, null, e.currentTarget)}>Kaynak ayrıntıları</Button>}
        <IconButton kind="ghost" size={boy} label={kopya || 'Kopyala'} onClick={() => void kopyala()}><Copy /></IconButton>
        {kopya && <span className="cds--visually-hidden" role="status">{kopya}</span>}
        {/* Salt okunur sohbette yapılamayacak eylem gizlenir, soluk gösterilmez (B42). */}
        {!salt && <IconButton kind="ghost" size={boy} label="Yeniden üret" disabled={yukleniyor} onClick={async () => {
          const s = soru(veri.metin); if (!s) return
          await inst.messaging.removeMessages([mesaj.id!]); await soruyuYeniden(inst, s, { transient: true })
        }}><Renew /></IconButton>}
        {!salt && <Button kind="ghost" size={boy} renderIcon={Search} disabled={yukleniyor}
          onClick={() => { const s = soru(veri.metin); if (s) void soruyuYeniden(inst, s, { deep: true }) }}>Daha derine in</Button>}
        {ses?.var && okunacakMetin(veri.metin) && <Button kind="ghost" size={boy} aria-pressed={ses.okunan === mesaj.id}
          onClick={() => ses.oku(mesaj.id!, veri.metin)}>{ses.okunan === mesaj.id ? 'Durdur' : 'Sesli oku'}</Button>}
      </div>
    </div>
  )
}
