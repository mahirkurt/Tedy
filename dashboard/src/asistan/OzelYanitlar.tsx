import { Button, InlineNotification, Tag } from '@carbon/react'
import { Renew } from '@carbon/icons-react'
import type { ChatInstance, RenderUserDefinedState } from '@carbon/ai-chat'
import AlistirmaKarti from '../components/AlistirmaKarti'
import OdevOnayKarti from '../components/OdevOnayKarti'
import NetlestirmeSecenekleri from '../components/NetlestirmeSecenekleri'
import ModOnerisi from '../components/ModOnerisi'
import { GENEL } from '../hooks/useOgretmen'
import type { OzelKart } from './olayEslemesi.ts'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { soruyuYeniden, tekrarDene } from './istek.ts'
import { useDar } from './useDar.ts'

export default function TedyKarti({ kart, state, inst, ogretmenSec }: { kart: OzelKart; state: RenderUserDefinedState; inst: ChatInstance; ogretmenSec: (id: string) => Promise<void> }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const ogretmenId = useAsistanDurumu(d => d.ogretmenId)
  const sonYanitId = useAsistanDurumu(d => d.sonYanitId)
  const dar = useDar()
  const mesajId = state.fullMessage?.id
  switch (kart.tur) {
    case 'alistirma':
      return <AlistirmaKarti alistirma={kart.veri} saltOkunur={salt} disabled={kart.akista || yukleniyor}
        onYanlislar={metin => void soruyuYeniden(inst, `Yanlış yaptığım bu soruları açıklar mısın?\n${metin}`, {})} />
    case 'odev_onerisi':
      return <OdevOnayKarti oneri={kart.veri} saltOkunur={salt || yukleniyor} />
    case 'netlestirme':
      // Yalnız son cevaptaki seçenekler etkin; eski ya da salt okunur sohbette kapalı (D1).
      return <NetlestirmeSecenekleri secenekler={kart.veri.secenekler}
        etkin={mesajId !== undefined && mesajId === sonYanitId && !yukleniyor && !salt}
        onSec={metin => void inst.send(metin)} onBaska={() => inst.requestFocus()} />
    case 'mod_onerisi':
      if (ogretmenId !== GENEL) return null
      return <ModOnerisi oneri={kart.veri} onGec={() => void ogretmenSec(kart.veri.ogretmen)} />
    case 'plan':
      return <ul className="asistan-plan">{kart.veri.map((b, i) => (
        <li key={`${b.day}-${i}`} className="asistan-plan__oge">
          <div className="asistan-plan__ust"><Tag type="gray" size="md">{b.day}</Tag><span className="asistan-plan__sure">{b.estimated_minutes} dk</span></div>
          <span className="asistan-plan__baslik">{b.title}</span>
          <p className="asistan-plan__adimlar">{b.actions.join(' • ')}</p>
        </li>))}</ul>
    case 'hata':
      // Hata bir bildirimdir (B45): cümle kırmızı Tag'de değil, Carbon InlineNotification'da; eylem altında.
      return <div className="asistan__hata">
        <InlineNotification kind="error" lowContrast hideCloseButton role="alert" title={kart.veri.mesaj}
          statusIconDescription="Hata" />
        {(kart.veri.govde || kart.veri.metin) && mesajId &&
          <Button kind="ghost" size={dar ? 'lg' : 'sm'} renderIcon={Renew} onClick={() => void tekrarDene(inst, mesajId, kart.veri)}>Tekrar dene</Button>}
      </div>
  }
}
