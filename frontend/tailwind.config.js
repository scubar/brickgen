/** @type {import('tailwindcss').Config} */
// ========== Central theme (single source for app colors) ==========
// Use only these keys in components: mint, dk-1..dk-5, danger, success.
// Update this object to change the app-wide palette.
const theme = {
  mint: '#3BBA9C',
  dk: {
    1: '#2E3047',
    2: '#43455C',
    3: '#3C3F58',
    4: '#707793',
    5: '#A8AEC4', // Primary text (lighter for contrast on dark)
  },
  danger: '#F87171',
  success: '#34D399',
}

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: theme,
    },
  },
  plugins: [],
}
