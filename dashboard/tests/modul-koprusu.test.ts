import { test } from 'node:test'
import assert from 'node:assert/strict'
import { appearanceMessage } from '../src/utils/moduleBridge.ts'

test('appearance mesajı kök yazı boyunu taşır', () => {
  assert.deepEqual(appearanceMessage('g10', 32),
    { type: 'edupedia:appearance', v: 1, theme: 'g10', rootPx: 32 })
})

test('kök boyu verilmezse alan hiç yazılmaz (geriye uyum)', () => {
  assert.deepEqual(appearanceMessage('g10'),
    { type: 'edupedia:appearance', v: 1, theme: 'g10' })
})
