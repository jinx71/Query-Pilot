/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Cool, instrument-like neutrals — not warm cream.
        canvas: '#F5F7FA',
        surface: '#FFFFFF',
        line: '#E3E9F0',
        'line-strong': '#CBD5E1',
        ink: {
          900: '#0B1220',
          700: '#2B3A4F',
          500: '#5B6B82',
          400: '#8493A8',
        },
        // Primary accent: a deep clinical teal for active/running states.
        teal: {
          DEFAULT: '#0E7C73',
          deep: '#0A5A54',
          soft: '#E2F2F0',
        },
        // Semantic status colors that mean something in pharma data.
        status: {
          pass: '#0E9F6E',
          fail: '#E02424',
          warn: '#D97706',
          critical: '#BE123C',
          neutral: '#64748B',
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        panel: '0 1px 2px rgba(11, 18, 32, 0.04), 0 8px 24px rgba(11, 18, 32, 0.06)',
        readout: 'inset 0 0 0 1px rgba(11, 18, 32, 0.06)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulse_dot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.35' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.28s ease-out',
        'pulse-dot': 'pulse_dot 1.1s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
