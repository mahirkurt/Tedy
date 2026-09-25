import { Calendar } from '@carbon/icons-react'
import {
  DataTable, Table, TableHead, TableRow, TableHeader,
  TableBody, TableCell, TableContainer, SkeletonText,
} from '@carbon/react'
import { useEffect, useRef } from 'react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import { cleanTeacherNames, normalizeCourseDisplayName } from '../utils/formatters'
import { dayColumns } from '../utils/schedule'
import { EmptyLine } from './patterns/EmptyLine'

interface ScheduleWeek {
  week_label?: string
  is_current?: boolean
  schedule?: { rows: string[][] }
}

interface ScheduleData {
  latest: ScheduleWeek
  today: string
}

const DAYS = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma']

const SKIP_CONTENT = new Set([
  'Kahvaltı', 'Öğle yemeği', 'İkindi Kahvaltısı', 'Çıkış'
])

function formatTime(cell: string): string {
  const periodMatch = cell.match(/(\d+)\. Ders/)
  const timeMatch = cell.match(/(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})/)
  if (periodMatch && timeMatch) return `${periodMatch[1]}. ${timeMatch[1]}`
  const justTime = cell.match(/(\d{2}:\d{2})/)
  return justTime ? justTime[1] : cell
}

function isCurrentPeriod(timeCell: string): boolean {
  const timeMatch = timeCell.match(/(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})/)
  if (!timeMatch) return false
  const now = new Date()
  const nowMin = now.getHours() * 60 + now.getMinutes()
  const startMin = +timeMatch[1] * 60 + +timeMatch[2]
  const endMin = +timeMatch[3] * 60 + +timeMatch[4]
  return nowMin >= startMin && nowMin < endMin
}

export default function WeeklySchedule() {
  const { data, loading } = useApi<ScheduleData>(
    '/api/schedule',
    { latest: {}, today: '' }
  )
  const { focusMode } = useFocusMode()
  const kapRef = useRef<HTMLDivElement>(null)

  // On a phone Carbon's table container scrolls the grid sideways, and a
  // scroll region has to be reachable by keyboard and named (axe
  // scrollable-region-focusable). The container is Carbon's own element, so
  // it is found after render rather than given props.
  useEffect(() => {
    const kap = kapRef.current?.querySelector<HTMLElement>('.cds--data-table-content')
    if (!kap) return
    kap.tabIndex = 0
    kap.setAttribute('role', 'region')
    kap.setAttribute('aria-label', 'Haftalık program tablosu')
  })

  // Carbon's skeleton in the content's shape (surface designs §2.4), not a
  // bare "Yükleniyor..." line.
  if (loading) {
    return (
      <div className="dashboard-card">
        <SkeletonText heading width="40%" />
        <SkeletonText paragraph lineCount={6} />
      </div>
    )
  }

  // No week picker. The portal offers 36 weeks and every one of them renders
  // the identical grid — a school timetable repeats — so the API's `latest`
  // (the week the scraper saw selected) is the only week there is to show.
  // Week-to-week variation lives in the course content below.
  const week = data.latest || {}
  const rows = week.schedule?.rows || []
  if (rows.length === 0) {
    return <EmptyLine label="Haftalık Program">Bu hafta için ders programı yok.</EmptyLine>
  }

  const dayHeaders = rows[0] || []
  // Matching the caps the portal writes, and pairing each day with its own
  // time column — see utils/schedule.ts for what both cost when they are
  // assumed instead.
  const dayCols = dayColumns(dayHeaders, DAYS)

  const headers = [
    { key: 'time', header: 'Saat' },
    ...dayCols.map(d => ({ key: d.day, header: d.day })),
  ]

  const tableRows = rows.slice(1)
    .map((row, ri) => {
      const timeCell = row[0] || ''
      if (!timeCell) return null
      const isBreak = row.some(c => SKIP_CONTENT.has(c))
      if (isBreak || timeCell.includes('Çıkış') || SKIP_CONTENT.has(timeCell)) return null

      const rowData: { id: string; [key: string]: string } = {
        id: String(ri),
        time: formatTime(timeCell),
        _timeRaw: timeCell,
      }
      dayCols.forEach(({ day, idx, timeIdx }) => {
        rowData[day] = row[idx] || ''
        // One Saat column cannot speak for two bell schedules. Where a day
        // runs on its own — Friday, five to ten minutes later than Monday
        // through Thursday — the cell carries its own start time, so the
        // shared column never quietly misstates it.
        const ownCell = row[timeIdx] || ''
        rowData[`${day}__saat`] = formatTime(ownCell) === rowData.time
          ? ''
          : ownCell.match(/(\d{2}:\d{2})/)?.[1] || ''
      })
      return rowData
    })
    .filter(Boolean) as { id: string; [key: string]: string }[]

  return (
    <div className="dashboard-card">
      <div className="schedule-table" ref={kapRef}>
      <TableContainer
        title={
          <span className="dashboard-card__title dashboard-card__title--tight">
            <Calendar size={20} />
            Haftalık Program &mdash; {week.week_label || ''}
          </span>
        }
      >
        <DataTable rows={tableRows} headers={headers} size="xs">
          {({ rows: dtRows, headers: dtHeaders, getTableProps, getHeaderProps, getRowProps }) => (
            <Table {...getTableProps()}>
              <TableHead>
                <TableRow>
                  {dtHeaders.map(header => (
                    <TableHeader
                      {...getHeaderProps({ header })}
                      key={header.key}
                      className={header.key === data.today ? 'today-column' : ''}
                    >
                      {header.header}
                    </TableHeader>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {dtRows.map(row => {
                  const kaynak = tableRows.find(r => r.id === row.id)
                  const rawTime = kaynak?._timeRaw || ''
                  const active = isCurrentPeriod(rawTime)
                  return (
                    <TableRow
                      {...getRowProps({ row })}
                      key={row.id}
                      className={active ? 'lesson-active' : ''}
                    >
                      {row.cells.map(cell => {
                        const isToday = cell.info.header === data.today
                        const isTime = cell.info.header === 'time'
                        const cellValue = String(cell.value || '')
                        const lines = cellValue.split('\n')

                        return (
                          <TableCell
                            key={cell.id}
                            className={isToday ? 'today-column' : ''}
                          >
                            {isTime ? (
                              <span className="schedule-time">{cellValue}</span>
                            ) : lines[0] ? (
                              <>
                                {kaynak?.[`${cell.info.header}__saat`] && (
                                  <span className="schedule-own-time">
                                    {kaynak[`${cell.info.header}__saat`]}
                                  </span>
                                )}
                                <span className="schedule-lesson">{normalizeCourseDisplayName(lines[0].trim())}</span>
                                {!focusMode && lines[1] && (
                                  <span className="schedule-detail">
                                    {cleanTeacherNames(lines.slice(1).join('\n'))}
                                  </span>
                                )}
                              </>
                            ) : null}
                          </TableCell>
                        )
                      })}
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </DataTable>
      </TableContainer>
      </div>
    </div>
  )
}
