import { useState, useEffect, type ReactNode } from 'react'
import { FocusModeContext, FOCUS_MODE_STORAGE_KEY } from './focusMode'

export function FocusModeProvider({ children }: { children: ReactNode }) {
  const [focusMode, setFocusMode] = useState(() => {
    try {
      return localStorage.getItem(FOCUS_MODE_STORAGE_KEY) === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(FOCUS_MODE_STORAGE_KEY, String(focusMode))
    } catch {
      // localStorage unavailable
    }
  }, [focusMode])

  const toggleFocusMode = () => setFocusMode(prev => !prev)

  return (
    <FocusModeContext.Provider value={{ focusMode, toggleFocusMode }}>
      {children}
    </FocusModeContext.Provider>
  )
}
