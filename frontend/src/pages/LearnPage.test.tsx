import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { EMPTY_HISTORY, mockApi, renderApp, SESSION_ROUTES, startSession } from '@/test/utils'

const EDUCATION = {
  normative: {
    title: 'Código de colores — Resolución 2184 de 2019',
    summary: 'Bolsa blanca para aprovechables, negra para no aprovechables y verde para orgánicos.',
    note: 'Consulta la norma oficial.',
  },
  bags: [
    {
      category: 'aprovechable',
      bag_color: 'blanca',
      description: 'Residuos aprovechables: plásticos, papel, cartón, vidrio y metales.',
      educational_text: 'Van en la bolsa blanca los materiales que vuelven al ciclo productivo.',
      items: [
        { code: 'botella_pet', display_name: 'Botella PET', disposal_tip: 'Vacíala y aplástala.' },
        { code: 'lata_aluminio', display_name: 'Lata de aluminio', disposal_tip: 'Enjuágala.' },
      ],
    },
    {
      category: 'no_aprovechable',
      bag_color: 'negra',
      description: 'Residuos no aprovechables.',
      educational_text: 'Van en la bolsa negra los residuos contaminados.',
      items: [{ code: 'colilla', display_name: 'Colilla de cigarrillo', disposal_tip: 'Apágala.' }],
    },
    {
      category: 'organico',
      bag_color: 'verde',
      description: 'Residuos orgánicos aprovechables.',
      educational_text: 'Van en la bolsa verde los residuos que se descomponen.',
      items: [{ code: 'cascara', display_name: 'Cáscara de fruta', disposal_tip: 'Sin bolsas.' }],
    },
  ],
  practices: [
    { title: 'Separa desde el origen', text: 'Clasifica en el momento en que desechas.' },
    { title: 'Limpio y seco', text: 'Enjuaga los envases.' },
  ],
}

describe('Aprende (RF-26, RF-27, RF-28)', () => {
  beforeEach(() => startSession())

  it('presenta la norma, cada bolsa con sus objetos y las buenas prácticas', async () => {
    mockApi({ ...SESSION_ROUTES, 'GET /api/v1/education': () => ({ json: EDUCATION }) })
    renderApp('/aprende')

    expect(
      await screen.findByRole('heading', { name: /Resolución 2184 de 2019/ }),
    ).toBeInTheDocument()
    const white = screen.getByRole('region', { name: 'Aprovechable' })
    expect(within(white).getByText('Bolsa blanca')).toBeInTheDocument()
    expect(within(white).getByText('Botella PET')).toBeInTheDocument()
    expect(within(white).getByText('Vacíala y aplástala.')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'No aprovechable' })).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: 'Orgánico' })).getByText('Cáscara de fruta'),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Buenas prácticas' })).toBeInTheDocument()
    expect(screen.getByText('Separa desde el origen')).toBeInTheDocument()
  })

  it('se abre desde la navegación', async () => {
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/classifications/me': () => ({ json: EMPTY_HISTORY }),
      'GET /api/v1/education': () => ({ json: EDUCATION }),
    })
    renderApp('/')

    const nav = await screen.findByRole('navigation', { name: 'Principal' })
    await userEvent.click(within(nav).getByRole('link', { name: 'Aprende' }))

    expect(await screen.findByRole('heading', { name: 'Aprende a separar' })).toBeInTheDocument()
  })

  it('si la carga falla, avisa y permite reintentar', async () => {
    let attempts = 0
    mockApi({
      ...SESSION_ROUTES,
      'GET /api/v1/education': () => {
        attempts += 1
        return attempts === 1 ? { status: 500, json: { detail: 'x' } } : { json: EDUCATION }
      },
    })
    renderApp('/aprende')

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar la guía')
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Botella PET')).toBeInTheDocument()
  })
})
