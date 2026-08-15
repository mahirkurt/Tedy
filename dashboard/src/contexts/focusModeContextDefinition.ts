import { createContext, useContext } from 'react'

interface FocusModeState {
  focusMode: boolean
  toggleFocusMode: () => void
}

export const FocusModeContext = createContext<FocusModeState>({
  focusMode: false,
  toggleFocusMode: () => {},
})

export function useFocusMode() {
  return useContext(FocusModeContext)
}
