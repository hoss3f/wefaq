/** frontend/tailwind.config.js */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        linen: '#FAF8F4',
        ink: '#22302C',
        muted: '#6B7B76',
        teal: {
          50: '#EEF4F2',
          100: '#D7E5E1',
          300: '#5E8B80',
          600: '#1F4741',
          700: '#173B36',
          800: '#14302C'
        },
        gold: {
          100: '#F2E7CE',
          300: '#DCC188',
          500: '#C9A15A',
          700: '#9C7A3C'
        },
        brick: {
          500: '#B4543A',
          100: '#F3E1DA'
        }
      },
      fontFamily: {
        display: ['"Aref Ruqaa"', 'serif'],
        body: ['"Tajawal"', 'sans-serif']
      },
      backgroundImage: {
        mashrabiya: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 56 56'%3E%3Cg fill='none' stroke='%231F4741' stroke-width='1.1' opacity='0.14'%3E%3Cpath d='M28 0 L56 28 L28 56 L0 28 Z'/%3E%3Cpath d='M28 8 L48 28 L28 48 L8 28 Z'/%3E%3Ccircle cx='28' cy='28' r='6'/%3E%3C/g%3E%3C/svg%3E\")"
      }
    }
  },
  plugins: []
}
