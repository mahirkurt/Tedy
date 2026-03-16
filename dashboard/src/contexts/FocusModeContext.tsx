import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface FocusModeState {
  focusMode: boolean
  toggleFocusMode: () => void
}

const FocusModeContext = createContext<FocusModeState>({
  focusMode: false,
  toggleFocusMode: () => {},
})

const STORAGE_KEY = 'tedy-focus-mode'

export function FocusModeProvider({ children }: { children: ReactNode }) {
  const [focusMode, setFocusMode] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(focusMode))
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

export function useFocusMode() {
  return useContext(FocusModeContext)
}
