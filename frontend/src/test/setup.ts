import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

import { useAuthStore } from '@/stores/authStore'

// jsdom no implementa estas APIs del navegador que usan la vista previa y la cámara.
Object.assign(URL, {
  createObjectURL: vi.fn(() => 'blob:mock-url'),
  revokeObjectURL: vi.fn(),
})
Object.defineProperty(HTMLMediaElement.prototype, 'play', {
  configurable: true,
  value: vi.fn().mockResolvedValue(undefined),
})

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState({ status: 'checking', user: null, accessToken: null, refreshToken: null })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
