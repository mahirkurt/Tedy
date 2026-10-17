import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

// C16: a component gets the page's minute clock (`nowMs` state ticking with setInterval), never
// `Date.now()` evaluated during render — an impure render the React Compiler cannot memoise, and a
// value that freezes at the render that happened to run. Pinned for props and for the exam countdown.
const KOK = new URL('../src/', import.meta.url).pathname

function tsxler(dizin: string): string[] {
  return readdirSync(dizin, { withFileTypes: true }).flatMap(g =>
    g.isDirectory() ? tsxler(join(dizin, g.name)) : g.name.endsWith('.tsx') ? [join(dizin, g.name)] : [])
}

test('hiçbir JSX özniteliği Date.now() taşımaz', () => {
  const ihlaller = tsxler(KOK).flatMap(f => {
    const metin = readFileSync(f, 'utf8')
    return [...metin.matchAll(/=\{\s*Date\.now\(\)\s*\}/g)].map(m => `${f.slice(KOK.length)}: ${m[0]}`)
  })
  assert.deepEqual(ihlaller, [])
})

test('Sınavlar kartının geri sayımı sayfanın nowMs saatini alır', () => {
  const metin = readFileSync(join(KOK, 'components/ExamTimeline.tsx'), 'utf8')
  assert.match(metin, /sinavGeriSayimi\(exam, nowMs\)/)
  assert.doesNotMatch(metin, /getExamCountdown\(/)
})
