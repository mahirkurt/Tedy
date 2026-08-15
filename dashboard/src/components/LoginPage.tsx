import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { InlineNotification } from '@carbon/react'

const GOOGLE_CLIENT_ID = '343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com'

interface LoginPageProps {
  onLogin: (credential: string) => Promise<{ ok: boolean; error?: string }>
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential: string }) => void
            auto_select?: boolean
          }) => void
          renderButton: (
            element: HTMLElement,
            config: {
              theme?: string
              size?: string
              width?: number
              text?: string
              shape?: string
              locale?: string
            }
          ) => void
        }
      }
    }
  }
}

const GSI_SCRIPT_ID = 'google-gsi-script'

/** Insert the Google Identity Services tag once, returning the existing one after that. */
function ensureGsiScript(): HTMLScriptElement {
  const existing = document.getElementById(GSI_SCRIPT_ID)
  if (existing) return existing as HTMLScriptElement
  const script = document.createElement('script')
  script.id = GSI_SCRIPT_ID
  script.src = 'https://accounts.google.com/gsi/client'
  script.async = true
  document.head.appendChild(script)
  return script
}

function subscribeGsi(onChange: () => void) {
  const script = ensureGsiScript()
  script.addEventListener('load', onChange)
  return () => script.removeEventListener('load', onChange)
}

/**
 * Readiness is whether the API object exists, not whether a <script> tag does.
 * A tag that is still downloading used to read as "loaded", after which the
 * init effect bailed on `!window.google` and never ran again.
 */
function gsiReady() {
  return Boolean(window.google?.accounts?.id)
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const buttonRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const scriptLoaded = useSyncExternalStore(subscribeGsi, gsiReady, () => false)

  // Initialize Google Sign-In button
  useEffect(() => {
    if (!scriptLoaded || !window.google || !buttonRef.current) return

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response: { credential: string }) => {
        setError(null)
        const result = await onLogin(response.credential)
        if (!result.ok) {
          setError(result.error || 'Giriş başarısız')
        }
      },
    })

    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: 'outline',
      size: 'large',
      width: 320,
      text: 'signin_with',
      shape: 'rectangular',
      locale: 'tr',
    })
  }, [scriptLoaded, onLogin])

  return (
    <div className="login-page">
      {/* Left Hero Panel */}
      <div className="login-page__hero">
        <div className="login-page__hero-geo" aria-hidden="true" />
        <div className="login-page__hero-content">
          <img src="/tedy-logo-white.svg" alt="TEDY" className="login-page__hero-logo" />
          <p className="login-page__hero-school">TED Rönesans Koleji</p>
          <p className="login-page__hero-subtitle">Öğrenci Takip Paneli</p>
        </div>
      </div>

      {/* Right Form Panel */}
      <div className="login-page__panel">
        <div className="login-page__panel-inner">
          <h1 className="login-page__heading">Hoş geldiniz</h1>
          <p className="login-page__intro">
            Devam etmek için Google hesabınızla giriş yapın.
          </p>

          <div className="login-page__google-button-wrap">
            <div ref={buttonRef} />
          </div>

          {error && (
            <InlineNotification
              kind="error"
              title="Hata"
              subtitle={error}
              lowContrast
              hideCloseButton
              className="login-page__error"
            />
          )}

          <p className="login-page__footnote">
            Sadece yetkili aile üyeleri giriş yapabilir.
          </p>
        </div>
      </div>
    </div>
  )
}
