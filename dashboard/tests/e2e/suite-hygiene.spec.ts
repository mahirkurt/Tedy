import { test, expect } from '@playwright/test'
import { readdir, readFile } from 'node:fs/promises'

// No fixed waits in this suite. A waitForTimeout encodes a guess about how long
// rendering takes on the machine that wrote the test; under parallel load the
// guess loses, and the non-retrying read after it (count, innerText, evaluate)
// sees a page that has not rendered. homework.spec.ts flaked exactly that way
// twice before the 21 fixed waits were replaced.
//
// Wait on the state the next line reads. And before asserting an absence —
// no banner, no overflow, no skipped heading — first prove the thing it is
// absent from has rendered, because every absence is true of a blank page.
test('the suite waits on conditions, not durations', async () => {
  const dir = new URL('.', import.meta.url)
  const files = (await readdir(dir)).filter(f => f.endsWith('.spec.ts'))
  const offenders: string[] = []
  for (const f of files) {
    const src = await readFile(new URL(f, dir), 'utf8')
    src.split('\n').forEach((line, i) => {
      if (/\bwaitForTimeout\s*\(/.test(line.replace(/\/\/.*$/, ''))) {
        offenders.push(`${f}:${i + 1}`)
      }
    })
  }
  expect(files.length, 'spec dosyası bulunamadı').toBeGreaterThan(5)
  expect(offenders, 'sabit süreli bekleme').toEqual([])
})
