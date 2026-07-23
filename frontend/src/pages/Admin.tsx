import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// ─── Types ────────────────────────────────────────────────────────────────────

interface DiseaseClass {
  class_id: number
  crop_name: string
  disease_name: string
  is_healthy: boolean
  description: string | null
}

interface Analytics {
  total_diagnoses: number
  low_confidence_count: number
  crop_stats: { crop: string; count: number }[]
}

// ─── Auth helpers ─────────────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem('admin_token')
}

function getRefreshToken() {
  return localStorage.getItem('admin_refresh_token')
}

function authHeaders() {
  return { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' }
}

/** Try to refresh the access token silently. Returns new token or null. */
async function refreshAccessToken(): Promise<string | null> {
  const rt = getRefreshToken()
  if (!rt) return null
  try {
    const res = await fetch(`${API_BASE_URL}/auth/admin/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })
    if (!res.ok) return null
    const { token, refresh_token } = await res.json()
    localStorage.setItem('admin_token', token)
    localStorage.setItem('admin_refresh_token', refresh_token)
    return token
  } catch {
    return null
  }
}

/** Fetch with automatic token refresh on 401. */
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  let res = await fetch(url, { ...options, headers: { ...authHeaders(), ...(options.headers ?? {}) } })
  if (res.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      res = await fetch(url, {
        ...options,
        headers: { Authorization: `Bearer ${newToken}`, 'Content-Type': 'application/json', ...(options.headers ?? {}) },
      })
    }
  }
  return res
}

// ─── Login form ───────────────────────────────────────────────────────────────

function LoginForm({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/auth/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) {
        setError('Invalid email or password.')
        return
      }
      const { token, refresh_token } = await res.json()
      localStorage.setItem('admin_token', token)
      localStorage.setItem('admin_refresh_token', refresh_token)
      onLogin(token)
    } catch {
      setError('Unable to reach the server.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-20">
      <div className="bg-white rounded-xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">Admin Login</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-emerald-600 text-white py-2 rounded-lg font-semibold hover:bg-emerald-700 disabled:bg-gray-400"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ─── Analytics panel ──────────────────────────────────────────────────────────

function AnalyticsPanel() {
  const { data, isLoading, error } = useQuery<Analytics>({
    queryKey: ['admin-analytics'],
    queryFn: async () => {
      const res = await authFetch(`${API_BASE_URL}/admin/analytics/summary`)
      if (!res.ok) throw new Error('Failed to load analytics')
      return res.json()
    },
  })

  if (isLoading) return <p className="text-gray-500">Loading analytics…</p>
  if (error) return <p className="text-red-600">Error loading analytics.</p>
  if (!data) return null

  const lowPct = data.total_diagnoses
    ? ((data.low_confidence_count / data.total_diagnoses) * 100).toFixed(1)
    : '0'

  return (
    <div className="space-y-6">
      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
          <p className="text-sm text-emerald-700 font-medium">Total Diagnoses</p>
          <p className="text-3xl font-bold text-emerald-800 mt-1">{data.total_diagnoses}</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <p className="text-sm text-yellow-700 font-medium">Low Confidence</p>
          <p className="text-3xl font-bold text-yellow-800 mt-1">{data.low_confidence_count}</p>
          <p className="text-xs text-yellow-600 mt-0.5">{lowPct}% of total</p>
        </div>
      </div>

      {/* Diagnoses by crop */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h3 className="font-semibold text-gray-700 mb-3">Diagnoses by Crop</h3>
        {data.crop_stats.length === 0 ? (
          <p className="text-gray-400 text-sm">No data yet.</p>
        ) : (
          <div className="space-y-2">
            {data.crop_stats.map(({ crop, count }) => {
              const pct = data.total_diagnoses ? (count / data.total_diagnoses) * 100 : 0
              return (
                <div key={crop}>
                  <div className="flex justify-between text-sm mb-0.5">
                    <span className="text-gray-700">{crop}</span>
                    <span className="text-gray-500">{count}</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Advisory editor ──────────────────────────────────────────────────────────

function AdvisoryEditor({ disease }: { disease: DiseaseClass }) {
  const queryClient = useQueryClient()
  const [action, setAction] = useState('')
  const [local, setLocal] = useState('')
  const [open, setOpen] = useState(false)
  const [saved, setSaved] = useState(false)

  const saveMutation = useMutation({
    mutationFn: async () => {
      const res = await authFetch(`${API_BASE_URL}/admin/advisory/${disease.class_id}`, {
        method: 'PUT',
        body: JSON.stringify({ recommended_action: action, local_treatment_options: local }),
      })
      if (!res.ok) throw new Error('Save failed')
    },
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      queryClient.invalidateQueries({ queryKey: ['diseases'] })
    },
  })

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-xs text-emerald-600 hover:underline"
      >
        Edit advisory
      </button>
    )
  }

  return (
    <div className="mt-3 space-y-2 border-t pt-3">
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Recommended action</label>
        <textarea
          value={action}
          onChange={e => setAction(e.target.value)}
          rows={3}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="What should the farmer do?"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Local treatment options</label>
        <textarea
          value={local}
          onChange={e => setLocal(e.target.value)}
          rows={2}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="Locally available inputs…"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending || !action}
          className="text-sm bg-emerald-600 text-white px-3 py-1 rounded hover:bg-emerald-700 disabled:bg-gray-400"
        >
          {saveMutation.isPending ? 'Saving…' : saved ? 'Saved ✓' : 'Save'}
        </button>
        <button
          onClick={() => setOpen(false)}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Cancel
        </button>
      </div>
      {saveMutation.isError && (
        <p className="text-red-600 text-xs">Save failed. Try again.</p>
      )}
    </div>
  )
}

// ─── Disease list panel ───────────────────────────────────────────────────────

function DiseasePanel() {
  const [search, setSearch] = useState('')
  const [filterCrop, setFilterCrop] = useState('')

  const { data: diseases = [], isLoading } = useQuery<DiseaseClass[]>({
    queryKey: ['diseases'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/diseases`)
      if (!res.ok) throw new Error('Failed to load diseases')
      return res.json()
    },
  })

  const crops = [...new Set(diseases.map(d => d.crop_name))].sort()

  const visible = diseases.filter(d => {
    const matchesCrop = !filterCrop || d.crop_name === filterCrop
    const matchesSearch =
      !search ||
      d.disease_name.toLowerCase().includes(search.toLowerCase()) ||
      d.crop_name.toLowerCase().includes(search.toLowerCase())
    return matchesCrop && matchesSearch
  })

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          type="search"
          placeholder="Search diseases…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
        <select
          value={filterCrop}
          onChange={e => setFilterCrop(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All crops</option>
          {crops.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {isLoading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="space-y-2">
          {visible.map(d => (
            <div key={d.class_id} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-xs font-medium uppercase tracking-wide text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                    {d.crop_name}
                  </span>
                  <h4 className="font-semibold text-gray-800 mt-1">{d.disease_name}</h4>
                  {d.description && (
                    <p className="text-xs text-gray-500 mt-0.5">{d.description}</p>
                  )}
                </div>
                {d.is_healthy && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Healthy</span>
                )}
              </div>
              {!d.is_healthy && <AdvisoryEditor disease={d} />}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Main Admin page ──────────────────────────────────────────────────────────

export default function Admin() {
  const [token, setToken] = useState<string | null>(getToken)
  const [tab, setTab] = useState<'analytics' | 'diseases'>('analytics')

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_refresh_token')
    setToken(null)
  }

  if (!token) return <LoginForm onLogin={setToken} />

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800">Admin Dashboard</h1>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-600"
        >
          Sign out
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2 border-b border-gray-200">
        {(['analytics', 'diseases'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 px-3 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'analytics' ? 'Analytics' : 'Disease Classes'}
          </button>
        ))}
      </div>

      {tab === 'analytics' ? <AnalyticsPanel /> : <DiseasePanel />}
    </div>
  )
}
