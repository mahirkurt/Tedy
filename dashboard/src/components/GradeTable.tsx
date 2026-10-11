import type { ComponentProps } from 'react'
import { useApi } from '../hooks/useApi'
import { EmptyLine } from './patterns/EmptyLine'
import { Certificate, Information } from '@carbon/icons-react'
import {
  DataTable, Table, TableHead, TableRow, TableHeader,
  TableBody, TableCell, TableContainer,
  TableExpandRow, TableExpandedRow, TableExpandHeader, Tag,
} from '@carbon/react'
import type { GradeItem } from '../types'
import { useFocusMode } from '../contexts/focusMode'

/* Row and prop-getter shapes come from Carbon's own render-prop signature, so
   the expanded-row helper stays in step with the library instead of guessing. */
type DataTableRenderArgs = Parameters<
  NonNullable<ComponentProps<typeof DataTable>['children']>
>[0]
type GradeDataTableRow = DataTableRenderArgs['rows'][number]
type GetRowProps = DataTableRenderArgs['getRowProps']

const COLS = ['1. Sınav', '2. Sınav', '3. Sınav', 'DİKP/Performans-1', 'DİKP/Performans-2', 'DİKP/Performans-3'] as const
const COL_SHORT = ['S1', 'S2', 'S3', 'P1', 'P2', 'P3']

/** A grade cell's text (S42, B72): the figure as it is, one neutral colour; a missing grade is an em dash with
 *  its meaning for a screen reader — never a 0-wide bar or a hyphen that reads as "minus". */
function NotDegeri({ deger }: { deger: string }) {
  const bos = !deger || deger === '-'
  if (bos) return <><span aria-hidden="true">—</span><span className="cds--visually-hidden">Not girilmedi</span></>
  return <span className="tedy-time">{deger}</span>
}

const headers = [
  { key: 'ders', header: 'Ders' },
  ...COL_SHORT.map(c => ({ key: c, header: c })),
]

// Carbon's default is the English "Expand current row". The column header
// already calls this Ayrıntı; the row button should use the same word.
function tabloDili(id: string): string {
  switch (id) {
    case 'carbon.table.row.expand': return 'Ayrıntı'
    case 'carbon.table.row.collapse': return 'Ayrıntıyı gizle'
    case 'carbon.table.all.expand': return 'Tüm ayrıntıları aç'
    case 'carbon.table.all.collapse': return 'Tüm ayrıntıları gizle'
    default: return id
  }
}

export default function GradeTable() {
  // priorYear: the report's term names an earlier school year than the one
  // TEDY is in (/api/grades, the check /api/exams and the assistant make).
  const { data } = useApi<{ semester?: string; grades?: GradeItem[]; priorYear?: boolean }>(
    '/api/grades', {}
  )
  const { focusMode } = useFocusMode()

  const grades = data.grades || []

  // A header row with nothing under it looks like a table whose rows failed
  // to load. Say the thing instead (D3).
  if (grades.length === 0) {
    return (
      <EmptyLine label="Notlar">
        {data.semester
          ? `${data.semester} döneminde henüz not girilmemiş.`
          : 'Henüz not girilmemiş.'}
      </EmptyLine>
    )
  }

  const tableRows = grades.map((g, i) => ({
    id: String(i),
    ders: g.Ders,
    ...Object.fromEntries(COL_SHORT.map((short, ci) => [short, g[COLS[ci]] || '-'])),
    _raw: g,
  }))

  return (
    <div className="dashboard-card grade-table">
      <TableContainer
        title={
          <span className="dashboard-card__title dashboard-card__title--tight">
            <Certificate size={20} />
            {data.semester ? `Notlar — ${data.semester}` : 'Notlar'}
            {/* Grey and small: a fact about the table, not an alarm (İ6).
                A span, because it sits inside the table's heading. */}
            {data.priorYear && (
              <Tag as="span" type="gray" size="sm"><Information size={16} /> Önceki öğretim yılı</Tag>
            )}
          </span>
        }
      >
        <DataTable rows={tableRows} headers={headers} size="sm" translateWithId={tabloDili}>
          {({ rows: dtRows, headers: dtHeaders, getTableProps, getHeaderProps, getRowProps, getExpandHeaderProps }) => (
            <Table {...getTableProps()} aria-label="Notlar">
              <TableHead>
                <TableRow>
                  {/* A header cell with no text is a blank column to a screen reader (axe). */}
                  {!focusMode && (
                    <TableExpandHeader {...getExpandHeaderProps()}>
                      <span className="cds--visually-hidden">Ayrıntı</span>
                    </TableExpandHeader>
                  )}
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
                        return (
                          <TableCell key={cell.id} className={isGrade ? 'grade-col-center grade-cell' : ''}>
                            {isGrade ? <NotDegeri deger={val} /> : val}
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
  row: GradeDataTableRow
  rawGrade: GradeItem | undefined
  getRowProps: GetRowProps
}) {
  return (
    <>
      <TableExpandRow {...getRowProps({ row })}>
        {row.cells.map(cell => {
          const isGrade = cell.info.header !== 'ders'
          const val = String(cell.value || '')
          // No colour band (S42, B72): four status colours were judging the grade, and the blue band was also
          // Yabancı diller's family and Carbon's information colour.
          return (
            <TableCell key={cell.id} className={isGrade ? 'grade-col-center grade-cell' : ''}>
              {isGrade ? <NotDegeri deger={val} /> : val}
            </TableCell>
          )
        })}
      </TableExpandRow>
      {/* The expand button's aria-controls names this row; Carbon renders the
          row but gives it no id, so the reference pointed at nothing. */}
      <TableExpandedRow colSpan={headers.length + 1} id={String(getRowProps({ row })['aria-controls'] ?? '')}>
        {/* The detail names each column in full (S1 → "1. Sınav") with its figure. No bars (B51, §8.7): a
            missing grade drew a 0-wide bar that read as a zero, and the figure already is the information. */}
        <dl className="grade-detail">
          {COLS.map((col, ci) => (
            <div key={ci} className="grade-detail__row">
              <dt className="grade-detail__label">{col}</dt>
              <dd className="grade-detail__value"><NotDegeri deger={rawGrade?.[col] || '-'} /></dd>
            </div>
          ))}
        </dl>
      </TableExpandedRow>
    </>
  )
}
