import { Time, Calendar, Task, Certificate, EventSchedule, ExamMode,
         GroupPresentation, Book, Catalog, ChartBar, Notification, UserAvatar } from '@carbon/icons-react'
import type { ComponentType } from 'react'
import type { UserRole } from './hooks/useAuth'

export interface RouteConfig {
  path: string
  label: string
  icon: ComponentType
  componentName: string
  /** Nested/detail routes are routable but stay out of the side navigation. */
  showInNav?: boolean
  /**
   * Reachable by "reader" accounts. Default-deny: a route without this flag is
   * for full-access accounts only, so a new page never leaks by omission.
   */
  readerAccess?: boolean
}

export const routes: RouteConfig[] = [
  { path: '/',          label: 'Bugün',      icon: Time,              componentName: 'TodaySchedule' },
  { path: '/program',   label: 'Program',    icon: Calendar,          componentName: 'WeeklySchedule' },
  { path: '/odevler',   label: 'Ödevler',    icon: Task,              componentName: 'HomeworkTracker' },
  { path: '/asistan',   label: 'Asistan',    icon: Notification,      componentName: 'AssistantChat' },
  { path: '/notlar',    label: 'Notlar',     icon: Certificate,       componentName: 'GradeTable' },
  { path: '/sinavlar',  label: 'Sınavlar',   icon: ExamMode,          componentName: 'ExamTimeline' },
  { path: '/takvim',    label: 'Takvim',     icon: EventSchedule,     componentName: 'CalendarEvents' },
  { path: '/takimlar',  label: 'Takımlar',   icon: GroupPresentation, componentName: 'TeamActivities' },
  { path: '/dersler',   label: 'Dersler',    icon: Catalog,           componentName: 'CourseContent' },
  { path: '/kitaplar',  label: 'Tedy Books', icon: Book,              componentName: 'TedyBooks', readerAccess: true },
  { path: '/ilerleme',  label: 'İlerleme',   icon: ChartBar,          componentName: 'PlatformProgress' },
  { path: '/duyurular', label: 'Duyurular',  icon: Notification,      componentName: 'Announcements' },
  { path: '/profil',    label: 'Profil',     icon: UserAvatar,        componentName: 'StudentProfile' },

  { path: '/kitaplar/:slug',             label: 'Kitap',  icon: Book, componentName: 'BookDetail', showInNav: false, readerAccess: true },
  { path: '/kitaplar/:slug/:chapterId',  icon: Book, label: 'Okuma', componentName: 'BookReader', showInNav: false, readerAccess: true },
]

export const navRoutes = routes.filter(r => r.showInNav !== false)

/** Where a role lands when it opens the app or asks for a page it cannot see. */
export const ROLE_HOME: Record<UserRole, string> = {
  full: '/',
  reader: '/kitaplar',
}

export function routesFor(role: UserRole): RouteConfig[] {
  return role === 'full' ? routes : routes.filter(r => r.readerAccess)
}

export function navRoutesFor(role: UserRole): RouteConfig[] {
  return routesFor(role).filter(r => r.showInNav !== false)
}
