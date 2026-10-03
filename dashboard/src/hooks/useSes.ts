import { useEffect, useRef, useState } from 'react'
import { birlestir, okunacakMetin, onayAnahtari, turkceSes } from '../utils/ses'

interface Tanima {
  lang: string; interimResults: boolean; continuous: boolean; maxAlternatives: number
  onresult: ((event: { results: { [index: number]: { [index: number]: { transcript: string } } } }) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void; stop: () => void; abort: () => void
}
type TanimaKurucu = new () => Tanima
type SesWindow = Window & { SpeechRecognition?: TanimaKurucu; webkitSpeechRecognition?: TanimaKurucu }

export function useSes(email: string | undefined, draft: string, setDraft: (s: string) => void,
  odaklan: () => void, salt: boolean) {
  const [ses, setSes] = useState<SpeechSynthesisVoice | null>(null)
  const [okunan, setOkunan] = useState<string | null>(null)
  const [dinliyor, setDinliyor] = useState(false)
  const [onayAcik, setOnayAcik] = useState(false)
  const [hata, setHata] = useState<string | null>(null)
  const recognition = useRef<Tanima | null>(null)
  const utterance = useRef<SpeechSynthesisUtterance | null>(null)
  const taban = useRef('')
  const geciciOnay = useRef<string | null>(null)
  const ctor = (window as SesWindow).SpeechRecognition ?? (window as SesWindow).webkitSpeechRecognition
  const anahtar = onayAnahtari(email ?? null)

  useEffect(() => {
    const synth = window.speechSynthesis
    if (!synth || typeof synth.speak !== 'function' || typeof window.SpeechSynthesisUtterance !== 'function') return
    const update = () => setSes(turkceSes(synth.getVoices()))
    update()
    synth.addEventListener('voiceschanged', update)
    return () => {
      synth.removeEventListener('voiceschanged', update)
      utterance.current = null
      synth.cancel()
    }
  }, [])

  useEffect(() => () => {
    const rec = recognition.current
    if (rec) { rec.onend = null; rec.onresult = null; rec.onerror = null; rec.abort() }
    recognition.current = null
  }, [email, salt])

  function oku(id: string, text: string) {
    if (!ses) return
    const synth = window.speechSynthesis
    utterance.current = null
    synth.cancel()
    if (okunan === id) { setOkunan(null); return }
    const plain = okunacakMetin(text)
    if (!plain) return
    const speech = new SpeechSynthesisUtterance(plain)
    speech.lang = 'tr-TR'; speech.voice = ses
    speech.rate = 1; speech.pitch = 1; speech.volume = 1
    speech.onend = speech.onerror = () => {
      if (utterance.current === speech) { setOkunan(null); utterance.current = null }
    }
    utterance.current = speech
    setOkunan(id)
    synth.speak(speech)
  }

  function basla() {
    if (!ctor || !anahtar || salt) return
    const rec = new ctor()
    rec.lang = 'tr-TR'; rec.interimResults = true; rec.continuous = false; rec.maxAlternatives = 1
    taban.current = draft
    recognition.current = rec
    setHata(null)
    rec.onresult = event => {
      if (recognition.current === rec) setDraft(birlestir(taban.current, event.results[0][0].transcript))
    }
    rec.onerror = event => {
      if (event.error !== 'aborted') setHata(event.error === 'not-allowed' ? 'Mikrofon açılamadı.' : 'Ses anlaşılamadı.')
      setDinliyor(false)
    }
    rec.onend = () => { setDinliyor(false); odaklan() }
    try { rec.start(); setDinliyor(true) }
    catch { setHata('Mikrofon açılamadı.'); setDinliyor(false) }
  }

  function mikrofon() {
    if (dinliyor) { recognition.current?.stop(); setDinliyor(false); odaklan(); return }
    if (!anahtar) return
    let onay = geciciOnay.current === anahtar
    try { onay ||= localStorage.getItem(anahtar) === '1' } catch { /* Session-only consent. */ }
    if (onay) basla()
    else setOnayAcik(true)
  }

  function onayla() {
    setOnayAcik(false)
    if (!anahtar) return
    geciciOnay.current = anahtar
    try { localStorage.setItem(anahtar, '1') } catch { /* Session-only consent. */ }
    basla()
  }

  return { ses, okunan, oku, dinliyor, mikrofonVar: !!ctor && !!anahtar && !salt,
    mikrofon, onayAcik, onayla, vazgec: () => setOnayAcik(false), hata }
}
