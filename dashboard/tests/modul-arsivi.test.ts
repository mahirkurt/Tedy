import { test } from 'node:test'
import assert from 'node:assert/strict'
import { arsivYonu } from '../src/utils/moduleLink.ts'

// GET /api/modules/<slug>/v<N>/ticket → 410 {arsivlendi: true, guncel} (src/dashboard_api.py, 2026-10-24).

test('arşivlenmiş sürüm güncel sürümün rotasına yönlenir', () => {
  assert.deepEqual(arsivYonu('fen5-su', 1, { arsivlendi: true, guncel: 3 }),
    { tur: 'yonlendir', yol: '/moduller/fen5-su/v3' })
})

test('güncel sürüm yoksa modül artık yayında değildir', () => {
  assert.deepEqual(arsivYonu('fen5-su', 1, { arsivlendi: true, guncel: null }), { tur: 'yayinda_degil' })
})

test('kendine ya da geçersiz sürüme yönlenmez: döngü ve uydurma rota yok', () => {
  assert.deepEqual(arsivYonu('fen5-su', 3, { arsivlendi: true, guncel: 3 }), { tur: 'yayinda_degil' })
  for (const guncel of [0, -1, 1.5, '3', 10000, undefined]) {
    assert.deepEqual(arsivYonu('fen5-su', 1, { arsivlendi: true, guncel }), { tur: 'yayinda_degil' })
  }
})

test('arşiv gövdesi değilse karar yok (genel hata cümlesi kalır)', () => {
  for (const govde of [null, undefined, 'x', {}, { error: 'not_found' }, { arsivlendi: 'true', guncel: 2 }]) {
    assert.equal(arsivYonu('fen5-su', 1, govde), null)
  }
})
