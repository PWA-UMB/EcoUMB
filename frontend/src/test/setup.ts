import '@testing-library/jest-dom/vitest'
import { configure } from '@testing-library/dom'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

import { useAuthStore } from '@/stores/authStore'

// El valor por defecto (1000 ms) alcanza en local, pero el runner de CI (GitHub Actions, 2 vCPU
// compartidas) es mucho más lento que una máquina de desarrollo: con varios workers de Vitest en
// paralelo, una cadena de fetch → estado → efecto (p. ej. AuthedImage) puede tardar más que eso y
// un `findBy*`/`waitFor` sin fallo real revienta por timeout. Se amplía el margen globalmente.
configure({ asyncUtilTimeout: 5000 })

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
