import type { Config } from 'tailwindcss'

// Tokens del sistema de diseño EcoUMB. El "verde bosque" ancla la marca; las bolsas blanca /
// negra / verde de la Resolución 2184 son el motivo visual recurrente.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        forest: {
          50: '#f0fdf4',
          100: '#dcfce7',
          300: '#86efac',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16',
        },
        bag: { white: '#f8fafc', black: '#0f172a', green: '#22c55e' },
      },
      fontFamily: {
        sans: ['"Inter Variable"', 'system-ui', 'sans-serif'],
        display: ['"Bricolage Grotesque Variable"', '"Inter Variable"', 'sans-serif'],
      },
      boxShadow: { card: '0 1px 2px rgb(5 46 22 / 0.06), 0 8px 24px -8px rgb(5 46 22 / 0.18)' },
    },
  },
  plugins: [],
} satisfies Config
