import { Link, NavLink, useLocation } from 'react-router-dom'
import { OverflowMenuHorizontal } from '@carbon/icons-react'
import type { UserRole } from '../hooks/useAuth'
import { primaryNavRoutes } from '../routes'
import { useFocusMode } from '../contexts/focusMode'

// The phone's navigation (D3a, 2026-10-02). Four daily places and "Daha fazla",
// always one tap away — the menu button behind the brand band asked for two taps
// and a scan of twelve items before anything happened (İ1). Shown only below
// Carbon's md breakpoint by CSS, so the desktop side nav and this bar are never
// both in the accessibility tree.
const GUNLUK = ['/', '/isler', '/asistan', '/dersler']

export default function BottomNav({ role }: { role: UserRole }) {
  const { focusMode } = useFocusMode()
  const { pathname } = useLocation()
  const sekmeler = primaryNavRoutes(role).filter(r => GUNLUK.includes(r.path))
  const birincilde = sekmeler.some(r =>
    r.path === '/' ? pathname === '/' : pathname === r.path || pathname.startsWith(`${r.path}/`))

  return (
    <nav className="bottom-nav" aria-label="Ana gezinme">
      <ul className="bottom-nav__list">
        {sekmeler.map(r => {
          const Icon = r.icon
          return (
            <li key={r.path}>
              <NavLink to={r.path} end={r.path === '/'} className="bottom-nav__link">
                <Icon aria-hidden="true" />
                <span>{r.label}</span>
              </NavLink>
            </li>
          )
        })}
        {!focusMode && (
          <li>
            {/*
              A plain Link, not NavLink: NavLink computes aria-current from its
              own isActive (a match against `to`), which stays false on every
              secondary page and overrides whatever aria-current is passed in
              — measured landing on /notlar, where the tab needs to read
              current while its own href never matches the path.
            */}
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
