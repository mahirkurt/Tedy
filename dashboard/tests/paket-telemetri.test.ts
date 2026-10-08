import assert from 'node:assert/strict'
import { test } from 'node:test'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'

const DIST = new URL('../../dashboard-dist/assets/', import.meta.url)

test('derlenmiş pakette IBM telemetri ucu yok', () => {
  // Bilerek atlamaz: paket yoksa test başarısızdır (bayat/eksik paket yanlış-geçiş tuzağı).
  assert.ok(existsSync(DIST), 'dashboard-dist yok: önce `npm run build:carbon-ai`')
  const js = readdirSync(DIST).filter(f => f.endsWith('.js'))
  assert.ok(js.some(f => readFileSync(new URL(f, DIST), 'utf8').includes('cds-aichat')),
    'pakette Carbon AI Chat yok: bayrak kapalı derlenmiş olabilir')
  for (const f of js) {
    assert.ok(!readFileSync(new URL(f, DIST), 'utf8').includes('ibm-telemetry/v1/metrics'), `${f} telemetri ucu içeriyor`)
  }
})

test('Carbon AI Chat ilk yüklenen parçalarda değil', () => {
  const html = readFileSync(new URL('../../dashboard-dist/index.html', import.meta.url), 'utf8')
  const ilk = [...html.matchAll(/(?:src|href)="\/assets\/([^"]+\.js)"/g)].map(m => m[1])
  for (const f of ilk) {
    const govde = readFileSync(new URL(f, DIST), 'utf8')
    assert.ok(!govde.includes('cds-aichat-container'), `${f} ilk yüklemede Carbon AI Chat taşıyor (${statSync(new URL(f, DIST)).size} bayt)`)
  }
})
