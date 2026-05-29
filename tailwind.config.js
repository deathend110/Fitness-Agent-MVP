/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        fitloop: {
          ink: '#1a1a2e',
          panel: '#20243a',
          line: '#303650',
          orange: '#f97316',
          mint: '#22c55e',
        },
      },
    },
  },
  plugins: [],
}
