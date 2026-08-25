// Entry point — mounts the React app into index.html
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Simple error boundary so a crash shows the reason instead of a blank page
class ErrorBoundary extends React.Component {
  constructor(p) { super(p); this.state = { err: null } }
  static getDerivedStateFromError(err) { return { err } }
  componentDidCatch(err, info) { console.log('APP ERROR >>>', err, info) }
  render() {
    if (this.state.err) {
      return (
        <pre style={{ color: '#fca5a5', padding: 24, whiteSpace: 'pre-wrap', fontSize: 13 }}>
          {String(this.state.err && this.state.err.stack || this.state.err)}
        </pre>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
)
