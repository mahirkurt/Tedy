import { useState } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { Content, SideNav, SideNavItems, SideNavLink } from '@carbon/react'
import DashboardHeader from './components/DashboardHeader'
import LoginPage from './components/LoginPage'
import { useAuth } from './hooks/useAuth'
import { routes } from './routes'

import TodaySchedule from './components/TodaySchedule'
import WeeklySchedule from './components/WeeklySchedule'
import HomeworkTracker from './components/HomeworkTracker'
import GradeTable from './components/GradeTable'
import PlatformProgress from './components/PlatformProgress'
import CalendarEvents from './components/CalendarEvents'
import TeamActivities from './components/TeamActivities'
import CourseContent from './components/CourseContent'
import Announcements from './components/Announcements'

const COMPONENTS: Record<string, React.ComponentType> = {
  TodaySchedule, WeeklySchedule, HomeworkTracker, GradeTable,
  PlatformProgress, CalendarEvents, TeamActivities, CourseContent, Announcements,
}

export default function App() {
  const { user, loading, login, logout } = useAuth()
  const [sideNavExpanded, setSideNavExpanded] = useState(false)
  const location = useLocation()

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

  return (
    <>
      <DashboardHeader
        user={user}
        onLogout={logout}
        isSideNavExpanded={sideNavExpanded}
        onClickSideNavExpand={() => setSideNavExpanded(p => !p)}
      />
      <SideNav
        aria-label="Navigasyon"
        isRail
        expanded={sideNavExpanded}
        onOverlayClick={() => setSideNavExpanded(false)}
        onSideNavBlur={() => setSideNavExpanded(false)}
        isChildOfHeader
      >
        <SideNavItems>
          {routes.map(r => (
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
      <Content className="app-shell-content">
        <Routes>
          {routes.map(r => {
            const Comp = COMPONENTS[r.componentName]
            return <Route key={r.path} path={r.path} element={<Comp />} />
          })}
        </Routes>
      </Content>
    </>
  )
}
