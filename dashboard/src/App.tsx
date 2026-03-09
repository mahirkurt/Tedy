import { Grid, Column, Content } from '@carbon/react'
import DashboardHeader from './components/DashboardHeader'
import TodaySchedule from './components/TodaySchedule'
import WeeklySchedule from './components/WeeklySchedule'
import HomeworkTracker from './components/HomeworkTracker'
import GradeTable from './components/GradeTable'
import PlatformProgress from './components/PlatformProgress'
import CalendarEvents from './components/CalendarEvents'
import TeamActivities from './components/TeamActivities'
import CourseContent from './components/CourseContent'
import Announcements from './components/Announcements'
import LoginPage from './components/LoginPage'
import { useAuth } from './hooks/useAuth'

export default function App() {
  const { user, loading, login, logout } = useAuth()

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        backgroundColor: '#F4F4F4',
      }}>
        <p style={{ color: '#525252' }}>Yükleniyor...</p>
      </div>
    )
  }

  if (!user) {
    return <LoginPage onLogin={login} />
  }

  return (
    <>
      <DashboardHeader user={user} onLogout={logout} />
      <Content style={{ padding: '3.5rem 1.5rem 2rem' }}>
        <Grid fullWidth>
          <Column lg={16} md={8} sm={4}>
            <TodaySchedule />
          </Column>

          <Column lg={16} md={8} sm={4}>
            <WeeklySchedule />
          </Column>

          <Column lg={10} md={8} sm={4}>
            <HomeworkTracker />
          </Column>
          <Column lg={6} md={8} sm={4}>
            <GradeTable />
          </Column>

          <Column lg={8} md={4} sm={4}>
            <PlatformProgress />
          </Column>
          <Column lg={8} md={4} sm={4}>
            <CalendarEvents />
          </Column>

          <Column lg={8} md={4} sm={4}>
            <TeamActivities />
          </Column>
          <Column lg={8} md={4} sm={4}>
            <CourseContent />
          </Column>

          <Column lg={16} md={8} sm={4}>
            <Announcements />
          </Column>
        </Grid>
      </Content>
    </>
  )
}
