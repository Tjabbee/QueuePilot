/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          base:     '#080C14',
          surface:  '#0F1624',
          elevated: '#162033',
          hover:    '#1C2840',
        },
        primary: {
          DEFAULT: '#0D9488',
          hover:   '#0F766E',
          light:   '#14B8A6',
        },
        accent: {
          DEFAULT: '#EA580C',
          hover:   '#C2410C',
        },
        border: {
          DEFAULT: '#1A2540',
          light:   '#243350',
        },
      },
      fontFamily: {
        sans: ['Fira Sans', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
