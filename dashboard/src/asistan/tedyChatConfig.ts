import type { PublicConfig, PublicConfigMessaging } from '@carbon/ai-chat'
import { TURKCE } from './dilPaketi.ts'

export interface ConfigGirdisi {
  /** 'sayfa': /asistan'a gömülü (açık başlar, başlatıcı yok). 'panel': diğer sayfalarda başlatıcıyla açılan yan panel. */
  bicim: 'sayfa' | 'panel'
  okur: 'ogrenci' | 'aile'
  karsilama: string
  hizliSorular: { metin: string; plan?: boolean }[]
  saltOkunur: boolean
  altBaslik: string
  gonder: PublicConfigMessaging['customSendMessage']
  gecmisYukle?: PublicConfigMessaging['customLoadHistory']
  /** Ekranda mesaj var mı: Carbon başlangıç ekranını yalnız gönderince kapatır; yüklenen geçmişte isOn kapatılır. */
  mesajVar?: boolean
}

/** Sayfa ve başlatıcı aynı yapılandırmayı kullanır; farkları bileşen (ChatCustomElement / ChatContainer) yapar. */
export function tedyChatConfig(g: ConfigGirdisi): Omit<PublicConfig, 'markdown'> {
  return {
    // 'tr' paketin tarih yerel ayarlarında yok ve 'en'e (12 saat, "3:50 PM") düşüyor; 'en-gb' 24 saat verir.
    // Görünen metinler `strings` ile Türkçedir (Görev 1 raporu, 4. satır).
    locale: 'en-gb',
    strings: {
      ...TURKCE,
      input_placeholder: g.okur === 'ogrenci' ? 'Bir soru sor veya çalışma planı iste...' : 'Bir soru sorun veya çalışma planı isteyin...',
    },
    // Model cevabı ve alıntılanan portal metni ham HTML taşıyabilir: Carbon'un temizleyicisi açık (XSS).
    shouldSanitizeHTML: true,
    aiEnabled: true,
    assistantName: 'TEDY Asistan',
    hideAvatar: true,
    openChatByDefault: g.bicim === 'sayfa',
    launcher: { isOn: g.bicim === 'panel' },
    // Carbon'un başlık AI etiketi axe nested-interactive ihlali veriyor; açıklama kendi AILabel'ımızla (Görev 14).
    header: { title: 'TEDY Asistan', name: g.altBaslik, showAiLabel: false, showRestartButton: !g.saltOkunur },
    homescreen: {
      isOn: !g.mesajVar, greeting: g.karsilama, disableReturn: false,
      starters: { isOn: !g.saltOkunur, buttons: g.hizliSorular.map(s => ({ label: s.metin })) },
    },
    history: { isOn: true, showMobileMenu: true },
    upload: { isOn: false },   // ekler bugünkü çiplerle giriş üstü yuvada (Görev 16)
    layout: { showFrame: false, hasContentMaxWidth: true },
    messaging: {
      customSendMessage: g.gonder,
      ...(g.gecmisYukle ? { customLoadHistory: g.gecmisYukle } : {}),
      messageTimeoutSecs: 180, showStopButtonImmediately: true,
    },
    isReadonly: g.saltOkunur,
    persistFeedback: true,
    injectCarbonTheme: 'g10' as PublicConfig['injectCarbonTheme'],   // panoyla aynı tema (DASHBOARD_THEME)
    keyboardShortcuts: { messageFocusToggle: { isOn: true } },
  }
}
