/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Light mode defaults
        'light-bg': '#F8FAFC',
        'light-bg-secondary': '#FFFFFF',
        'light-bg-tertiary': '#F1F5F9',
        'light-border': '#DCE3ED',
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
