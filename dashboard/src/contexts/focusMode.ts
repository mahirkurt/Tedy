import { createContext, useContext } from 'react'

/**
 * Context object and consumer hook live apart from the provider component so
 * that the provider's module exports components only — the condition React
 * Fast Refresh needs to hot-swap it without dropping state.
 */

export interface FocusModeState {
  focusMode: boolean
  toggleFocusMode: () => void
}

export const FOCUS_MODE_STORAGE_KEY = 'tedy-focus-mode'

export const FocusModeContext = createContext<FocusModeState>({
  focusMode: false,
  toggleFocusMode: () => {},
})

export function useFocusMode() {
  return useContext(FocusModeContext)
}
