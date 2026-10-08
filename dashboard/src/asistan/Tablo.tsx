import type { ReactNode } from 'react'
import Kaydirilabilir from '../components/Kaydirilabilir'
import { renderMarkdown } from '../utils/markdown'

interface Hucre { text: string }
interface TabloVerisi { headers: Hucre[]; rows: Hucre[][] }

/** Carbon'un tablo çizicisi (filtre kutulu cds-table) axe ve IBM ihlali veriyor (Görev 1 raporu, 2. ve 5.
 *  satır): cevap tabloları eski arayüzdeki gibi çizilir — kendi içinde kayan, gerekirse odak alan bölge.
 *  Hücre metni React ile çizilir (HTML enjeksiyonu yok); satır içi biçim sohbet renderer'ından gelir. */
function hucre(metin: string): ReactNode {
  return renderMarkdown(metin, { bicim: 'sohbet' })
}

export function tabloCiz(args: TabloVerisi): ReactNode {
  return (
    <Kaydirilabilir className="ac-md__table-wrap" etiket="Tablo">
      <table className="ac-md__table">
        <thead><tr>{args.headers.map((h, j) => <th key={j} scope="col">{hucre(h.text)}</th>)}</tr></thead>
        <tbody>{args.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{hucre(c.text)}</td>)}</tr>)}</tbody>
      </table>
    </Kaydirilabilir>
  )
}
