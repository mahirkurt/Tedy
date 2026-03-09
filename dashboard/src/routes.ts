import { Time, Calendar, Task, Certificate, EventSchedule,
         GroupPresentation, Book, ChartBar, Notification } from '@carbon/icons-react'
import type { ComponentType } from 'react'

export interface RouteConfig {
  path: string
  label: string
  icon: ComponentType
  componentName: string
}

export const routes: RouteConfig[] = [
  { path: '/',          label: 'Bugün',     icon: Time,              componentName: 'TodaySchedule' },
  { path: '/program',   label: 'Program',   icon: Calendar,          componentName: 'WeeklySchedule' },
  { path: '/odevler',   label: 'Ödevler',   icon: Task,              componentName: 'HomeworkTracker' },
  { path: '/notlar',    label: 'Notlar',    icon: Certificate,       componentName: 'GradeTable' },
  { path: '/takvim',    label: 'Takvim',    icon: EventSchedule,     componentName: 'CalendarEvents' },
  { path: '/takimlar',  label: 'Takımlar',  icon: GroupPresentation,  componentName: 'TeamActivities' },
  { path: '/dersler',   label: 'Dersler',   icon: Book,              componentName: 'CourseContent' },
  { path: '/ilerleme',  label: 'İlerleme',  icon: ChartBar,          componentName: 'PlatformProgress' },
  { path: '/duyurular', label: 'Duyurular', icon: Notification,      componentName: 'Announcements' },
]
