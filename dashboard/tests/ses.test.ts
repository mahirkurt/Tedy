import assert from 'node:assert/strict'
import { test } from 'node:test'
import { birlestir, okunacakMetin, onayAnahtari, turkceSes } from '../src/utils/ses.ts'

test('markdown ve atıf okunmaz, kesir durur', () => {
  assert.equal(okunacakMetin('Payda **eşitlenir** [S1].'), 'Payda eşitlenir.')
  assert.equal(okunacakMetin('# Başlık\n\n1/2'), 'Başlık 1/2')
  assert.equal(okunacakMetin('[kitap](https://ornek.test/a)'), 'kitap')
  assert.equal(okunacakMetin('![şekil](https://ornek.test/a.png)'), 'şekil')
  assert.equal(okunacakMetin('```py\n1/2\n```'), '1/2')
  assert.equal(okunacakMetin('> alıntı\n- madde'), 'alıntı madde')
  assert.equal(okunacakMetin('a * b ve MAT_7 ve *kalın* ve _vurgu_'), 'a * b ve MAT_7 ve kalın ve vurgu')
  assert.equal(okunacakMetin('[S1]'), '')
})

test('tr-TR once, sonra tr, yoksa null', () => {
  assert.equal(turkceSes([{ lang: 'en-US' }, { lang: 'tr' }, { lang: 'tr-TR' }])?.lang, 'tr-TR')
  assert.equal(turkceSes([{ lang: 'tr_TR' }])?.lang, 'tr_TR')
  assert.equal(turkceSes([{ lang: 'en-US' }]), null)
  assert.equal(turkceSes([]), null)
})

test('birlestir ve kisi anahtari', () => {
  assert.equal(birlestir('1/2', 'kaçtır'), '1/2 kaçtır')
  assert.equal(birlestir('', 'kesir'), 'kesir')
  assert.equal(birlestir('kesir ', ' nedir'), 'kesir nedir')
  assert.equal(birlestir('  ', '  '), '')
  assert.equal(onayAnahtari('Test@TEDY.online'), 'tedy-ses-onay::test@tedy.online')
  assert.equal(onayAnahtari('  a@b.c '), 'tedy-ses-onay::a@b.c')
  assert.equal(onayAnahtari(''), null)
  assert.equal(onayAnahtari(null), null)
})
