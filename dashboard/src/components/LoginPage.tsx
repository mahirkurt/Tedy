import { useEffect, useRef, useState } from 'react'
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

export default function LoginPage({ onLogin }: LoginPageProps) {
  const buttonRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [scriptLoaded, setScriptLoaded] = useState(false)

  // Load Google Identity Services script
  useEffect(() => {
    if (document.getElementById('google-gsi-script')) {
      setScriptLoaded(true)
      return
    }
    const script = document.createElement('script')
    script.id = 'google-gsi-script'
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => setScriptLoaded(true)
    document.head.appendChild(script)
  }, [])

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
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#F4F4F4',
    }}>
      <div style={{
        backgroundColor: '#FFFFFF',
        padding: '3rem 2.5rem',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)',
        maxWidth: '420px',
        width: '100%',
        textAlign: 'center',
      }}>
        {/* TEDY Header Bar */}
        <div style={{
          backgroundColor: '#002D9C',
          margin: '-3rem -2.5rem 2rem',
          padding: '1.5rem 2rem',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <img src="/tedy-logo-white.svg" alt="TEDY" style={{ height: 40 }} />
          <p style={{
            color: 'rgba(255,255,255,0.7)',
            fontSize: '0.8125rem',
            margin: 0,
          }}>
            Öğrenci Takip Paneli
          </p>
        </div>

        <p style={{
          fontSize: '0.875rem',
          color: '#525252',
          marginBottom: '1.5rem',
        }}>
          Devam etmek için Google hesabınızla giriş yapın.
        </p>

        {/* Google Sign-In Button */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
          <div ref={buttonRef} />
        </div>

        {error && (
          <InlineNotification
            kind="error"
            title="Hata"
            subtitle={error}
            lowContrast
            hideCloseButton
            style={{ marginTop: '1rem' }}
          />
        )}

        <p style={{
          fontSize: '0.6875rem',
          color: '#8D8D8D',
          marginTop: '2rem',
        }}>
          Sadece yetkili aile üyeleri giriş yapabilir.
        </p>
      </div>
    </div>
  )
}
