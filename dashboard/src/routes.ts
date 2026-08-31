import { Time, Task, Certificate, EventSchedule, ExamMode,
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
   * Reachable, but not one of the five things worth deciding between before
   * doing anything. Grouped under "Daha fazla" rather than competing for the
   * same glance (design principles İ1).
   */
  secondary?: boolean
  /**
   * Reachable by "reader" accounts. Default-deny: a route without this flag is
   * for full-access accounts only, so a new page never leaks by omission.
   */
  readerAccess?: boolean
}

export const routes: RouteConfig[] = [
  { path: '/',          label: 'Bugün',      icon: Time,              componentName: 'TodaySchedule' },
  { path: '/isler',     label: 'İşler',      icon: Task,              componentName: 'HomeworkTracker' },
  { path: '/asistan',   label: 'Asistan',    icon: Notification,      componentName: 'AssistantChat' },
  { path: '/notlar',    label: 'Notlar',     icon: Certificate,       componentName: 'GradeTable' , secondary: true },

  { path: '/takvim',    label: 'Takvim',     icon: EventSchedule,     componentName: 'CalendarEvents' , secondary: true },
  { path: '/takimlar',  label: 'Takımlar',   icon: GroupPresentation, componentName: 'TeamActivities' , secondary: true },
  { path: '/dersler',   label: 'Dersler',    icon: Catalog,           componentName: 'Lessons' },
  { path: '/kitaplar',  label: 'Tedy Books', icon: Book,              componentName: 'TedyBooks', readerAccess: true },
  { path: '/ilerleme',  label: 'İlerleme',   icon: ChartBar,          componentName: 'PlatformProgress' , secondary: true },
  { path: '/duyurular', label: 'Duyurular',  icon: Notification,      componentName: 'Announcements' , secondary: true },
  { path: '/profil',    label: 'Profil',     icon: UserAvatar,        componentName: 'StudentProfile' , secondary: true },

  // Exams keep a page of their own: grades, past papers and study guides are
  // real content, and folding them into a section would lose them. What they
  // give up is a slot in the primary navigation — the work ahead is surfaced
  // inside İşler, which is where Işık goes to see what she owes.
  { path: '/sinavlar',  label: 'Sınavlar',   icon: ExamMode, componentName: 'ExamTimeline', showInNav: false },

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

/** Paths that moved. Bookmarks and old links redirect rather than 404. */
export const redirects: Record<string, string> = {
  '/odevler': '/isler',
  '/program': '/dersler',
}
