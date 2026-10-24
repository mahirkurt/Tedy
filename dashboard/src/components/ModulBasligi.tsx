import { useRef, useState, type ReactNode } from 'react'
import { Breadcrumb, BreadcrumbItem, Modal, OperationalTag, SkeletonText } from '@carbon/react'
import { useNavigate } from 'react-router-dom'
import { useDar } from '../asistan/useDar'
import { basliga } from '../utils/baslik'
import { subjectClass } from '../utils/subject'
import SubjectLabel from './SubjectLabel'
import type { ModulAciklamaDurumu, ModulAciklamasi } from '../hooks/useModulAciklamasi'

const aralik = (s: string) => s.replace(/-/g, '–')

function kitapMetni(kitap: ModulAciklamasi['kitap']): string | null {
  if (!kitap) return null
  return [kitap.ad ?? 'Ders kitabı', kitap.sayfalar ? `s. ${aralik(kitap.sayfalar)}` : null].filter(Boolean).join(', ')
}

/**
 * The module page's head (2026-10-19): the module is a section of the dashboard, so the dashboard
 * names it — the module itself drops its own title in the flow layout. A Carbon breadcrumb back to
 * Modüller (the current page is not a link), then the view's one subject panel (İ8.3; the
 * `NextThing` language: step-10 ground, step-30 border, 4px accent edge): the subject mark with
 * class and time, the title in title case, the AI label upper right of its container (S41), and one
 * operational tag per outcome that opens the outcome's wording in a passive Carbon modal.
 */
export default function ModulBasligi({ durum, aiEtiketi, taslak, yedekBaslik = 'Öğrenme Modülü' }: {
  durum: ModulAciklamaDurumu
  aiEtiketi: ReactNode
  taslak?: boolean
  /** The title when the explanation carries none (a module no longer published says "Modül"). */
  yedekBaslik?: string
}) {
  const navigate = useNavigate()
  const dar = useDar()
  const [acik, setAcik] = useState<string | null>(null)
  // Carbon returns focus to the launcher only through this ref; it is the tag that opened the dialog.
  const acan = useRef<HTMLElement | null>(null)
  const veri = durum.tur === 'hazir' ? durum.veri : null
  const ders = veri?.ders ?? null
  const kazanimlar = veri?.kazanim_ayrintilari?.length
    ? veri.kazanim_ayrintilari
    : (veri?.kazanimlar ?? []).map(kod => ({ kod, metin: null, beceri: null }))
  const secili = kazanimlar.find(k => k.kod === acik) ?? null
  const kitap = kitapMetni(veri?.kitap ?? null)
  const kas = [veri?.sinif, veri?.sure_dk ? `~${veri.sure_dk} dk` : null].filter(Boolean).join(' · ')
  return (
    <header className={['modul-baslik', ders ? subjectClass(ders) : 'modul-baslik--notr'].join(' ')}>
      <Breadcrumb className="modul-baslik__iz" aria-label="Konum">
        <BreadcrumbItem href="/moduller"
          onClick={(e: React.MouseEvent) => { e.preventDefault(); navigate('/moduller') }}>Modüller</BreadcrumbItem>
      </Breadcrumb>
      <div className="modul-baslik__panel" aria-busy={durum.tur === 'yukleniyor' || undefined}>
        <div className="modul-baslik__ust">
          <p className="modul-baslik__kas">
            {ders
              ? <SubjectLabel course={ders}>{[ders, kas].filter(Boolean).join(' · ')}</SubjectLabel>
              : kas || (taslak ? 'Taslak' : '')}
          </p>
          <div className="modul-baslik__ai">
            <p className="modul-baslik__ai-not">Yapay zekâ yardımıyla hazırlanmış modül</p>
            {aiEtiketi}
          </div>
        </div>
        {durum.tur === 'yukleniyor'
          ? <SkeletonText heading width="60%" />
          : <h2 className="modul-baslik__baslik">{veri?.baslik ? basliga(veri.baslik) : yedekBaslik}</h2>}
        {(kazanimlar.length > 0 || kitap) && (
          <div className="modul-baslik__alt">
            {kazanimlar.length > 0 && (
              <div className="modul-baslik__kazanimlar" role="group" aria-label="Kazanımlar">
                {kazanimlar.map(k => (
                  <OperationalTag key={k.kod} type="gray" size={dar ? 'lg' : 'md'} text={k.kod}
                    aria-haspopup="dialog"
                    onClick={(e: React.MouseEvent<HTMLElement>) => { acan.current = e.currentTarget; setAcik(k.kod) }} />
                ))}
              </div>
            )}
            {kitap && <p className="modul-baslik__kitap">{kitap}</p>}
          </div>
        )}
      </div>
      <Modal open={secili !== null} passiveModal size="sm" modalLabel="Kazanım" modalHeading={secili?.kod ?? ''}
        closeButtonLabel="Kapat" onRequestClose={() => setAcik(null)} className="modul-kazanim"
        launcherButtonRef={acan}
        // First focus on the wording, not the close button: there Carbon's tooltip eats the first Escape.
        selectorPrimaryFocus=".modul-kazanim__metin">
        {secili && (
          <div className="modul-kazanim__govde">
            <p className="modul-kazanim__metin" tabIndex={-1}>
              {secili.metin ?? 'Bu kazanımın metni bu sürümde kayıtlı değil.'}
            </p>
            <dl className="modul-kazanim__ayrinti">
              {secili.beceri && (<><dt>Beceri</dt><dd>{secili.beceri}</dd></>)}
              {ders && (<><dt>Ders</dt><dd>{[ders, veri?.sinif].filter(Boolean).join(' · ')}</dd></>)}
              {kitap && (<><dt>Dayandığı kitap</dt><dd>{kitap}</dd></>)}
            </dl>
          </div>
        )}
      </Modal>
    </header>
  )
}
