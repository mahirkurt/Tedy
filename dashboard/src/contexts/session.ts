import { createContext, useContext } from 'react'
import type { User } from '../hooks/useAuth'

/**
 * The signed-in user, readable from anywhere below the app shell.
 *
 * Screens shared between roles (the shelf, a book page) use this to address the
 * reader by name and to drop dashboard-only affordances, without every one of
 * them re-fetching `/api/auth/me`.
 *
 * Context object and hook sit apart from the provider so the provider module
 * exports components only — what React Fast Refresh needs to hot-swap it.
 */
export const SessionContext = createContext<User | null>(null)

export function useSession(): User | null {
  return useContext(SessionContext)
}

/** "Hülya Murzoğlu" → "Hülya"; falls back to the mailbox name. */
export function firstName(user: User | null): string {
  const fromName = (user?.name || '').trim().split(/\s+/)[0]
  if (fromName) return fromName
  const local = (user?.email || '').split('@')[0]
  if (!local) return ''
  return local.charAt(0).toLocaleUpperCase('tr-TR') + local.slice(1)
}
