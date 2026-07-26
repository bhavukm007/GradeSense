import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#07111f',
          900: '#0b1728',
          800: '#132238',
          700: '#1d304a',
        },
        cyan: {
          400: '#2dd4bf',
          500: '#14b8a6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        panel: '0 20px 60px -32px rgb(2 12 27 / 0.65)',
      },
    },
  },
  plugins: [],
} satisfies Config
