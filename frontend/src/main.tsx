// Enable @preact/signals-react auto-tracking for signal reactivity in React components.
// MUST be the FIRST import — before React, ReactDOM, or any component.
import '@preact/signals-react/auto'

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './theme/styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
