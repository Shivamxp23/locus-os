/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#FAFAF8',
        surface: '#F4F3F0',
        primary: '#1A1A1A',
        secondary: '#5B4FD4',
        success: '#1D9E75',
        warning: '#BA7517',
        danger: '#C0392B',
        'text-primary': '#1A1A1A',
        'text-secondary': '#6B6B6B',
        'text-tertiary': '#9B9B9B',
      },
      borderColor: {
        default: 'rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
}
