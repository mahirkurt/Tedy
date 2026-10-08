import { Link, useLocation } from 'react-router-dom'
import { OverflowMenuHorizontal } from '@carbon/icons-react'
import type { UserRole } from '../hooks/useAuth'
import { primaryNavRoutes } from '../routes'
import { useFocusMode } from '../contexts/focusMode'
import { CARBON_AI_ACIK } from '../asistan/bayrak'
import { sayfaAdi } from '../asistan/sayfaBaglami'

// The phone's navigation (D3a, 2026-10-02). Four daily places and "Daha fazla",
// always one tap away — the menu button behind the brand band asked for two taps
// and a scan of twelve items before anything happened (İ1). Shown only below
// Carbon's md breakpoint by CSS, so the desktop side nav and this bar are never
// both in the accessibility tree.
const GUNLUK = ['/', '/isler', '/asistan', '/dersler']

// Sınavlar (fix round 1, item 2) is routable on its own (docs/frontend-...
// §4.2) but counts as İşler for the bar: exams surface inside İşler now
// (routes.ts), so a reader on /sinavlar should see İşler lit, not Daha fazla.
const ALIAS: Record<string, string> = { '/sinavlar': '/isler' }

// Every link here is a plain Link, not NavLink: NavLink computes aria-current
// from its own isActive (a straight match against `to`), which overrides
// whatever aria-current is passed in and knows nothing about ALIAS above —
// measured landing on /notlar (Daha fazla's own isActive is false, so its
// forced aria-current vanished) and on /sinavlar (İşler's isActive is false
// too, since the path is literally different). Active state is ours to
// compute, once, against the aliased path, for every tab alike.
export default function BottomNav({ role }: { role: UserRole }) {
  const { focusMode } = useFocusMode()
  const { pathname } = useLocation()
  const etkinYol = ALIAS[pathname] ?? pathname
  const sekmeler = primaryNavRoutes(role).filter(r => GUNLUK.includes(r.path))
  const eslesiyorMu = (yol: string) =>
    yol === '/' ? etkinYol === '/' : etkinYol === yol || etkinYol.startsWith(`${yol}/`)
  const birincilde = sekmeler.some(r => eslesiyorMu(r.path))
  // Carbon AI asistanında Asistan sekmesi bulunulan sayfayı bağlam olarak taşır (?sayfa=isler).
  const hedef = (yol: string) => {
    const ad = yol === '/asistan' && CARBON_AI_ACIK ? sayfaAdi(pathname) : null
    return ad ? `/asistan?sayfa=${ad}` : yol
  }

  return (
    <nav className="bottom-nav" aria-label="Ana gezinme">
      <ul className="bottom-nav__list">
        {sekmeler.map(r => {
          const Icon = r.icon
          const aktif = eslesiyorMu(r.path)
          return (
            <li key={r.path}>
              <Link
                to={hedef(r.path)}
                className={'bottom-nav__link' + (aktif ? ' active' : '')}
                aria-current={aktif ? 'page' : undefined}
              >
                <Icon aria-hidden="true" />
                <span>{r.label}</span>
              </Link>
            </li>
          )
        })}
        {!focusMode && (
          <li>
            <Link
              to="/daha-fazla"
              className={'bottom-nav__link' + (birincilde ? '' : ' active')}
              aria-current={birincilde ? undefined : 'page'}
            >
              <OverflowMenuHorizontal aria-hidden="true" />
              <span>Daha fazla</span>
            </Link>
          </li>
        )}
      </ul>
    </nav>
  )
}
