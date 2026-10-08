import assert from 'node:assert/strict'
import { test } from 'node:test'
import { execFileSync } from 'node:child_process'
import { TURKCE } from '../src/asistan/dilPaketi.ts'

test('Carbon dil paketinin her anahtarı Türkçe', () => {
  const anahtarlar: string[] = JSON.parse(execFileSync('node', ['scripts/carbon-dil-anahtarlari.mjs'], { encoding: 'utf8' }))
  assert.ok(anahtarlar.length >= 263)
  const eksik = anahtarlar.filter(k => !(k in TURKCE))
  assert.deepEqual(eksik, [])
  const ingilizce = Object.entries(TURKCE).filter(([, v]) => /\b(the|you|your|Close|Open|Send|Cancel)\b/.test(v as string))
  assert.deepEqual(ingilizce, [])
})
