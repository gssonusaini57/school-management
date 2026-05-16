/** Khalsa International — Tailwind preset
 *  Drop into tailwind.config.js: { presets: [require('./design-tokens/tailwind.preset.js')] }
 */
module.exports = {
  theme: {
    extend: {
      colors: {
        'khalsa-blue':  '#0E2F8E',
        'royal-gold':   '#F5C518',
        'sangat-red':   '#E11D2C',
        'vasant-cream': '#FFF6CC',
        'deep-indigo':  '#08205C',
        ink: '#1A1A1A',
        neutral: {
          50:  '#F8F8F9',
          100: '#EEEEF0',
          200: '#D9D9DD',
          300: '#BCBCC2',
          400: '#8E8E96',
          500: '#6B6B72',
          600: '#4F4F55',
          700: '#3A3A3F',
          800: '#27272B',
          900: '#1A1A1A',
          950: '#0E0E10',
        },
        success: '#15803D',
        warning: '#B45309',
        error:   '#E11D2C',
        info:    '#0E2F8E',
      },
      fontFamily: {
        display:    ['"Playfair Display"', 'Georgia', 'serif'],
        crest:      ['Cinzel', '"Playfair Display"', 'Georgia', 'serif'],
        body:       ['Manrope', '"Helvetica Neue"', 'Arial', 'sans-serif'],
        gurmukhi:   ['"Noto Sans Gurmukhi"', 'system-ui', 'sans-serif'],
        mono:       ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        'display':     ['56px', { lineHeight: '1.05', letterSpacing: '-0.02em', fontWeight: '800' }],
        'heading-xl':  ['40px', { lineHeight: '1.1',  letterSpacing: '-0.015em', fontWeight: '700' }],
        'heading-lg':  ['32px', { lineHeight: '1.15', letterSpacing: '-0.01em',  fontWeight: '700' }],
        'heading-md':  ['24px', { lineHeight: '1.2', fontWeight: '600' }],
        'heading-sm':  ['18px', { lineHeight: '1.3', fontWeight: '700' }],
        'body':        ['16px', { lineHeight: '1.4' }],
        'body-sm':     ['14px', { lineHeight: '1.4' }],
        'caption':     ['12px', { lineHeight: '1.3', letterSpacing: '0.02em', fontWeight: '500' }],
        'crest-caps':  ['12px', { lineHeight: '1.2', letterSpacing: '0.32em', fontWeight: '600' }],
      },
      spacing: {
        '0':  '0px',  '1':  '4px',  '2':  '8px',  '3':  '12px',
        '4':  '16px', '5':  '20px', '6':  '24px', '8':  '32px',
        '10': '40px', '12': '48px', '16': '64px', '20': '80px',
        '24': '96px', '32': '128px',
      },
      borderRadius: {
        none: '0px', sm: '4px', md: '8px', lg: '12px', xl: '16px', full: '9999px',
      },
      boxShadow: {
        '1': '0 1px 2px rgba(14, 14, 16, 0.06)',
        '2': '0 2px 6px rgba(14, 14, 16, 0.08)',
        '3': '0 8px 20px rgba(14, 14, 16, 0.10)',
        '4': '0 16px 32px rgba(14, 14, 16, 0.12)',
        '5': '0 24px 48px rgba(14, 14, 16, 0.16)',
        seal: '0 0 0 6px #FFF6CC, 0 8px 24px rgba(14, 47, 142, 0.18)',
      },
      transitionDuration: { fast: '120ms', base: '200ms', slow: '320ms' },
      transitionTimingFunction: {
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
        decelerate: 'cubic-bezier(0, 0, 0, 1)',
        accelerate: 'cubic-bezier(0.3, 0, 1, 1)',
      },
      screens: { sm: '640px', md: '768px', lg: '1024px', xl: '1280px', '2xl': '1536px' },
      zIndex: { base: '0', dropdown: '1000', sticky: '1100', modal: '1200', toast: '1300' },
    },
  },
  plugins: [],
};
