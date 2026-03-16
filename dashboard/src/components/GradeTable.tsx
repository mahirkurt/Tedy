import { useApi } from '../hooks/useApi'
import { Certificate } from '@carbon/icons-react'
import {
  DataTable, Table, TableHead, TableRow, TableHeader,
  TableBody, TableCell, TableContainer,
  TableExpandRow, TableExpandedRow, TableExpandHeader,
} from '@carbon/react'
import type { GradeItem } from '../types'
import { gradeColor } from '../utils/formatters'
import { useFocusMode } from '../contexts/FocusModeContext'

const COLS = ['1. Sınav', '2. Sınav', '3. Sınav', 'DİKP/Performans-1', 'DİKP/Performans-2', 'DİKP/Performans-3'] as const
const COL_SHORT = ['S1', 'S2', 'S3', 'P1', 'P2', 'P3']

const headers = [
  { key: 'ders', header: 'Ders' },
  ...COL_SHORT.map(c => ({ key: c, header: c })),
]

export default function GradeTable() {
  const { data } = useApi<{ semester?: string; grades?: GradeItem[] }>(
    '/api/grades', {}
  )
  const { focusMode } = useFocusMode()

  const grades = data.grades || []

  const tableRows = grades.map((g, i) => ({
    id: String(i),
    ders: g.Ders,
    ...Object.fromEntries(COL_SHORT.map((short, ci) => [short, g[COLS[ci]] || '-'])),
    _raw: g,
  }))

  return (
    <div className="dashboard-card">
      <TableContainer
        title={
          <span className="dashboard-card__title dashboard-card__title--tight">
            <Certificate size={20} />
            Notlar &mdash; {data.semester || ''}
          </span>
        }
      >
        <DataTable rows={tableRows} headers={headers} size="sm">
          {({ rows: dtRows, headers: dtHeaders, getTableProps, getHeaderProps, getRowProps, getExpandHeaderProps }) => (
            <Table {...getTableProps()}>
              <TableHead>
                <TableRow>
                  {!focusMode && <TableExpandHeader {...getExpandHeaderProps()} />}
                  {dtHeaders.map(header => (
                    <TableHeader
                      {...getHeaderProps({ header })}
                      key={header.key}
                      className={header.key !== 'ders' ? 'grade-col-center' : ''}
                    >
                      {header.header}
                    </TableHeader>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {dtRows.map(row => {
                  const rawGrade = tableRows.find(r => r.id === row.id)?._raw
                  return focusMode ? (
                    <TableRow {...getRowProps({ row })} key={row.id}>
                      {row.cells.map(cell => {
                        const isGrade = cell.info.header !== 'ders'
                        const val = String(cell.value || '')
                        const color = isGrade ? gradeColor(val) : ''
                        return (
                          <TableCell
                            key={cell.id}
                            className={isGrade ? 'grade-col-center' : ''}
                            style={isGrade && color ? {
                              fontWeight: 600,
                              color,
                              backgroundColor: val !== '-' ? `${color}11` : undefined,
                            } : isGrade ? { fontWeight: 600 } : { fontWeight: 500 }}
                          >
                            {val}
                          </TableCell>
                        )
                      })}
                    </TableRow>
                  ) : (
                    <GradeExpandRow key={row.id} row={row} rawGrade={rawGrade} getRowProps={getRowProps} />
                  )
                })}
              </TableBody>
            </Table>
          )}
        </DataTable>
      </TableContainer>
    </div>
  )
}

function GradeExpandRow({ row, rawGrade, getRowProps }: {
  row: any
  rawGrade: GradeItem | undefined
  getRowProps: (opts: { row: any }) => any
}) {
  return (
    <>
      <TableExpandRow {...getRowProps({ row })}>
        {row.cells.map((cell: any) => {
          const isGrade = cell.info.header !== 'ders'
          const val = String(cell.value || '')
          const color = isGrade ? gradeColor(val) : ''
          return (
            <TableCell
              key={cell.id}
              className={isGrade ? 'grade-col-center' : ''}
              style={isGrade && color ? {
                fontWeight: 600,
                color,
                backgroundColor: val !== '-' ? `${color}11` : undefined,
              } : isGrade ? { fontWeight: 600 } : { fontWeight: 500 }}
            >
              {val}
            </TableCell>
          )
        })}
      </TableExpandRow>
      <TableExpandedRow colSpan={headers.length + 1}>
        <div className="grade-detail">
          {COLS.map((col, ci) => {
            const val = rawGrade?.[col] || '-'
            const color = gradeColor(val)
            const numVal = parseInt(val)
            const barWidth = !isNaN(numVal) ? numVal : 0
            return (
              <div key={ci} className="grade-detail__row">
                <span className="grade-detail__label">{col}</span>
                <div className="grade-detail__bar-track">
                  <div
                    className="grade-detail__bar-fill"
                    style={{
                      width: `${barWidth}%`,
                      backgroundColor: color || '#c6c6c6',
                    }}
                  />
                </div>
                <span className="grade-detail__value" style={{ color: color || undefined }}>
                  {val}
                </span>
              </div>
            )
          })}
        </div>
      </TableExpandedRow>
    </>
  )
}
