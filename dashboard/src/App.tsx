import { useEffect, useState } from 'react'
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { Content, SideNav, SideNavItems, SideNavLink } from '@carbon/react'
import DashboardHeader from './components/DashboardHeader'
import ReaderHeader, { ReaderFooter } from './components/ReaderChrome'
import DashboardFooter from './components/DashboardFooter'
import LoginPage from './components/LoginPage'
import { SessionContext } from './contexts/session'
import { useAuth } from './hooks/useAuth'
import { useFocusMode } from './contexts/focusMode'
import { activateReaderProfile, useBookProgressSync } from './hooks/useBookReader'
import { routesFor, navRoutesFor, ROLE_HOME, redirects } from './routes'
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
import Announcements from './components/Announcements'
import StudentProfile from './components/StudentProfile'
import ExamTimeline from './components/ExamTimeline'
import TedyBooks, { BookDetail } from './components/TedyBooks'
import BookReader from './components/BookReader'

const COMPONENTS: Record<string, React.ComponentType> = {
  TodaySchedule, WeeklySchedule, HomeworkTracker, AssistantChat, GradeTable, ExamTimeline,
  PlatformProgress, CalendarEvents, TeamActivities, CourseContent, Announcements, StudentProfile,
  TedyBooks, BookDetail, BookReader,
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
        isRail
        expanded={sideNavExpanded}
        onOverlayClick={() => setSideNavExpanded(false)}
        onSideNavBlur={() => setSideNavExpanded(false)}
        isChildOfHeader
      >
        <SideNavItems>
          {navItems.map(r => (
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
        {/* Readers are refused /api/health, so the banner is not theirs to fetch. */}
        {!isReader && <PortalStatusBanner />}
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
      </Content>
      {isReader ? <ReaderFooter /> : <DashboardFooter />}
    </SessionContext.Provider>
  )
}
