import { BrowserRouter as Router, Routes, Route, Link as RouterLink, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Link,
  Button,
  useTheme,
  Stack,
} from '@mui/material'
import Diagnose from './pages/Diagnose'
import History from './pages/History'
import Home from './pages/Home'
import Admin from './pages/Admin'
import { ErrorBoundary } from './components/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

function getOrCreateDeviceId(): string {
  let id = localStorage.getItem('device_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('device_id', id)
  }
  return id
}

function AppShell({ deviceId }: { deviceId: string }) {
  const theme = useTheme()
  const location = useLocation()

  const navItems = [
    { label: 'Home', to: '/' },
    { label: 'Diagnose', to: '/diagnose' },
    { label: 'History', to: '/history' },
  ]

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: 'grey.50' }}>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          zIndex: theme.zIndex.drawer + 1,
          background: 'linear-gradient(135deg, #047857 0%, #059669 55%, #10b981 100%)',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between', maxWidth: 1200, mx: 'auto', width: '100%', py: 1 }}>
          <Link
            component={RouterLink}
            to="/"
            sx={{
              textDecoration: 'none',
              color: 'inherit',
              display: 'flex',
              alignItems: 'center',
              gap: 1.25,
            }}
          >
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 2.5,
                display: 'grid',
                placeItems: 'center',
                bgcolor: 'rgba(255,255,255,0.14)',
                backdropFilter: 'blur(6px)',
                fontSize: 20,
              }}
            >
              🌿
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
                AgroScan NG
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.82 }}>
                AI Crop Diagnosis
              </Typography>
            </Box>
          </Link>

          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {navItems.map((item) => (
              <Button
                key={item.to}
                component={RouterLink}
                to={item.to}
                variant={isActive(item.to) ? 'contained' : 'text'}
                color={isActive(item.to) ? 'secondary' : 'inherit'}
                sx={{
                  borderRadius: 999,
                  px: 2,
                  color: isActive(item.to) ? 'common.white' : 'rgba(255,255,255,0.92)',
                  bgcolor: isActive(item.to) ? 'rgba(255,255,255,0.16)' : 'transparent',
                  boxShadow: 'none',
                  '&:hover': {
                    bgcolor: 'rgba(255,255,255,0.14)',
                    boxShadow: 'none',
                  },
                }}
              >
                {item.label}
              </Button>
            ))}
          </Stack>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 }, flexGrow: 1, width: '100%' }}>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/diagnose" element={<Diagnose deviceId={deviceId} />} />
            <Route path="/history" element={<History deviceId={deviceId} />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </ErrorBoundary>
      </Container>

      <Box
        component="footer"
        sx={{
          py: 3,
          borderTop: 1,
          borderColor: 'divider',
          backgroundColor: 'background.paper',
        }}
      >
        <Container
          maxWidth="lg"
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 2,
            flexWrap: 'wrap',
          }}
        >
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            © {new Date().getFullYear()} AgroScan NG — TASUED Final Year Project
          </Typography>
          <Link
            component={RouterLink}
            to="/admin"
            sx={{
              textDecoration: 'none',
              color: 'text.secondary',
              '&:hover': {
                color: 'text.primary',
              },
            }}
          >
            Staff portal
          </Link>
        </Container>
      </Box>
    </Box>
  )
}

function App() {
  const [deviceId, setDeviceId] = useState<string | null>(null)

  useEffect(() => {
    setDeviceId(getOrCreateDeviceId())
  }, [])

  if (!deviceId) return null

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AppShell deviceId={deviceId} />
      </Router>
    </QueryClientProvider>
  )
}

export default App
