/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        apple: {
          primary: '#0066cc',
          'primary-focus': '#0071e3',
          'primary-on-dark': '#2997ff',
          ink: '#1d1d1f',
          body: '#1d1d1f',
          'body-on-dark': '#ffffff',
          'body-muted': '#cccccc',
          'ink-muted-80': '#333333',
          'ink-muted-48': '#7a7a7a',
          'divider-soft': '#f0f0f0',
          hairline: '#e0e0e0',
          canvas: '#ffffff',
          parchment: '#f5f5f7',
          pearl: '#fafafc',
          'tile-1': '#272729',
          'tile-2': '#2a2a2c',
          'tile-3': '#252527',
          black: '#000000',
          chip: '#d2d2d7',
        },
      },
      fontFamily: {
        display: ['"SF Pro Display"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Inter"', 'sans-serif'],
        text: ['"SF Pro Text"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Inter"', 'sans-serif'],
      },
      fontSize: {
        'apple-hero': ['56px', { lineHeight: '1.07', letterSpacing: '-0.28px', fontWeight: '600' }],
        'apple-display-lg': ['40px', { lineHeight: '1.1', letterSpacing: '0', fontWeight: '600' }],
        'apple-display-md': ['34px', { lineHeight: '1.47', letterSpacing: '-0.374px', fontWeight: '600' }],
        'apple-lead': ['28px', { lineHeight: '1.14', letterSpacing: '0.196px', fontWeight: '400' }],
        'apple-lead-airy': ['24px', { lineHeight: '1.5', letterSpacing: '0', fontWeight: '300' }],
        'apple-tagline': ['21px', { lineHeight: '1.19', letterSpacing: '0.231px', fontWeight: '600' }],
        'apple-body': ['17px', { lineHeight: '1.47', letterSpacing: '-0.374px', fontWeight: '400' }],
        'apple-body-strong': ['17px', { lineHeight: '1.24', letterSpacing: '-0.374px', fontWeight: '600' }],
        'apple-caption': ['14px', { lineHeight: '1.43', letterSpacing: '-0.224px', fontWeight: '400' }],
        'apple-caption-strong': ['14px', { lineHeight: '1.29', letterSpacing: '-0.224px', fontWeight: '600' }],
        'apple-button-large': ['18px', { lineHeight: '1', letterSpacing: '0', fontWeight: '300' }],
        'apple-fine-print': ['12px', { lineHeight: '1', letterSpacing: '-0.12px', fontWeight: '400' }],
        'apple-micro': ['10px', { lineHeight: '1.3', letterSpacing: '-0.08px', fontWeight: '400' }],
        'apple-nav': ['12px', { lineHeight: '1', letterSpacing: '-0.12px', fontWeight: '400' }],
      },
      borderRadius: {
        'apple-xs': '5px',
        'apple-sm': '8px',
        'apple-md': '11px',
        'apple-lg': '18px',
        'apple-pill': '9999px',
      },
      boxShadow: {
        'apple-product': '3px 5px 30px rgba(0, 0, 0, 0.22)',
      },
      spacing: {
        'apple-section': '80px',
        'apple-xxl': '48px',
      },
    },
  },
  plugins: [],
}
