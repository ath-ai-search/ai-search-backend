// Client-portal design tokens — LIGHT OCEAN family (client asked for light:
// soft warm-white canvas, deep mint/teal accents, dark-ink text — friendly,
// nothing harsh, clearly different from the dark admin console).
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        abyss: '#14102b',        // dark ink (text on mint buttons)
        tide:  '#ffffff',        // card background
        mint:  '#6d4aff',        // primary accent (deepened for white)
        teal:  '#5b3bd6',
        sand:  '#e0821f',        // warm highlight (money/AI)
        coral: '#dd5c46',        // errors / found-nothing
        mist:  '#54527a',        // dim text
        foam:  '#201d33',        // main text (dark ink)
      },
      borderRadius: { card: '16px' },
    },
  },
  plugins: [],
}
