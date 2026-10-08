// İstek çalıştırma: sayfa, başlatıcı ve kartlar (Tekrar dene, Daha derine in) aynı yolu kullanır.
import type { ChatInstance, StreamChunk } from '@carbon/ai-chat'
import type { AssistantCitation } from '../types'
import { asistanDeposu } from './asistanDeposu.ts'
import { akisBaslat, hataYaniti, olayIsle, sonYanit } from './olayEslemesi.ts'
import type { SonYanitSecenekleri } from './olayEslemesi.ts'
import { okurHatasi, planGonder, soruGonder } from './akisIstemcisi.ts'

function secenekler(): SonYanitSecenekleri {
  const d = asistanDeposu.al()
  return { geriBildirim: !d.saltOkunur, ogrenci: d.okur === 'ogrenci' }
}

/** Bir isteği çalıştırır ve Carbon'a parça parça verir. Parçalar sırayla eklenir (addMessageChunk asenkron). */
export async function calistir(inst: ChatInstance, govde: Record<string, unknown>, plan: boolean, signal: AbortSignal) {
  asistanDeposu.ayarla({ bekleyen: { govde, plan }, yukleniyor: true })
  let d = akisBaslat(crypto.randomUUID())
  let zincir: Promise<unknown> = Promise.resolve()
  const sira = (f: () => Promise<unknown>) => { zincir = zincir.then(f); return zincir }
  try {
    if (plan) {
      const p = await planGonder(govde, signal)
      await inst.messaging.addMessageChunk({ final_response: sonYanit(d, p, secenekler()) } as StreamChunk)
      asistanDeposu.ayarla({ sonYanitId: d.yanitId, sonModel: p.meta?.model })
    } else {
      await soruGonder(govde, o => {
        const r = olayIsle(d, o, secenekler())
        d = r.durum
        if (r.kaldir) { const k = r.kaldir; sira(() => inst.messaging.removeMessages(k)) }
        for (const p of r.parcalar) sira(() => inst.messaging.addMessageChunk(p))
        if (o.ad === 'answer') {
          const payload = o.veri.payload as { answer?: string; meta?: { model?: string } }
          const dk = asistanDeposu.al()
          asistanDeposu.ayarla({ dokum: [...dk.dokum, { role: 'assistant', content: payload.answer ?? '' }],
            sonYanitId: d.yanitId, sonModel: payload.meta?.model })
        }
      }, signal)
      await zincir
    }
    asistanDeposu.ayarla({ bekleyen: null })
  } catch (e) {
    await zincir.catch(() => {})
    if ((e as { name?: string })?.name === 'AbortError' || signal.aborted) return
    await inst.messaging.addMessage(hataYaniti(crypto.randomUUID(), okurHatasi(e)))
  } finally {
    asistanDeposu.ayarla({ yukleniyor: false })
  }
}

export async function tekrarDene(inst: ChatInstance, hataMesajiId: string) {
  const b = asistanDeposu.al().bekleyen
  if (!b) return
  await inst.messaging.removeMessages([hataMesajiId])
  await calistir(inst, b.govde, b.plan, new AbortController().signal)
}

export async function soruyuYeniden(inst: ChatInstance, metin: string, ek: { deep?: boolean; transient?: boolean; plan?: boolean }) {
  asistanDeposu.ayarla({ sonrakiIstek: ek })
  await inst.send(metin)
}


/** Kaynak ayrıntıları (figür küçük resmi, modül bağlantısı, kitap) workspace panelinde bugünkü SourcePanel ile. */
export async function kaynaklariAc(inst: ChatInstance, atiflar: AssistantCitation[], etkin: string | null, donus?: HTMLElement) {
  asistanDeposu.ayarla({ acikAtif: { atiflar, etkin, donus } })
  await inst.customPanels?.getPanel('workspace' as never).open({ title: 'Kaynaklar', preferredLocation: 'end' } as never)
}
