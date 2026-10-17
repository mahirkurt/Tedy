import { test } from 'node:test'
import assert from 'node:assert/strict'
import { uygulamaIcindeAc } from '../src/utils/gezinme.ts'

// C13: düz sol tık uygulama içinde gezinir; yeni sekme/pencere isteyen tık ve dış bağlantı tarayıcıya kalır.
const tik = (ek: Partial<{ button: number; metaKey: boolean; ctrlKey: boolean; shiftKey: boolean; altKey: boolean;
  defaultPrevented: boolean }> = {}) =>
  ({ button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false, defaultPrevented: false, ...ek })

test('düz sol tık, uygulama içi yol: SPA', () => {
  assert.equal(uygulamaIcindeAc(tik(), '/dersler?hafta=2.%20Hafta'), true)
  assert.equal(uygulamaIcindeAc(tik(), '/sinavlar#uyarilar'), true)
})

test('ctrl/cmd/shift/alt ve orta tık tarayıcıya kalır', () => {
  for (const ek of [{ ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }]) {
    assert.equal(uygulamaIcindeAc(tik(ek), '/dersler'), false, JSON.stringify(ek))
  }
})

test('hedefli bağlantı, dış adres, API ve önlenmiş olay tarayıcıya kalır', () => {
  assert.equal(uygulamaIcindeAc(tik(), '/dersler', '_blank'), false)
  assert.equal(uygulamaIcindeAc(tik(), '/dersler', '_self'), true)
  assert.equal(uygulamaIcindeAc(tik(), 'https://portal.example/x'), false)
  assert.equal(uygulamaIcindeAc(tik(), '//baska.example/x'), false)
  assert.equal(uygulamaIcindeAc(tik(), '/api/ekler/abc'), false)
  assert.equal(uygulamaIcindeAc(tik({ defaultPrevented: true }), '/dersler'), false)
  assert.equal(uygulamaIcindeAc(tik(), undefined), false)
})
