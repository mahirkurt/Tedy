import { test } from 'node:test'
import assert from 'node:assert/strict'
import { acceptSizeMessage, appearanceMessage } from '../src/utils/moduleBridge.ts'

test('appearance mesajı kök yazı boyunu taşır', () => {
  assert.deepEqual(appearanceMessage('g10', 32),
    { type: 'edupedia:appearance', v: 1, theme: 'g10', rootPx: 32 })
})

test('kök boyu verilmezse alan hiç yazılmaz (geriye uyum)', () => {
  assert.deepEqual(appearanceMessage('g10'),
    { type: 'edupedia:appearance', v: 1, theme: 'g10' })
})

test('appearance mesajı akış yerleşimini taşır', () => {
  assert.deepEqual(appearanceMessage('g10', 16, 'flow'),
    { type: 'edupedia:appearance', v: 1, theme: 'g10', rootPx: 16, layout: 'flow' })
})

// The frame is sandboxed without allow-same-origin, so its messages arrive from origin "null".
const cerceve = {} as Window
const yabanci = {} as Window
const olay = (data: unknown, source: Window | null = cerceve, origin = 'null') =>
  ({ data, source, origin }) as Pick<MessageEvent, 'data' | 'origin' | 'source'>

test('boy mesajı yalnız açtığımız çerçeveden kabul edilir', () => {
  const mesaj = { type: 'edupedia:size', v: 1, height: 1840 }
  assert.deepEqual(acceptSizeMessage(olay(mesaj), cerceve), mesaj)
  assert.deepEqual(acceptSizeMessage(olay({ ...mesaj, top: true }), cerceve), { ...mesaj, top: true })
  assert.equal(acceptSizeMessage(olay(mesaj, yabanci), cerceve), null)
  assert.equal(acceptSizeMessage(olay(mesaj, cerceve, 'https://tedy.online'), cerceve), null)
  assert.equal(acceptSizeMessage(olay(mesaj), null), null)
})

test('bozuk ya da sınır dışı boy mesajı reddedilir', () => {
  for (const kotu of [
    null, [], 'edupedia:size',
    { type: 'edupedia:size', v: 2, height: 100 },
    { type: 'edupedia:progress', v: 1, height: 100 },
    { type: 'edupedia:size', v: 1, height: 0 },
    { type: 'edupedia:size', v: 1, height: 200_001 },
    { type: 'edupedia:size', v: 1, height: 12.5 },
    { type: 'edupedia:size', v: 1, height: '900' },
    { type: 'edupedia:size', v: 1, height: 900, top: 'evet' },
    { type: 'edupedia:size', v: 1, height: 900, xp: 10 },
  ]) assert.equal(acceptSizeMessage(olay(kotu), cerceve), null, JSON.stringify(kotu))
})
