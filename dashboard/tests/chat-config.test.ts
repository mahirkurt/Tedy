import assert from 'node:assert/strict'
import { test } from 'node:test'
import { tedyChatConfig } from '../src/asistan/tedyChatConfig.ts'
import type { ConfigGirdisi } from '../src/asistan/tedyChatConfig.ts'

const G: ConfigGirdisi = { bicim: 'sayfa', okur: 'ogrenci', karsilama: 'Merhaba!', hizliSorular: [{ metin: 'Soru 1' }],
  saltOkunur: false, altBaslik: 'Kaynaklı soru-cevap', gonder: async () => {} }

test('güvenlik ve görünüm kararları (Görev 1 raporu, güvenlik incelemesi)', () => {
  const c = tedyChatConfig(G)
  assert.equal(c.shouldSanitizeHTML, true)
  assert.equal(c.locale, 'en-gb')                       // 'tr' desteklenmiyor; 24 saat biçimi
  assert.equal(c.assistantName, 'TEDY Asistan')
  assert.equal(c.hideAvatar, true)
  assert.equal(c.header?.showAiLabel, false)            // kendi AILabel'ımız (axe nested-interactive)
  assert.equal(c.upload?.isOn, false)
  assert.equal(c.strings?.input_placeholder, 'Bir soru sor veya çalışma planı iste...')
})

test('gömülü sayfa açık başlar ve başlatıcısızdır; panel başlatıcılı', () => {
  assert.equal(tedyChatConfig(G).openChatByDefault, true)
  assert.equal(tedyChatConfig(G).launcher?.isOn, false)
  assert.equal(tedyChatConfig({ ...G, bicim: 'panel' }).launcher?.isOn, true)
})

test('salt okunur: hızlı soru ve yeniden başlatma yok; aileye siz', () => {
  const c = tedyChatConfig({ ...G, saltOkunur: true, okur: 'aile' })
  assert.equal(c.isReadonly, true)
  assert.equal(c.homescreen?.starters?.isOn, false)
  assert.equal(c.header?.showRestartButton, false)
  assert.equal(c.strings?.input_placeholder, 'Bir soru sorun veya çalışma planı isteyin...')
})

test('mesajlı sohbet açılınca başlangıç ekranı kapanır (Carbon yalnız gönderince kapatıyor)', () => {
  assert.equal(tedyChatConfig({ ...G, mesajVar: true }).homescreen?.isOn, false)
  assert.equal(tedyChatConfig({ ...G, mesajVar: false }).homescreen?.isOn, true)
})
