import { useState, useEffect, useCallback } from 'react'

export type UserRole = 'full' | 'reader'

export interface User {
  email: string
  name: string
  picture: string
  /** "reader" accounts see Tedy Books and nothing else. */
  role: UserRole
  /** Işık's own account. The assistant says "sen" to this account only and
   *  addresses everyone else as family. */
  student: boolean
}

/** Anything the API does not label explicitly is treated as least privilege. */
function toUser(data: Partial<User> | null | undefined): User {
  return {
    email: String(data?.email ?? ''),
    name: String(data?.name ?? ''),
    picture: String(data?.picture ?? ''),
    role: data?.role === 'full' ? 'full' : 'reader',
    student: data?.student === true,
  }
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const checkSession = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/me', { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        setUser(toUser(data))
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkSession()
  }, [checkSession])

  const login = useCallback(async (credential: string): Promise<{ ok: boolean; error?: string }> => {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ credential }),
      })
      const data = await res.json()
      if (res.ok) {
        setUser(toUser(data))
        return { ok: true }
      }
      return { ok: false, error: data.error || 'Giris basarisiz' }
    } catch {
      return { ok: false, error: 'Baglanti hatasi' }
    }
  }, [])

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
    setUser(null)
  }, [])

  return { user, loading, login, logout }
}
