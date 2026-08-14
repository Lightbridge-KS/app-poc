import { useState } from 'react'
import { FetchPage } from './pages/FetchPage'
import { OrvalPage } from './pages/OrvalPage'
import './App.css'

type Tab = 'fetch' | 'orval'

const TABS: { id: Tab; label: string; sub: string }[] = [
  { id: 'fetch', label: 'openapi-fetch', sub: 'types only · ~6kb' },
  { id: 'orval', label: 'orval', sub: 'SDK · hooks · mocks' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('fetch')

  return (
    <div className="app">
      <header>
        <h1>Pydantic is the contract</h1>
        <p className="sub">
          Both tabs below call the same FastAPI backend through the same{' '}
          <code>openapi.json</code>. Neither hand-writes a single request or response type.
        </p>
        <pre className="pipeline">
{`  models.py  ──app.openapi()──▶  openapi.json  ──codegen──▶  schema.d.ts / orval SDK
      ▲                                                              │
      └──────────────  rename a field here and tsc fails  ◀──────────┘`}
        </pre>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={t.id === tab ? 'active' : undefined}
          >
            {t.label}
            <span>{t.sub}</span>
          </button>
        ))}
      </nav>

      <main>{tab === 'fetch' ? <FetchPage /> : <OrvalPage />}</main>

      <footer className="muted">
        Click a row to report it. <code>just drift-demo</code> breaks the build on purpose.
      </footer>
    </div>
  )
}
