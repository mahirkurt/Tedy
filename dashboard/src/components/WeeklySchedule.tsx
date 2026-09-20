import { Calendar } from '@carbon/icons-react'
import {
  DataTable, Table, TableHead, TableRow, TableHeader,
  TableBody, TableCell, TableContainer,
} from '@carbon/react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import { cleanTeacherNames, normalizeCourseDisplayName } from '../utils/formatters'
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

  if (loading) return <div className="dashboard-card">Yükleniyor...</div>

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
  // The portal writes the days in caps ("PAZARTESI"), and this matched them
  // with `indexOf('Pazartesi')` — so no column ever matched and the timetable
  // rendered as a column of times with no lessons beside it. Not a Turkish
  // locale uppercase either: that maps "Pazartesi" to "PAZARTESİ" with a
  // dotted İ while the portal writes a dotless one, so Monday — the one day
  // with an i — still failed and every lesson shifted a column left. Pairing
  // the day with its column index also fixes the alignment: the old code
  // filtered the index list, so one missing day shifted every day after it.
  const norm = (s: string) => (s || '').trim().toUpperCase().replace(/İ/g, 'I')
  const dayCols = DAYS
    .map(day => ({ day, idx: dayHeaders.findIndex(h => norm(h) === norm(day)) }))
    .filter(d => d.idx >= 0)

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
      dayCols.forEach(({ day, idx }) => {
        rowData[day] = row[idx] || ''
      })
      return rowData
    })
    .filter(Boolean) as { id: string; [key: string]: string }[]

  return (
    <div className="dashboard-card">
      <div className="schedule-table">
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
                  const rawTime = tableRows.find(r => r.id === row.id)?._timeRaw || ''
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
