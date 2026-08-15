import { Time, Calendar, Task, Certificate, EventSchedule, ExamMode,
         GroupPresentation, Book, Catalog, ChartBar, Notification, UserAvatar } from '@carbon/icons-react'
import type { ComponentType } from 'react'

export interface RouteConfig {
  path: string
  label: string
  icon: ComponentType
  componentName: string
  /** Nested/detail routes are routable but stay out of the side navigation. */
  showInNav?: boolean
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
  { path: '/kitaplar',  label: 'Tedy Books', icon: Book,              componentName: 'TedyBooks' },
  { path: '/ilerleme',  label: 'İlerleme',   icon: ChartBar,          componentName: 'PlatformProgress' },
  { path: '/duyurular', label: 'Duyurular',  icon: Notification,      componentName: 'Announcements' },
  { path: '/profil',    label: 'Profil',     icon: UserAvatar,        componentName: 'StudentProfile' },

  { path: '/kitaplar/:slug',             label: 'Kitap',  icon: Book, componentName: 'BookDetail', showInNav: false },
  { path: '/kitaplar/:slug/:chapterId',  icon: Book, label: 'Okuma', componentName: 'BookReader', showInNav: false },
]

export const navRoutes = routes.filter(r => r.showInNav !== false)
