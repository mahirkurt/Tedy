import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { Button } from '@carbon/react'
import { Restart } from '@carbon/icons-react'

interface Props {
  /** Changing this resets the boundary — pass the pathname. */
  resetKey: string
  children: ReactNode
}
interface State { error: Error | null }

/**
 * Keeps one broken surface from taking the whole dashboard down.
 *
 * Before this existed, any render-time exception — an endpoint answering 200
 * with an unexpected shape was enough — unmounted the entire React tree. The
 * result was a white page: no header, no navigation, no words, and no way
 * back except knowing to reload. For a reader who already cannot tell "this
 * section is empty" from "this is broken", that is the worst failure the
 * interface can produce (D3).
 *
 * The boundary sits inside the shell rather than around it, so the chrome
 * survives and the navigation is still there to leave by.
 */
export default class RouteBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // The reader gets plain words; the details go where a developer looks.
    console.error('Surface crashed:', error, info.componentStack)
  }

  componentDidUpdate(prev: Props) {
    // Navigating away is itself a recovery: a different surface should not
    // inherit this one's failure.
    if (prev.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null })
    }
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <section className="route-boundary" role="alert">
        <h2 className="route-boundary__title">Bu bölüm açılamadı</h2>
        <p className="route-boundary__body">
          Panonun geri kalanı çalışıyor — soldaki menüden başka bir sayfaya
          geçebilirsin. Bu sayfayı yeniden denemek istersen:
        </p>
        <Button
          kind="tertiary"
          size="md"
          renderIcon={Restart}
          onClick={() => this.setState({ error: null })}
        >
          Yeniden dene
        </Button>
      </section>
    )
  }
}
