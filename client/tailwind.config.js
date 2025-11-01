/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./components/**/*.{js,ts,vue}",
    "./layouts/**/*.{js,ts,vue}",
    "./pages/**/*.{js,ts,vue}",
    "./composables/**/*.{js,ts,vue}",
    "./app.vue"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif']
      },
      colors: {
        dark: {
          50: '#f0f0f0',
          100: '#d0d0d0',
          200: '#8b949e',
          300: '#6e7681',
          400: '#484f58',
          500: '#30363d',
          600: '#21262d',
          700: '#161b22',
          800: '#0d1117'
        },
        qonto: {
          active: '#3d3d3d',
          hover: 'rgba(5, 5, 5, 0.08)'
        }
      }
    }
  },
  plugins: []
}


