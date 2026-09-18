import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

import { useAuthStore } from '@/stores/authStore'

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState({ status: 'checking', user: null, accessToken: null, refreshToken: null })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
