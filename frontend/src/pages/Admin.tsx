import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Box, Typography, Button, Card, CardContent, TextField, Alert,
  Stack, Chip, Avatar, CircularProgress, LinearProgress,
  Tab, Tabs, IconButton, InputAdornment, Select, MenuItem,
  FormControl, InputLabel, Tooltip, alpha, useTheme, Paper,
} from '@mui/material'
import AdminPanelSettingsRoundedIcon from '@mui/icons-material/AdminPanelSettingsRounded'
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded'
import BarChartRoundedIcon from '@mui/icons-material/BarChartRounded'
import LocalHospitalRoundedIcon from '@mui/icons-material/LocalHospitalRounded'
import SearchRoundedIcon from '@mui/icons-material/SearchRounded'
import EditRoundedIcon from '@mui/icons-material/EditRounded'
import SaveRoundedIcon from '@mui/icons-material/SaveRounded'
import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded'
import VisibilityOffRoundedIcon from '@mui/icons-material/VisibilityOffRounded'
import TrendingUpRoundedIcon from '@mui/icons-material/TrendingUpRounded'
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded'
import { AnimatedSection } from '../components/AnimatedSection'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// ── Types ────────────────────────────────────────────────────────────────────
interface DiseaseClass {
  class_id: number; crop_name: string; disease_name: string
  is_healthy: boolean; description: string | null
}
interface Analytics {
  total_diagnoses: number; low_confidence_count: number
  crop_stats: { crop: string; count: number }[]
}

// ── Auth helpers ─────────────────────────────────────────────────────────────
function getToken()        { return localStorage.getItem('admin_token') }
function getRefreshToken() { return localStorage.getItem('admin_refresh_token') }
function authHeaders() {
  return { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' }
}
async function refreshAccessToken(): Promise<string | null> {
  const rt = getRefreshToken()
  if (!rt) return null
  try {
    const res = await fetch(`${API_BASE_URL}/auth/admin/refresh`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })
    if (!res.ok) return null
    const { token, refresh_token } = await res.json()
    localStorage.setItem('admin_token', token)
    localStorage.setItem('admin_refresh_token', refresh_token)
    return token
  } catch { return null }
}
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  let res = await fetch(url, { ...options, headers: { ...authHeaders(), ...(options.headers ?? {}) } })
  if (res.status === 401) {
    const t = await refreshAccessToken()
    if (t) res = await fetch(url, {
      ...options, headers: { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json', ...(options.headers ?? {}) }
    })
  }
  return res
}

// ── Login ────────────────────────────────────────────────────────────────────
function LoginForm({ onLogin }: { onLogin: (t: string) => void }) {
  const theme = useTheme()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/auth/admin/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) { setError('Invalid email or password.'); return }
      const { token, refresh_token } = await res.json()
      localStorage.setItem('admin_token', token)
      localStorage.setItem('admin_refresh_token', refresh_token)
      onLogin(token)
    } catch { setError('Unable to reach the server.')
    } finally { setLoading(false) }
  }

  return (
    <Box sx={{ maxWidth: 420, mx: 'auto', mt: { xs: 4, md: 8 } }}>
      <AnimatedSection>
        <Box sx={{ textAlign: 'center', mb: 5 }}>
          <Box sx={{
            width: 64, height: 64, borderRadius: 4, mx: 'auto', mb: 2,
            background: 'linear-gradient(135deg, #047857, #10b981)',
            display: 'grid', placeItems: 'center',
            boxShadow: `0 8px 24px ${alpha(theme.palette.primary.main, 0.35)}`,
          }}>
            <AdminPanelSettingsRoundedIcon sx={{ color: '#fff', fontSize: 32 }} />
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 800, mb: 0.5 }}>Staff Portal</Typography>
          <Typography variant="body2" color="text.secondary">
            AgroScan NG · Admin Dashboard
          </Typography>
        </Box>

        <Card sx={{ overflow: 'hidden' }}>
          <Box sx={{ height: 4, background: 'linear-gradient(90deg, #047857, #10b981)' }} />
          <CardContent sx={{ p: 4 }}>
            <Box component="form" onSubmit={handleSubmit}>
              <Stack spacing={2.5}>
                <TextField
                  label="Email address" type="email" required fullWidth
                  value={email} onChange={e => setEmail(e.target.value)}
                  autoComplete="email" disabled={loading}
                />
                <TextField
                  label="Password" type={showPw ? 'text' : 'password'} required fullWidth
                  value={password} onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password" disabled={loading}
                  slotProps={{
                    input: {
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton onClick={() => setShowPw(p => !p)} edge="end" size="small">
                            {showPw ? <VisibilityOffRoundedIcon fontSize="small" /> : <VisibilityRoundedIcon fontSize="small" />}
                          </IconButton>
                        </InputAdornment>
                      ),
                    },
                  }}
                />
                {error && <Alert severity="error" sx={{ borderRadius: 2 }}>{error}</Alert>}
                <Button type="submit" variant="contained" fullWidth size="large"
                  disabled={loading}
                  endIcon={loading ? <CircularProgress size={18} color="inherit" /> : undefined}
                  sx={{ py: 1.5, fontWeight: 700 }}>
                  {loading ? 'Signing in…' : 'Sign In'}
                </Button>
              </Stack>
            </Box>
          </CardContent>
        </Card>
      </AnimatedSection>
    </Box>
  )
}

// ── KPI Card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, icon, color }: {
  label: string; value: string | number; sub?: string; icon: React.ReactNode; color: string
}) {
  return (
    <Card className="card-hover">
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 700 }}>{label}</Typography>
            <Typography variant="h3" sx={{ fontWeight: 900, color, lineHeight: 1.1, mt: 0.5 }}>
              {value}
            </Typography>
            {sub && <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>{sub}</Typography>}
          </Box>
          <Avatar sx={{ bgcolor: alpha(color, 0.12), color, width: 48, height: 48, borderRadius: 3 }}>
            {icon}
          </Avatar>
        </Box>
      </CardContent>
    </Card>
  )
}

// ── Analytics Panel ───────────────────────────────────────────────────────────
function AnalyticsPanel() {
  const { data, isLoading, error } = useQuery<Analytics>({
    queryKey: ['admin-analytics'],
    queryFn: async () => {
      const res = await authFetch(`${API_BASE_URL}/admin/analytics/summary`)
      if (!res.ok) throw new Error('Failed')
      return res.json()
    },
  })

  if (isLoading) return (
    <Box>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 2, mb: 3 }}>
        {[...Array(2)].map((_, i) => <Card key={i} sx={{ p: 3, height: 110 }}><LinearProgress sx={{ borderRadius: 999 }} /></Card>)}
      </Box>
    </Box>
  )
  if (error) return <Alert severity="error" sx={{ borderRadius: 3 }}>Failed to load analytics.</Alert>
  if (!data) return null

  const lowPct = data.total_diagnoses
    ? ((data.low_confidence_count / data.total_diagnoses) * 100).toFixed(1) : '0'
  const maxCount = Math.max(...data.crop_stats.map(c => c.count), 1)

  return (
    <Stack spacing={3}>
      {/* KPI row */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2,1fr)' }, gap: 2 }}>
        <AnimatedSection>
          <KpiCard label="Total Diagnoses" value={data.total_diagnoses.toLocaleString()}
            icon={<TrendingUpRoundedIcon />} color="#059669" />
        </AnimatedSection>
        <AnimatedSection delay={0.08}>
          <KpiCard label="Low Confidence" value={data.low_confidence_count}
            sub={`${lowPct}% of total`}
            icon={<WarningAmberRoundedIcon />} color="#f59e0b" />
        </AnimatedSection>
      </Box>

      {/* Crop bar chart */}
      <AnimatedSection delay={0.12}>
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <BarChartRoundedIcon sx={{ color: 'primary.main' }} />
              <Typography variant="h6" sx={{ fontWeight: 700 }}>Diagnoses by Crop</Typography>
            </Box>
            {data.crop_stats.length === 0
              ? <Typography variant="body2" color="text.secondary">No diagnoses recorded yet.</Typography>
              : (
                <Stack spacing={2.5}>
                  {data.crop_stats.map(({ crop, count }, i) => {
                    const pct = maxCount ? (count / maxCount) * 100 : 0
                    const colors: Record<string, string> = { Cassava: '#059669', Maize: '#d97706', Rice: '#0284c7', Tomato: '#dc2626' }
                    const color = colors[crop] ?? '#059669'
                    return (
                      <motion.div key={crop} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.07 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.75 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color }} />
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>{crop}</Typography>
                          </Box>
                          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>{count}</Typography>
                        </Box>
                        <LinearProgress variant="determinate" value={pct}
                          sx={{ height: 8, borderRadius: 999, bgcolor: alpha(color, 0.12), '& .MuiLinearProgress-bar': { bgcolor: color } }} />
                      </motion.div>
                    )
                  })}
                </Stack>
              )}
          </CardContent>
        </Card>
      </AnimatedSection>
    </Stack>
  )
}

// ── Advisory Editor ───────────────────────────────────────────────────────────
function AdvisoryEditor({ disease }: { disease: DiseaseClass }) {
  const queryClient = useQueryClient()
  const [open, setOpen]     = useState(false)
  const [action, setAction] = useState('')
  const [local, setLocal]   = useState('')
  const [saved, setSaved]   = useState(false)

  const saveMutation = useMutation({
    mutationFn: async () => {
      const res = await authFetch(`${API_BASE_URL}/admin/advisory/${disease.class_id}`, {
        method: 'PUT',
        body: JSON.stringify({ recommended_action: action, local_treatment_options: local }),
      })
      if (!res.ok) throw new Error('Save failed')
    },
    onSuccess: () => {
      setSaved(true); setTimeout(() => setSaved(false), 2500)
      queryClient.invalidateQueries({ queryKey: ['diseases'] })
    },
  })

  if (!open) return (
    <Button size="small" startIcon={<EditRoundedIcon />} onClick={() => setOpen(true)}
      sx={{ mt: 1, fontSize: '0.78rem', color: 'primary.main' }}>
      Edit advisory
    </Button>
  )

  return (
    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
      transition={{ duration: 0.25 }}>
      <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Stack spacing={2}>
          <TextField multiline rows={3} fullWidth size="small" label="Recommended action"
            value={action} onChange={e => setAction(e.target.value)}
            placeholder="What should the farmer do?" />
          <TextField multiline rows={2} fullWidth size="small" label="Local treatment options"
            value={local} onChange={e => setLocal(e.target.value)}
            placeholder="Locally available inputs…" />

          {saveMutation.isError && (
            <Alert severity="error" sx={{ borderRadius: 2 }}>Save failed. Please try again.</Alert>
          )}

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button size="small" variant="contained" onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || !action}
              startIcon={saved ? <CheckCircleRoundedIcon /> : <SaveRoundedIcon />}
              sx={{ fontWeight: 700 }}>
              {saveMutation.isPending ? 'Saving…' : saved ? 'Saved!' : 'Save'}
            </Button>
            <Button size="small" variant="outlined" color="inherit"
              startIcon={<CloseRoundedIcon />} onClick={() => setOpen(false)}
              sx={{ color: 'text.secondary', borderColor: 'divider' }}>
              Cancel
            </Button>
          </Box>
        </Stack>
      </Box>
    </motion.div>
  )
}

// ── Disease Panel ─────────────────────────────────────────────────────────────
function DiseasePanel() {
  const theme = useTheme()
  const [search, setSearch] = useState('')
  const [filterCrop, setFilterCrop] = useState('')

  const { data: diseases = [], isLoading } = useQuery<DiseaseClass[]>({
    queryKey: ['diseases'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/diseases`)
      if (!res.ok) throw new Error('Failed')
      return res.json()
    },
  })

  const crops = [...new Set(diseases.map(d => d.crop_name))].sort()
  const visible = diseases.filter(d => {
    const matchCrop   = !filterCrop || d.crop_name === filterCrop
    const matchSearch = !search
      || d.disease_name.toLowerCase().includes(search.toLowerCase())
      || d.crop_name.toLowerCase().includes(search.toLowerCase())
    return matchCrop && matchSearch
  })

  const cropColors: Record<string, string> = {
    Cassava: '#059669', Maize: '#d97706', Rice: '#0284c7', Tomato: '#dc2626',
  }

  return (
    <Stack spacing={3}>
      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField size="small" placeholder="Search diseases…"
          value={search} onChange={e => setSearch(e.target.value)} sx={{ flex: '1 1 200px' }}
          slotProps={{
            input: {
              startAdornment: <InputAdornment position="start"><SearchRoundedIcon sx={{ fontSize: 18, color: 'text.secondary' }} /></InputAdornment>,
            },
          }} />
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Crop</InputLabel>
          <Select value={filterCrop} label="Crop" onChange={e => setFilterCrop(e.target.value)} sx={{ borderRadius: 3 }}>
            <MenuItem value=""><em>All crops</em></MenuItem>
            {crops.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
          </Select>
        </FormControl>
      </Box>

      {/* Count */}
      <Typography variant="body2" color="text.secondary">
        Showing {visible.length} of {diseases.length} disease classes
      </Typography>

      {isLoading
        ? <Stack spacing={1.5}>{[...Array(4)].map((_, i) => <Card key={i} sx={{ p: 3, height: 80 }}><LinearProgress /></Card>)}</Stack>
        : (
          <Stack spacing={1.5}>
            {visible.map((d, i) => {
              const color = cropColors[d.crop_name] ?? theme.palette.primary.main
              return (
                <AnimatedSection key={d.class_id} delay={i * 0.03}>
                  <Card sx={{ overflow: 'hidden' }}>
                    <Box sx={{ display: 'flex', borderLeft: '4px solid', borderColor: color }}>
                      <CardContent sx={{ p: 2.5, flex: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
                          <Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <Chip label={d.crop_name} size="small"
                                sx={{ bgcolor: alpha(color, 0.1), color, fontWeight: 700, fontSize: '0.7rem', height: 20 }} />
                              {d.is_healthy && (
                                <Chip label="Healthy" size="small" icon={<CheckCircleRoundedIcon />}
                                  sx={{ bgcolor: alpha('#059669', 0.08), color: '#047857', fontWeight: 700, fontSize: '0.7rem', height: 20 }} />
                              )}
                            </Box>
                            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{d.disease_name}</Typography>
                            {d.description && (
                              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.25, display: 'block' }}>
                                {d.description}
                              </Typography>
                            )}
                          </Box>
                          <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0, ml: 1 }}>
                            ID {d.class_id}
                          </Typography>
                        </Box>
                        {!d.is_healthy && <AdvisoryEditor disease={d} />}
                      </CardContent>
                    </Box>
                  </Card>
                </AnimatedSection>
              )
            })}
          </Stack>
        )
      }
    </Stack>
  )
}

// ── Main Admin page ───────────────────────────────────────────────────────────
export default function Admin() {
  const [token, setToken] = useState<string | null>(getToken)
  const [tab, setTab]     = useState(0)

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_refresh_token')
    setToken(null)
  }

  if (!token) return <LoginForm onLogin={setToken} />

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      {/* Header */}
      <AnimatedSection>
        <Box sx={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          mb: 4, flexWrap: 'wrap', gap: 2,
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{
              width: 44, height: 44, borderRadius: 3,
              background: 'linear-gradient(135deg, #047857, #10b981)',
              display: 'grid', placeItems: 'center',
            }}>
              <AdminPanelSettingsRoundedIcon sx={{ color: '#fff' }} />
            </Box>
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 800, lineHeight: 1.1 }}>Admin Dashboard</Typography>
              <Typography variant="body2" color="text.secondary">AgroScan NG · Staff Portal</Typography>
            </Box>
          </Box>
          <Tooltip title="Sign out">
            <Button variant="outlined" color="error" size="small"
              startIcon={<LogoutRoundedIcon />} onClick={handleLogout}
              sx={{ borderRadius: 999, fontWeight: 600 }}>
              Sign Out
            </Button>
          </Tooltip>
        </Box>
      </AnimatedSection>

      {/* Tabs */}
      <Paper sx={{ mb: 3, border: '1px solid', borderColor: 'divider' }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}
          slotProps={{ indicator: { style: { height: 3, borderRadius: '3px 3px 0 0' } } }}
          sx={{ px: 1 }}>
          <Tab icon={<BarChartRoundedIcon sx={{ fontSize: 18 }} />} iconPosition="start"
            label="Analytics" sx={{ minHeight: 52, gap: 0.5 }} />
          <Tab icon={<LocalHospitalRoundedIcon sx={{ fontSize: 18 }} />} iconPosition="start"
            label="Disease Classes" sx={{ minHeight: 52, gap: 0.5 }} />
        </Tabs>
      </Paper>

      {/* Tab content */}
      <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22 }}>
        {tab === 0 ? <AnalyticsPanel /> : <DiseasePanel />}
      </motion.div>
    </Box>
  )
}
