import YuklenenEk from '../components/YuklenenEk'
import { useApi } from '../hooks/useApi'
import type { HomeworkItem } from '../types'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { acikOdevler } from './odevler.ts'

/** Kullanıcı mesajının altında, o mesajla gönderilen ekler (eski arayüzdeki gibi: okunabilir, ödeve bağlanabilir). */
export default function IstekEkleri({ mesajId }: { mesajId?: string }) {
  const ekler = useAsistanDurumu(d => (mesajId ? d.ekGoruntuleri[mesajId] : undefined))
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const { data } = useApi<{ homework: HomeworkItem[] }>('/api/homework', { homework: [] })
  if (!ekler?.length) return null
  return <>{ekler.map(ek => <YuklenenEk key={ek.id} ek={ek} odevler={acikOdevler(data.homework)} saltOkunur={salt} disabled={yukleniyor} />)}</>
}

