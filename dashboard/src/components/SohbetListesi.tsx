import { useEffect, useState } from 'react'
import { Button, TextInput } from '@carbon/react'
import type { Sohbet, useSohbetler } from '../hooks/useSohbetler'

type Depo = ReturnType<typeof useSohbetler>

export default function SohbetListesi({ depo, student, disabled, onAc, onYeni, onSil }: {
  depo: Depo; student: boolean; disabled: boolean
  onAc: (id: string, salt: boolean) => void
  onYeni: () => void
  onSil: (id: string) => void
}) {
  const [telefon, setTelefon] = useState(() => window.matchMedia('(max-width: 34rem)').matches)
  const [acik, setAcik] = useState(false)
  const [duzenle, setDuzenle] = useState<{ id: string; not: boolean; metin: string } | null>(null)
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 34rem)')
    const update = () => setTelefon(mq.matches)
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  async function kaydet() {
    if (!duzenle) return
    try {
      if (duzenle.not) await depo.notDegistir(duzenle.id, duzenle.metin)
      else await depo.degistir(duzenle.id, { baslik: duzenle.metin })
      setDuzenle(null)
    } catch (e) { depo.setHata(e instanceof Error ? e.message : 'Sohbet kaydedilemedi.') }
  }

  const alan = () => duzenle && <TextInput
    id={`sohbet-duzenle-${duzenle.id}`} labelText={duzenle.not ? 'Not' : 'Başlık'}
    value={duzenle.metin} onChange={e => setDuzenle({ ...duzenle, metin: e.target.value })}
    onKeyDown={e => { if (e.key === 'Enter') void kaydet(); if (e.key === 'Escape') setDuzenle(null) }}
  />
  function satirlar(liste: Sohbet[], salt = false) {
    const gorunen = liste.filter(s => s.baslik)
    return gorunen.length ? <ul className="ac-sohbetler__liste">{gorunen.map(s => <li key={s.id}>
      <Button kind="ghost" size="sm" disabled={disabled} aria-pressed={depo.secili?.id === s.id}
        onClick={() => { onAc(s.id, salt); setAcik(false) }}>{s.baslik}</Button>
      {!salt && <div className="ac-sohbetler__eylemler">
        <Button kind="ghost" size="sm" disabled={disabled}
          onClick={() => setDuzenle({ id: s.id, not: false, metin: s.baslik })}>Yeniden adlandır</Button>
        <Button kind="ghost" size="sm" disabled={disabled} onClick={() => onSil(s.id)}>Sil</Button>
      </div>}
      {duzenle?.id === s.id && alan()}
    </li>)}</ul> : <p className="ac__muted">Henüz sohbet yok — bir soru sorarak başla</p>
  }

  return <>
    {telefon && <Button className="ac-sohbetler__ac" kind="tertiary" size="sm"
      aria-expanded={acik} aria-controls="ac-sohbetler" onClick={() => setAcik(!acik)}>Sohbetler</Button>}
    <aside id="ac-sohbetler" className="ac-sohbetler" hidden={telefon && !acik} aria-label="Sohbet geçmişi">
      <div className="ac-sohbetler__baslik"><h3>Sohbetler</h3>
        {telefon && <Button kind="ghost" size="sm" onClick={() => setAcik(false)}>Kapat</Button>}
      </div>
      <Button kind="tertiary" size="sm" disabled={disabled} onClick={() => { onYeni(); setAcik(false) }}>Yeni sohbet</Button>
      {depo.hata && <p role="alert">{depo.hata}</p>}
      {satirlar(depo.liste)}
      {!student && <><h3>Işık'ın sohbetleri</h3>{satirlar(depo.isikListe, true)}
        <h3>Asistanın notları</h3>
        <ul className="ac-sohbetler__liste">{depo.notlar.map(n => <li key={n.id}>
          <p>{n.metin}</p>
          <div className="ac-sohbetler__eylemler">
            <Button kind="ghost" size="sm" onClick={() => setDuzenle({ id: n.id, not: true, metin: n.metin })}>Düzelt</Button>
            <Button kind="ghost" size="sm" onClick={() => void depo.notDegistir(n.id).catch(e => depo.setHata(String(e.message)))}>Sil</Button>
          </div>
          {duzenle?.id === n.id && alan()}
        </li>)}</ul>
      </>}
    </aside>
  </>
}
