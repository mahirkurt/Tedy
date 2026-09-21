import { useEffect, useState } from 'react'
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { Content, SideNav, SideNavItems, SideNavMenu, SideNavMenuItem, SideNavLink } from '@carbon/react'
import { OverflowMenuHorizontal } from '@carbon/icons-react'
import DashboardHeader from './components/DashboardHeader'
import ReaderHeader, { ReaderFooter } from './components/ReaderChrome'
import DashboardFooter from './components/DashboardFooter'
import LoginPage from './components/LoginPage'
import { SessionContext } from './contexts/session'
import { useAuth } from './hooks/useAuth'
import { useFocusMode } from './contexts/focusMode'
import { activateReaderProfile, useBookProgressSync } from './hooks/useBookReader'
import { routesFor, navRoutesFor, ROLE_HOME, redirects } from './routes'
import RouteBoundary from './components/RouteBoundary'
import { PortalStatusBanner } from './components/PortalStatusBanner'

import TodaySchedule from './components/TodaySchedule'
import WeeklySchedule from './components/WeeklySchedule'
import HomeworkTracker from './components/HomeworkTracker'
import AssistantChat from './components/AssistantChat'
import GradeTable from './components/GradeTable'
import PlatformProgress from './components/PlatformProgress'
import CalendarEvents from './components/CalendarEvents'
import TeamActivities from './components/TeamActivities'
import CourseContent from './components/CourseContent'
import Lessons from './components/Lessons'
import Announcements from './components/Announcements'
import StudentProfile from './components/StudentProfile'
import ExamTimeline from './components/ExamTimeline'
import TedyBooks, { BookDetail } from './components/TedyBooks'
import BookReader from './components/BookReader'
import Modules, { ModuleViewerRoute, DraftViewerRoute } from './components/Modules'

function matchRoute(pathname: string, list: ReturnType<typeof routesFor>) {
  const exact = list.find(r => r.path === pathname)
  if (exact) return exact
  return [...list]
    .filter(r => r.path.includes(':'))
    .sort((a, b) => b.path.length - a.path.length)
    .find(r => {
      const prefix = r.path.split('/:')[0]
      return pathname === prefix || pathname.startsWith(`${prefix}/`)
    })
}

const COMPONENTS: Record<string, React.ComponentType> = {
  Lessons,
  TodaySchedule, WeeklySchedule, HomeworkTracker, AssistantChat, GradeTable, ExamTimeline,
  PlatformProgress, CalendarEvents, TeamActivities, CourseContent, Announcements, StudentProfile,
  TedyBooks, BookDetail, BookReader,
  Modules, ModuleViewerRoute, DraftViewerRoute,
}

export default function App() {
  const { user, loading, login, logout } = useAuth()
  const { focusMode } = useFocusMode()
  const [sideNavExpanded, setSideNavExpanded] = useState(false)
  const location = useLocation()

  // Before any reader screen renders, so the first read already hits this
  // profile's storage rather than the previous occupant's.
  activateReaderProfile(user?.email, { inheritLegacy: user?.role === 'full' })
  useBookProgressSync(user?.email)

  // The reader's ground is paper, not Carbon grey — and that has to reach the
  // body, which sits above this component.
  useEffect(() => {
    const root = document.documentElement
    if (user) root.dataset.role = user.role
    else delete root.dataset.role
    return () => { delete root.dataset.role }
  }, [user])

  useEffect(() => {
    const root = document.documentElement
    if (focusMode) root.dataset.focus = 'on'
    else delete root.dataset.focus
    return () => { delete root.dataset.focus }
  }, [focusMode])

  if (loading) {
    return (
      <div className="app-shell-loading">
        <p className="app-shell-loading__text">Yükleniyor...</p>
      </div>
    )
  }

  if (!user) {
    return <LoginPage onLogin={login} />
  }

  const visibleRoutes = routesFor(user.role)
  const navItems = navRoutesFor(user.role)
  const home = ROLE_HOME[user.role]
  const isReader = user.role === 'reader'
  // The nav already names every route; the page heading reuses that name
  // rather than inventing a second vocabulary for the same place.
  const matchedRoute = matchRoute(location.pathname, visibleRoutes)
  const pageTitle = matchedRoute?.label ?? 'TEDY'
  // Book surfaces already typeset their own visible h1 (Kitaplık / title /
  // chapter). A second, hidden one made the outline read "Tedy Books" then
  // "Kitaplık", or fell back to "TEDY" on /kitaplar/:slug.
  const isBookSurface = location.pathname === '/kitaplar'
    || location.pathname.startsWith('/kitaplar/')
  // The portal-closed banner names Ders Programı and Takvim. Anywhere else
  // it is the same sentence on a page that does not show those sections (İ6).
  // The closed-portal sentence still belongs only to the two pages that show
  // those sections; the banner decides that for itself now, because it also
  // carries the "could not be read" warning, which belongs on whichever page
  // the unread section would have filled.
  const showPortalBanner = !isReader && !focusMode

  return (
    <SessionContext.Provider value={user}>
      {isReader ? (
        <ReaderHeader user={user} onLogout={logout} />
      ) : (
        <DashboardHeader
          user={user}
          onLogout={logout}
          isSideNavExpanded={sideNavExpanded}
          onClickSideNavExpand={() => setSideNavExpanded(p => !p)}
        />
      )}
      {navItems.length > 1 && (
      <SideNav
        aria-label="Navigasyon"
        expanded={sideNavExpanded}
        onOverlayClick={() => setSideNavExpanded(false)}
        onSideNavBlur={() => setSideNavExpanded(false)}
        isChildOfHeader
      >
        <SideNavItems>
          {navItems.filter(r => !r.secondary).map(r => (
            <SideNavLink
              key={r.path}
              as={NavLink}
              to={r.path}
              renderIcon={r.icon}
              isActive={location.pathname === r.path}
              onClick={() => setSideNavExpanded(false)}
            >
              {r.label}
            </SideNavLink>
          ))}
          {/* Everything reachable but not worth a decision before doing
              anything sits one level down (İ1). */}
          {!focusMode && navItems.some(r => r.secondary) && (
            <SideNavMenu
              title="Daha fazla"
              renderIcon={OverflowMenuHorizontal}
              defaultExpanded={navItems.some(
                r => r.secondary && location.pathname === r.path)}
            >
              {navItems.filter(r => r.secondary).map(r => (
                <SideNavMenuItem
                  key={r.path}
                  as={NavLink}
                  to={r.path}
                  isActive={location.pathname === r.path}
                  onClick={() => setSideNavExpanded(false)}
                >
                  {r.label}
                </SideNavMenuItem>
              ))}
            </SideNavMenu>
          )}
        </SideNavItems>
      </SideNav>
      )}
      {sideNavExpanded && (
        <button
          type="button"
          className="app-shell-nav-scrim"
          aria-label="Menüyü kapat"
          onClick={() => setSideNavExpanded(false)}
        />
      )}
      <Content
        className={[
          'app-shell-content',
          focusMode ? 'app-shell-content--focus' : '',
          isReader ? 'app-shell-content--reader' : '',
        ].filter(Boolean).join(' ')}
      >
        {/* Readers are refused /api/health. Everyone else only sees this
            on the two pages that actually render those portal sections. */}
        {showPortalBanner && <PortalStatusBanner pathname={location.pathname} />}
        {/* Named for assistive technology, which otherwise finds no page
            title at all: every surface used to open its heading outline
            with a card title, or with a closed modal's heading. It stays
            invisible because the surface below already announces itself. */}
        {!isBookSurface && (
          <h1 className="cds--visually-hidden">{pageTitle}</h1>
        )}
        <RouteBoundary resetKey={location.pathname}>
        <Routes>
          {visibleRoutes.map(r => {
            const Comp = COMPONENTS[r.componentName]
            return <Route key={r.path} path={r.path} element={<Comp />} />
          })}
          {/* Paths that moved keep working. */}
          {Object.entries(redirects).map(([from, to]) => (
            <Route key={from} path={from} element={<Navigate to={to} replace />} />
          ))}
          {/* Anything this role cannot see resolves to its own home. */}
          <Route path="*" element={<Navigate to={home} replace />} />
        </Routes>
        </RouteBoundary>
      </Content>
      {isReader ? <ReaderFooter /> : <DashboardFooter />}
    </SessionContext.Provider>
  )
}
