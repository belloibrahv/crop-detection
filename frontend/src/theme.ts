import { createTheme } from '@mui/material/styles';

// AgroScan NG theme — emerald green primary color
const theme = createTheme({
  palette: {
    primary: {
      main: '#059669', // emerald-600
      light: '#10b981', // emerald-500
      dark: '#047857', // emerald-700
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#7c3aed', // violet-600
    },
  },
  typography: {
    fontFamily: 'Roboto, sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none', // Keep button text normal case (no uppercase)
        },
      },
    },
  },
});

export default theme;
