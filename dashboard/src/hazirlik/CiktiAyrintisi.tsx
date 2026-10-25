import { useEffect, useRef } from 'react'
import type { KeyboardEvent } from 'react'
import { IconButton, Link as CarbonLink } from '@carbon/react'
import { Close, Launch } from '@carbon/icons-react'
import IcBaglanti from '../components/patterns/IcBaglanti'
import { ciktiKimligi, kitapYoluMetni, sayfaMetni } from './hazirlik'
import type { MatrisSatiri } from './tipler'

/** Satırın ayrıntısı (spec §3.2): tam MEB metni ve kitap bölümü. Masaüstünde tablonun yanında, telefonda alttan
 *  (Hazirlik.scss). Başlık yalnız kodu taşır (S38 başlık düzeni, MEB cümlesi alıntıda bir kez); açılınca odak başlığa gelir; Esc ve "Ayrıntıyı kapat" kapatır, odak satıra döner (çağıran).
 *
 *  D20: Esc yalnız odak panelin içindeyken kapatır (panelin kendi olayı, belgeye dinleyici yok): başka bir katman
 *  (asistan, pencere) üstteyse odak onda olur ve Esc o katmanın işidir. */
export default function CiktiAyrintisi({ satir, kilavuz, kapat }: { satir: MatrisSatiri; kilavuz: string; kapat: () => void }) {
  const baslik = useRef<HTMLHeadingElement>(null)
  useEffect(() => { baslik.current?.focus() }, [satir.kod])
  const tus = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key !== 'Escape' || e.defaultPrevented) return
    e.preventDefault()
    kapat()
  }
  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- Esc, odak panelin içindeyken kapatır (D20)
    <aside className="cikti-ayrinti" aria-labelledby="cikti-ayrinti-baslik" onKeyDown={tus}>
      <div className="cikti-ayrinti__ust">
        <h3 id="cikti-ayrinti-baslik" ref={baslik} tabIndex={-1} className="cikti-ayrinti__baslik">
          Öğrenme Çıktısı <span className="kilavuz-kod">{satir.kod}</span>
        </h3>
        <IconButton kind="ghost" size="lg" label="Ayrıntıyı kapat" onClick={kapat}><Close size={20} /></IconButton>
      </div>
      <blockquote className="cikti-ayrinti__meb">{`MEB: “${satir.metin}”`}</blockquote>
      <p className="cikti-ayrinti__etiket">Kitapta</p>
      {satir.kitap_durumu === 'var' ? (
        <ul className="cikti-ayrinti__yollar">
          {satir.kitapta.map(y => (
            <li key={`${y.cerceve}-${y.konu}`}>
              <CarbonLink href={y.baglanti} target="_blank" rel="noreferrer" renderIcon={Launch}>{kitapYoluMetni(y)}</CarbonLink>
              <span className="cikti-ayrinti__sayfa">{sayfaMetni(y.sayfa, y.son_sayfa)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p>{satir.kitap_durumu === 'bulunamadi' ? 'Kitapta karşılığı bulunamadı.' : 'Kitap bölümleri henüz eklenmedi.'}</p>
      )}
      <IcBaglanti href={`${kilavuz}#${ciktiKimligi(satir.kod)}`}>Kılavuzda aç</IcBaglanti>
    </aside>
  )
}
