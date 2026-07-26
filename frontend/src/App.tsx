import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AppBar, Toolbar, Typography, Container, Box, IconButton,
  Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  useTheme, useMediaQuery, Tooltip, Chip,
} from '@mui/material'
import HomeRoundedIcon from '@mui/icons-material/HomeRounded'
import BiotechRoundedIcon from '@mui/icons-material/BiotechRounded'
import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded'
import MenuRoundedIcon from '@mui/icons-material/MenuRounded'
import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import WifiOffRoundedIcon from '@mui/icons-material/WifiOffRounded'
import Diagnose from './pages/Diagnose'
import History from './pages/History'
import Home from './pages/Home'
import Admin from './pages/Admin'
import { ErrorBoundary } from './components/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

function getOrCreateDeviceId(): string {
  let id = localStorage.getItem('device_id')
  if (!id) { id = crypto.randomUUID(); localStorage.setItem('device_id', id) }
  return id
}

const NAV_ITEMS = [
  { label: 'Home',     to: '/',         icon: <HomeRoundedIcon />,    exact: true },
  { label: 'Diagnose', to: '/diagnose', icon: <BiotechRoundedIcon />, exact: false },
  { label: 'History',  to: '/history',  icon: <HistoryRoundedIcon />, exact: false },
]

const PAGE_TRANSITION = {
  initial:  { opacity: 0, y: 12 },
  animate:  { opacity: 1, y: 0 },
  exit:     { opacity: 0, y: -8 },
  transition: { duration: 0.22, ease: 'easeInOut' as const },
}

function AnimatedRoutes({ deviceId }: { deviceId: string }) {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={location.pathname} {...PAGE_TRANSITION} style={{ flex: 1 }}>
        <Routes location={location}>
          <Route path="/"        element={<Home />} />
          <Route path="/diagnose" element={<Diagnose deviceId={deviceId} />} />
          <Route path="/history"  element={<History  deviceId={deviceId} />} />
          <Route path="/admin"    element={<Admin />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  )
}

function AppShell({ deviceId }: { deviceId: string }) {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 8)
    const onOnline  = () => setIsOnline(true)
    const onOffline = () => setIsOnline(false)
    window.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('online',  onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('scroll', handleScroll)
      window.removeEventListener('online',  onOnline)
      window.removeEventListener('offline', onOffline)
    }
  }, [])

  const navLinkSx = (active: boolean) => ({
    display: 'flex', alignItems: 'center', gap: 0.75,
    px: 2, py: 0.9, borderRadius: 999, textDecoration: 'none',
    fontSize: '0.9rem', fontWeight: active ? 700 : 500,
    color: active ? '#fff' : 'rgba(255,255,255,0.82)',
    background: active ? 'rgba(255,255,255,0.18)' : 'transparent',
    border: active ? '1px solid rgba(255,255,255,0.22)' : '1px solid transparent',
    transition: 'all 0.18s ease',
    '&:hover': { background: 'rgba(255,255,255,0.13)', color: '#fff' },
  })

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* ── Offline banner ── */}
      <AnimatePresence>
        {!isOnline && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
          >
            <Box sx={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1,
              py: 0.75, bgcolor: '#f59e0b', color: '#fff', fontSize: '0.82rem', fontWeight: 600,
            }}>
              <WifiOffRoundedIcon sx={{ fontSize: 16 }} />
              You're offline — new diagnoses require a connection
            </Box>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── App Bar ── */}
      <AppBar
        position="sticky"
        sx={{
          background: scrolled
            ? 'linear-gradient(135deg, #065f46 0%, #047857 60%, #059669 100%)'
            : 'linear-gradient(135deg, #047857 0%, #059669 55%, #10b981 100%)',
          backdropFilter: 'blur(12px)',
          boxShadow: scrolled ? '0 4px 24px rgba(4,120,87,0.35)' : 'none',
          transition: 'all 0.3s ease',
        }}
      >
        <Toolbar sx={{ maxWidth: 1200, mx: 'auto', width: '100%', px: { xs: 2, md: 3 }, py: 0.5, gap: 2 }}>
          {/* Logo */}
          <NavLink to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
            <Box sx={{
              width: 42, height: 42, borderRadius: 3,
              background: 'rgba(255,255,255,0.15)',
              border: '1px solid rgba(255,255,255,0.25)',
              backdropFilter: 'blur(8px)',
              display: 'grid', placeItems: 'center', fontSize: 22,
            }}>
              🌿
            </Box>
            <Box>
              <Typography sx={{ fontWeight: 800, fontSize: '1.1rem', lineHeight: 1.1, color: '#fff' }}>
                AgroScan NG
              </Typography>
              <Typography sx={{ fontSize: '0.68rem', opacity: 0.78, color: '#fff', fontWeight: 500 }}>
                AI Crop Diagnosis
              </Typography>
            </Box>
          </NavLink>

          <Box sx={{ flexGrow: 1 }} />

          {/* Desktop nav */}
          {!isMobile && (
            <Box sx={{ display: 'flex', gap: 0.75, alignItems: 'center' }}>
              {NAV_ITEMS.map(({ label, to, icon, exact }) => (
                <NavLink key={to} to={to} end={exact}>
                  {({ isActive }) => (
                    <Box component="span" sx={navLinkSx(isActive)}>
                      <Box sx={{ display: 'flex', fontSize: 17 }}>{icon}</Box>
                      {label}
                    </Box>
                  )}
                </NavLink>
              ))}
              {!isOnline && (
                <Tooltip title="Offline mode">
                  <Chip icon={<WifiOffRoundedIcon />} label="Offline" size="small"
                    sx={{ ml: 1, bgcolor: 'rgba(245,158,11,0.25)', color: '#fcd34d', border: '1px solid rgba(245,158,11,0.4)', fontWeight: 600 }} />
                </Tooltip>
              )}
            </Box>
          )}

          {/* Mobile hamburger */}
          {isMobile && (
            <IconButton onClick={() => setDrawerOpen(true)} sx={{ color: '#fff', ml: 'auto' }}>
              <MenuRoundedIcon />
            </IconButton>
          )}
        </Toolbar>
      </AppBar>

      {/* ── Mobile Drawer ── */}
      <Drawer
        anchor="right" open={drawerOpen} onClose={() => setDrawerOpen(false)}
        slotProps={{
          paper: {
            sx: {
              width: 280,
              background: 'linear-gradient(160deg, #065f46 0%, #047857 100%)',
              color: '#fff',
            },
          },
        }}
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography sx={{ fontWeight: 800, fontSize: '1.1rem' }}>AgroScan NG</Typography>
          <IconButton onClick={() => setDrawerOpen(false)} sx={{ color: 'rgba(255,255,255,0.8)' }}>
            <CloseRoundedIcon />
          </IconButton>
        </Box>
        <List sx={{ px: 1.5, pt: 1 }}>
          {NAV_ITEMS.map(({ label, to, icon, exact }) => (
            <NavLink key={to} to={to} end={exact} style={{ textDecoration: 'none' }}>
              {({ isActive }) => (
                <ListItemButton
                  onClick={() => setDrawerOpen(false)}
                  sx={{
                    borderRadius: 3, mb: 0.5, color: '#fff',
                    background: isActive ? 'rgba(255,255,255,0.18)' : 'transparent',
                    '&:hover': { background: 'rgba(255,255,255,0.12)' },
                  }}
                >
                  <ListItemIcon sx={{ color: '#fff', minWidth: 38 }}>{icon}</ListItemIcon>
                  <ListItemText primary={label} />
                </ListItemButton>
              )}
            </NavLink>
          ))}
        </List>
      </Drawer>

      {/* ── Page content ── */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 }, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <ErrorBoundary>
            <AnimatedRoutes deviceId={deviceId} />
          </ErrorBoundary>
        </Container>
      </Box>

      {/* ── Footer ── */}
      <Box
        component="footer"
        sx={{
          borderTop: '1px solid',
          borderColor: 'divider',
          background: 'linear-gradient(135deg, #f8fafc 0%, #ecfdf5 100%)',
          py: { xs: 4, md: 5 },
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: '1fr 1fr 1fr' },
            gap: 4,
          }}>
            {/* Brand */}
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, mb: 1.5 }}>
                <Box sx={{ fontSize: 22 }}>🌿</Box>
                <Typography sx={{ fontWeight: 800, fontSize: '1.05rem', color: 'primary.dark' }}>
                  AgroScan NG
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 240, lineHeight: 1.7 }}>
                AI-powered crop disease detection for Nigerian smallholder farmers.
                Diagnose in seconds, not days.
              </Typography>
            </Box>

            {/* Academic info */}
            <Box>
              <Typography variant="overline" color="primary.main" sx={{ mb: 1.5, display: 'block' }}>
                Academic Project
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.9 }}>
                Department of Computer &amp; Information Science<br />
                Tai Solarin University of Education (TASUED)<br />
                Ijagun, Ogun State, Nigeria · 2026
              </Typography>
            </Box>

            {/* Quick links */}
            <Box>
              <Typography variant="overline" color="primary.main" sx={{ mb: 1.5, display: 'block' }}>
                Quick Links
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                {[
                  { label: 'Start Diagnosis', to: '/diagnose' },
                  { label: 'View History',    to: '/history' },
                  { label: 'Staff Portal',    to: '/admin' },
                ].map(({ label, to }) => (
                  <NavLink key={to} to={to}
                    style={{ textDecoration: 'none', color: '#475569', fontSize: '0.875rem',
                      fontWeight: 500, transition: 'color 0.15s' }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#059669')}
                    onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
                  >
                    {label}
                  </NavLink>
                ))}
              </Box>
            </Box>
          </Box>

          <Box sx={{ mt: 4, pt: 3, borderTop: '1px solid', borderColor: 'divider',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Typography variant="caption" color="text.disabled">
              © {new Date().getFullYear()} AgroScan NG · TASUED Final Year Project · Built with TensorFlow &amp; React
            </Typography>
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              {['Cassava', 'Maize', 'Rice', 'Tomato'].map(c => (
                <Chip key={c} label={c} size="small"
                  sx={{ fontSize: '0.68rem', height: 22, bgcolor: 'rgba(5,150,105,0.08)', color: 'primary.dark' }} />
              ))}
            </Box>
          </Box>
        </Container>
      </Box>
    </Box>
  )
}

export default function App() {
  const [deviceId, setDeviceId] = useState<string | null>(null)
  useEffect(() => { setDeviceId(getOrCreateDeviceId()) }, [])
  if (!deviceId) return null
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AppShell deviceId={deviceId} />
      </Router>
    </QueryClientProvider>
  )
}
