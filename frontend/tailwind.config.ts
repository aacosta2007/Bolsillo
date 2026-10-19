import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#F4F6F3',
        surface: '#FFFFFF',
        ink: '#16201B',
        muted: '#55615B',
        line: { DEFAULT: '#DDE3DE', soft: '#EEF1EE' },
        primary: { DEFAULT: '#0F5E55', hover: '#0B4740', tint: '#E3F0ED' },
        income: { DEFAULT: '#1D4ED8', tint: '#E4ECFD' },
        expense: { DEFAULT: '#B33A0A', tint: '#FDECE2' },
        warning: { DEFAULT: '#E58A2E', chip: '#FFF0DC', ink: '#8A4A0F' },
        danger: { DEFAULT: '#B33A0A', chip: '#FDE3D6', ink: '#8A2C07' },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        sans: ['Figtree', 'system-ui', 'sans-serif'],
      },
      borderRadius: { card: '20px', xl2: '24px', ctl: '12px', ctl2: '14px' },
    },
  },
  plugins: [],
} satisfies Config;
