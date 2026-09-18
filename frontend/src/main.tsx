import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { App } from '@/app/App'
import './index.css'

const ROUTER_FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true }

const queryClient = new QueryClient({
  defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={ROUTER_FUTURE}>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
