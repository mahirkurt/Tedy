import assert from 'node:assert/strict'
import { test } from 'node:test'
import { tedyChatConfig } from '../src/asistan/tedyChatConfig.ts'
import type { ConfigGirdisi } from '../src/asistan/tedyChatConfig.ts'

const G: ConfigGirdisi = { bicim: 'sayfa', okur: 'ogrenci',
  saltOkunur: false, altBaslik: 'Kaynaklı soru-cevap', gonder: async () => {} }

test('güvenlik ve görünüm kararları (Görev 1 raporu, güvenlik incelemesi)', () => {
  const c = tedyChatConfig(G)
  assert.equal(c.shouldSanitizeHTML, true)
  assert.equal(c.locale, 'en-gb')                       // 'tr' desteklenmiyor; 24 saat biçimi
  assert.equal(c.assistantName, 'TEDY Asistan')
  assert.equal(c.hideAvatar, true)
  assert.equal(c.header?.showAiLabel, false)            // kendi AILabel'ımız (axe nested-interactive)
  assert.equal(c.upload?.isOn, false)
  assert.equal(c.injectCarbonTheme, undefined)   // tema sayfadan miras; aksi ders rengini ezer
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
  assert.equal(c.header?.showRestartButton, false)
  assert.equal(c.strings?.input_placeholder, 'Bir soru sorun veya çalışma planı isteyin...')
})

test('Carbon başlangıç ekranı kapalı, karşılama isteği gönderilmez: tek giriş alanı (karşılama ve hızlı sorular bizim)', () => {
  const c = tedyChatConfig(G)
  assert.equal(c.homescreen?.isOn, false)
  assert.equal(c.messaging?.skipWelcome, true)
})

test('soranın etiketi hitaba uyar: öğrenciye "Sen", aileye "Siz"', () => {
  const ogrenci = tedyChatConfig({ ...G, okur: 'ogrenci' }).strings
  const aile = tedyChatConfig({ ...G, okur: 'aile' }).strings
  assert.equal(ogrenci?.message_labelYou, 'Sen {timestamp}')
  assert.equal(ogrenci?.messages_youSaid, 'Sen yazdın')
  assert.equal(aile?.message_labelYou, 'Siz {timestamp}')
  assert.equal(aile?.messages_youSaid, 'Siz yazdınız')
})

test('gömülü sayfada küçült düğmesi yok (başlatıcı yokken sohbet geri açılamazdı); panelde var', () => {
  assert.equal(tedyChatConfig({ ...G, bicim: 'sayfa' }).header?.hideMinimizeButton, true)
  assert.equal(tedyChatConfig({ ...G, bicim: 'panel' }).header?.hideMinimizeButton, false)
})
