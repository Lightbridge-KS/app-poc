import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'

// Only the orval tab needs this, but the provider has to sit above both.
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
})

async function start() {
  // Orval also generates MSW handlers from the same spec. `VITE_MOCK=1 npm run dev`
  // serves the whole app from generated mocks with no Python running at all.
  if (import.meta.env.VITE_MOCK === '1') {
    const [{ setupWorker }, { getRadiologyStudiesPoCMock }] = await Promise.all([
      import('msw/browser'),
      import('./api/orval/poc.msw'),
    ])
    await setupWorker(...getRadiologyStudiesPoCMock()).start({
      onUnhandledRequest: 'bypass',
    })
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </StrictMode>,
  )
}

void start()
