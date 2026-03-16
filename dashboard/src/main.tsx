import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Theme } from '@carbon/react'
import { FocusModeProvider } from './contexts/FocusModeContext'
import App from './App'
import './theme/ted-theme.scss'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Theme theme="g10">
      <FocusModeProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </FocusModeProvider>
    </Theme>
  </React.StrictMode>
)
