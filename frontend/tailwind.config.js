/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Dark mode defaults
        'dark-bg': '#0D0F12',
        'dark-bg-secondary': '#111318',
        'dark-bg-tertiary': '#16191F',
        'dark-border': '#1E2230',
        // Accent colors
        'accent-amber': '#F59E0B',
        'accent-emerald': '#10B981',
        'accent-rose': '#F43F5E',
        'accent-indigo': '#6366F1',
        'accent-sky': '#38BDF8',
      },
      fontFamily: {
        'sans': ['DM Sans', 'sans-serif'],
        'mono': ['DM Mono', 'monospace'],
        'display': ['Syne', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
