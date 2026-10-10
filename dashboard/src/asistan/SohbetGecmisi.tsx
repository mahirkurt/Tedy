import { useState } from 'react'
import { Button, IconButton, InlineNotification, TextInput } from '@carbon/react'
import { Add, Close, Edit, TrashCan } from '@carbon/icons-react'
import type { Sohbet, useSohbetler } from '../hooks/useSohbetler'

type Depo = ReturnType<typeof useSohbetler>

/** Silme onayının isteği: SilmeOnayi modalı sohbet kabının dışında çizer (S40, B23). */
export interface SilmeIstegi {
  baslik: string; govde: string; dugme: string
  /** Başarısız silmenin cümlesi, doğru fiille ("silinemedi"). */
  hata: string; hataBildir: (m: string) => void
  sil: () => Promise<void>
}

/**
 * Carbon geçmiş panelinin içeriği (HISTORY_PANEL_ELEMENT). Nötr TEDY yüzeyi (S46: AI aurası yalnız sohbet panelinde):
 * okurun kendi sohbetleri, ailede Işık'ın sohbetleri (salt okunur) ve asistanın notları. Boş durum tek cümle,
 * okurun sesiyle; silme her zaman onaylı (onSil yalnız onay ister, işi modal yapar).
 */
export default function SohbetGecmisi({ depo, ogrenci, kilitli, onAc, onYeni, onKapat, onSilSohbet, onSil }: {
  depo: Depo; ogrenci: boolean; kilitli: boolean
  /** Paneli kapatır: telefonda panel sohbet başlığını da örter, "Sohbetler" eylemi görünmez. */
  onKapat: () => void
  onAc: (id: string, salt: boolean) => void
  onYeni: () => void
  /** Sohbet silindikten sonra (açık olan sohbetse konuşmayı boşaltmak için). */
  onSilSohbet: (id: string) => Promise<void>
  onSil: (istek: SilmeIstegi) => void
}) {
  const [duzenle, setDuzenle] = useState<{ id: string; not: boolean; metin: string } | null>(null)

  async function kaydet() {
    if (!duzenle) return
    try {
      if (duzenle.not) await depo.notDegistir(duzenle.id, duzenle.metin)
      else await depo.degistir(duzenle.id, { baslik: duzenle.metin })
      setDuzenle(null)
    } catch { depo.setHata(duzenle.not ? 'Not kaydedilemedi.' : 'Sohbetin adı kaydedilemedi.') }
  }

  const alan = (id: string) => duzenle?.id === id && <TextInput
    id={`sohbet-duzenle-${id}`} size="lg" labelText={duzenle.not ? 'Not' : 'Sohbetin adı'}
    helperText="Kaydetmek için Enter, vazgeçmek için Esc." value={duzenle.metin}
    onChange={e => setDuzenle({ ...duzenle, metin: e.target.value })}
    onKeyDown={e => { if (e.key === 'Enter') void kaydet(); if (e.key === 'Escape') setDuzenle(null) }} />

  function satirlar(liste: Sohbet[], bos: string, salt = false) {
    const gorunen = liste.filter(s => s.baslik)
    if (!gorunen.length) return <p className="asistan-gecmis__bos">{bos}</p>
    return <ul className="asistan-gecmis__liste">{gorunen.map(s => <li key={s.id} className="asistan-gecmis__satir">
      <div className="asistan-gecmis__satir-ust">
        <Button kind="ghost" size="lg" className="asistan-gecmis__ac" disabled={kilitli}
          aria-current={depo.secili?.id === s.id ? 'true' : undefined} onClick={() => onAc(s.id, salt)}>{s.baslik}</Button>
        {!salt && <>
          <IconButton kind="ghost" size="lg" align="left" label={`Yeniden adlandır: ${s.baslik}`} disabled={kilitli}
            onClick={() => setDuzenle({ id: s.id, not: false, metin: s.baslik })}><Edit /></IconButton>
          <IconButton kind="ghost" size="lg" align="left" label={`Sil: ${s.baslik}`} disabled={kilitli}
            onClick={() => onSil({ baslik: 'Sohbeti sil', dugme: 'Sohbeti sil', hata: 'Sohbet silinemedi.', hataBildir: depo.setHata,
              govde: `“${s.baslik}” sohbeti, ona bağlı ekler ve alıştırmalarla birlikte silinir. Bu geri alınamaz.`,
              sil: () => onSilSohbet(s.id) })}><TrashCan /></IconButton>
        </>}
      </div>
      {alan(s.id)}
    </li>)}</ul>
  }

  return <section className="asistan-gecmis" aria-labelledby="asistan-gecmis-baslik">
    <div className="asistan-gecmis__ust">
      <h2 id="asistan-gecmis-baslik" className="asistan-gecmis__baslik">Sohbetler</h2>
      <IconButton kind="ghost" size="lg" align="left" label="Sohbetleri kapat" onClick={onKapat}><Close /></IconButton>
    </div>
    <Button kind="tertiary" size="lg" renderIcon={Add} disabled={kilitli} onClick={onYeni}>Yeni sohbet</Button>
    {depo.hata && <InlineNotification kind="error" lowContrast hideCloseButton role="alert" title={depo.hata}
      statusIconDescription="Hata" />}
    {satirlar(depo.liste, ogrenci ? 'Henüz sohbetin yok.' : 'Henüz sohbetiniz yok.')}
    {!ogrenci && <>
      <h3 className="asistan-gecmis__alt-baslik">Işık'ın sohbetleri</h3>
      {satirlar(depo.isikListe, "Işık'ın henüz sohbeti yok.", true)}
      <h3 className="asistan-gecmis__alt-baslik">Asistanın notları</h3>
      {depo.notlar.length ? <ul className="asistan-gecmis__liste">{depo.notlar.map(n => <li key={n.id} className="asistan-gecmis__satir">
        <div className="asistan-gecmis__satir-ust">
          <p className="asistan-gecmis__not">{n.metin}</p>
          <IconButton kind="ghost" size="lg" align="left" label="Notu düzelt"
            onClick={() => setDuzenle({ id: n.id, not: true, metin: n.metin })}><Edit /></IconButton>
          <IconButton kind="ghost" size="lg" align="left" label="Notu sil"
            onClick={() => onSil({ baslik: 'Notu sil', dugme: 'Notu sil', hata: 'Not silinemedi.', hataBildir: depo.setHata,
              govde: `“${n.metin}” notu silinir; asistan sonraki sohbetlerde bunu hatırlamaz. Bu geri alınamaz.`,
              sil: () => depo.notDegistir(n.id) })}><TrashCan /></IconButton>
        </div>
        {alan(n.id)}
      </li>)}</ul> : <p className="asistan-gecmis__bos">Asistan henüz not almadı.</p>}
    </>}
  </section>
}
