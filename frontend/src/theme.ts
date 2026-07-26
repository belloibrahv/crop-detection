import { createTheme, alpha } from '@mui/material/styles'

declare module '@mui/material/styles' {
  interface Palette {
    gradient: {
      hero: string
      card: string
      accent: string
    }
  }
  interface PaletteOptions {
    gradient?: {
      hero?: string
      card?: string
      accent?: string
    }
  }
}

const EMERALD = {
  50:  '#ecfdf5',
  100: '#d1fae5',
  200: '#a7f3d0',
  300: '#6ee7b7',
  400: '#34d399',
  500: '#10b981',
  600: '#059669',
  700: '#047857',
  800: '#065f46',
  900: '#064e3b',
}

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      light:        EMERALD[400],
      main:         EMERALD[600],
      dark:         EMERALD[800],
      contrastText: '#ffffff',
    },
    secondary: {
      light: '#a78bfa',
      main:  '#7c3aed',
      dark:  '#5b21b6',
      contrastText: '#ffffff',
    },
    success: {
      main:  EMERALD[500],
      light: EMERALD[300],
      dark:  EMERALD[700],
    },
    error: {
      main:  '#ef4444',
      light: '#fca5a5',
      dark:  '#b91c1c',
    },
    warning: {
      main:  '#f59e0b',
      light: '#fcd34d',
      dark:  '#b45309',
    },
    info: {
      main:  '#3b82f6',
      light: '#93c5fd',
      dark:  '#1d4ed8',
    },
    background: {
      default: '#f8fafc',
      paper:   '#ffffff',
    },
    text: {
      primary:   '#0f172a',
      secondary: '#475569',
      disabled:  '#94a3b8',
    },
    divider: '#e2e8f0',
    gradient: {
      hero:   `linear-gradient(135deg, ${EMERALD[800]} 0%, ${EMERALD[600]} 50%, ${EMERALD[400]} 100%)`,
      card:   `linear-gradient(135deg, ${alpha(EMERALD[50], 0.8)}, ${alpha(EMERALD[100], 0.4)})`,
      accent: `linear-gradient(135deg, #7c3aed 0%, ${EMERALD[600]} 100%)`,
    },
  },

  typography: {
    fontFamily: '"Inter", "Roboto", system-ui, -apple-system, sans-serif',
    fontWeightLight:   300,
    fontWeightRegular: 400,
    fontWeightMedium:  500,
    fontWeightBold:    700,
    h1: { fontSize: 'clamp(2.5rem, 5vw, 4rem)',   fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.1 },
    h2: { fontSize: 'clamp(2rem, 4vw, 3rem)',     fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1.15 },
    h3: { fontSize: 'clamp(1.5rem, 3vw, 2.25rem)', fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1.2 },
    h4: { fontSize: 'clamp(1.25rem, 2.5vw, 1.75rem)', fontWeight: 700, letterSpacing: '-0.01em', lineHeight: 1.25 },
    h5: { fontSize: '1.25rem', fontWeight: 600, lineHeight: 1.3 },
    h6: { fontSize: '1.1rem',  fontWeight: 600, lineHeight: 1.35 },
    subtitle1: { fontSize: '1.05rem', fontWeight: 500, lineHeight: 1.5 },
    subtitle2: { fontSize: '0.9rem',  fontWeight: 600, lineHeight: 1.5 },
    body1: { fontSize: '1rem',   lineHeight: 1.7 },
    body2: { fontSize: '0.875rem', lineHeight: 1.65 },
    caption: { fontSize: '0.75rem', letterSpacing: '0.02em' },
    overline: { fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' },
    button: { fontWeight: 600, letterSpacing: '0.01em' },
  },

  shape: { borderRadius: 12 },

  shadows: [
    'none',
    '0 1px 2px rgba(0,0,0,0.04)',
    '0 1px 4px rgba(0,0,0,0.06)',
    '0 2px 8px rgba(0,0,0,0.08)',
    '0 4px 12px rgba(0,0,0,0.08)',
    '0 6px 16px rgba(0,0,0,0.10)',
    '0 8px 24px rgba(0,0,0,0.10)',
    '0 10px 28px rgba(0,0,0,0.12)',
    '0 12px 32px rgba(0,0,0,0.12)',
    '0 14px 36px rgba(0,0,0,0.14)',
    '0 16px 40px rgba(0,0,0,0.14)',
    '0 18px 44px rgba(0,0,0,0.15)',
    '0 20px 48px rgba(0,0,0,0.15)',
    '0 22px 52px rgba(0,0,0,0.16)',
    '0 24px 56px rgba(0,0,0,0.16)',
    '0 26px 60px rgba(0,0,0,0.17)',
    '0 28px 64px rgba(0,0,0,0.17)',
    '0 30px 68px rgba(0,0,0,0.18)',
    '0 32px 72px rgba(0,0,0,0.18)',
    '0 34px 76px rgba(0,0,0,0.19)',
    '0 36px 80px rgba(0,0,0,0.19)',
    '0 38px 84px rgba(0,0,0,0.20)',
    '0 40px 88px rgba(0,0,0,0.20)',
    '0 42px 92px rgba(0,0,0,0.21)',
    '0 44px 96px rgba(0,0,0,0.22)',
  ] as any,

  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 999,
          paddingTop: 10,
          paddingBottom: 10,
          paddingLeft: 24,
          paddingRight: 24,
          transition: 'all 0.2s cubic-bezier(0.4,0,0.2,1)',
        },
        sizeLarge: { paddingTop: 13, paddingBottom: 13, paddingLeft: 32, paddingRight: 32, fontSize: '1.05rem' },
        sizeSmall: { paddingTop: 6, paddingBottom: 6, paddingLeft: 16, paddingRight: 16, fontSize: '0.8rem' },
      },
    },

    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 20,
          border: '1px solid #e2e8f0',
          transition: 'box-shadow 0.2s ease, transform 0.2s ease',
        },
      },
    },

    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, borderRadius: 8 },
      },
    },

    MuiAppBar: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { borderBottom: '1px solid rgba(255,255,255,0.08)' },
      },
    },

    MuiTextField: {
      defaultProps: { variant: 'outlined' },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: EMERALD[500] },
          },
        },
      },
    },

    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { borderRadius: 20 },
        outlined: { border: '1px solid #e2e8f0' },
      },
    },

    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 12 },
      },
    },

    MuiTooltip: {
      styleOverrides: {
        tooltip: { borderRadius: 8, fontSize: '0.78rem', fontWeight: 500 },
      },
    },

    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 999, height: 6 },
        bar: { borderRadius: 999 },
      },
    },

    MuiSkeleton: {
      styleOverrides: {
        root: { borderRadius: 10 },
      },
    },

    MuiTab: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600, minHeight: 48 },
      },
    },
  },
})

export default theme
export { EMERALD }
