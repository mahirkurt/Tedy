import { Button, Tag } from '@carbon/react'
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

export default function TedyKarti({ kart, state, inst, ogretmenSec }: { kart: OzelKart; state: RenderUserDefinedState; inst: ChatInstance; ogretmenSec: (id: string) => Promise<void> }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const ogretmenId = useAsistanDurumu(d => d.ogretmenId)
  const sonYanitId = useAsistanDurumu(d => d.sonYanitId)
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
      return <ul className="ac__ref-list">{kart.veri.map((b, i) => (
        <li key={`${b.day}-${i}`} className="ac__plan-item">
          <div className="ac__plan-header"><Tag type="gray" size="sm">{b.day}</Tag><span className="ac__plan-time">{b.estimated_minutes} dk</span></div>
          <span className="ac__plan-title">{b.title}</span>
          <p className="ac__plan-actions">{b.actions.join(' • ')}</p>
        </li>))}</ul>
    case 'hata':
      return <div className="asistan__hata" role="alert">
        <Tag type="red" size="sm">{kart.veri.mesaj}</Tag>
        {(kart.veri.govde || kart.veri.metin) && mesajId &&
          <Button kind="ghost" size="sm" renderIcon={Renew} onClick={() => void tekrarDene(inst, mesajId, kart.veri)}>Tekrar dene</Button>}
      </div>
  }
}
