import { useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Box, Typography, Card, CardContent, IconButton, Chip, Alert,
  Skeleton, Stack, Divider, Avatar, Tooltip, alpha, useTheme, Button,
} from '@mui/material'
import DeleteRoundedIcon from '@mui/icons-material/DeleteRounded'
import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded'
import WifiOffRoundedIcon from '@mui/icons-material/WifiOffRounded'
import ScienceRoundedIcon from '@mui/icons-material/ScienceRounded'
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import { Link as RouterLink } from 'react-router-dom'
import {
  useOfflineHistory, cacheDiagnosis, deleteCachedDiagnosis, type CachedDiagnosis,
} from '../hooks/useOfflineHistory'
import { AnimatedSection } from '../components/AnimatedSection'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

const CROP_COLORS: Record<string, string> = {
  Cassava: '#059669', Maize: '#d97706', Rice: '#0284c7', Tomato: '#dc2626',
}
const CROP_EMOJI: Record<string, string> = {
  Cassava: '🌿', Maize: '🌽', Rice: '🌾', Tomato: '🍅',
}

function HistorySkeleton() {
  return (
    <Stack spacing={2}>
      {[...Array(3)].map((_, i) => (
        <Card key={i} sx={{ p: 2.5 }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
            <Skeleton variant="rounded" width={48} height={48} sx={{ borderRadius: 3, flexShrink: 0 }} />
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="55%" height={24} sx={{ mb: 0.75 }} />
              <Skeleton variant="text" width="30%" height={18} sx={{ mb: 1 }} />
              <Skeleton variant="rounded" width={100} height={24} sx={{ borderRadius: 2 }} />
            </Box>
          </Box>
        </Card>
      ))}
    </Stack>
  )
}

function DiagnosisCard({ d, onDelete, isDeleting }: {
  d: CachedDiagnosis; onDelete: () => void; isDeleting: boolean
}) {
  const theme = useTheme()
  const top = d.top3_predictions?.[0]
  const crop = top?.crop ?? ''
  const color = CROP_COLORS[crop] ?? theme.palette.primary.main
  const emoji = CROP_EMOJI[crop] ?? '🌱'
  const date = new Date(d.created_at)
  const isHealthy = top?.is_healthy ?? false
  const conf = d.confidence_score ?? 0

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -40, transition: { duration: 0.25 } }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
    >
      <Card className="card-hover" sx={{ overflow: 'hidden' }}>
        {/* Top color accent */}
        <Box sx={{ height: 4, background: isHealthy ? '#059669' : color }} />
        <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
            {/* Crop avatar */}
            <Avatar sx={{
              width: 48, height: 48, borderRadius: 3, flexShrink: 0,
              bgcolor: alpha(color, 0.12), fontSize: '1.5rem',
              border: `1px solid ${alpha(color, 0.25)}`,
            }}>
              {emoji}
            </Avatar>

            {/* Content */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
                <Box sx={{ flex: 1, pr: 1 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.25 }}>
                    {top?.disease ?? 'Unknown'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                    {crop}
                  </Typography>
                </Box>
                <Tooltip title="Delete record">
                  <IconButton
                    size="small" onClick={onDelete} disabled={isDeleting}
                    sx={{
                      color: 'text.disabled', flexShrink: 0,
                      '&:hover': { color: 'error.main', bgcolor: alpha('#ef4444', 0.08) },
                    }}
                  >
                    <DeleteRoundedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, mt: 1.5 }}>
                {d.confidence_score != null && (
                  <Chip
                    label={`${conf.toFixed(1)}% confidence`} size="small"
                    sx={{
                      bgcolor: alpha(isHealthy ? '#059669' : conf >= 70 ? '#ef4444' : '#f59e0b', 0.1),
                      color: isHealthy ? '#047857' : conf >= 70 ? '#dc2626' : '#b45309',
                      fontWeight: 700,
                    }}
                  />
                )}
                {isHealthy && (
                  <Chip label="Healthy ✓" size="small"
                    sx={{ bgcolor: alpha('#059669', 0.1), color: '#047857', fontWeight: 700 }} />
                )}
                <Chip
                  label={date.toLocaleDateString('en-NG', { day: 'numeric', month: 'short', year: 'numeric' })}
                  size="small" variant="outlined"
                  sx={{ color: 'text.secondary', borderColor: 'divider', fontSize: '0.7rem' }}
                />
              </Box>

              {/* Alternative predictions */}
              {d.top3_predictions && d.top3_predictions.length > 1 && (
                <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mb: 0.75, display: 'block' }}>
                    Also considered
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                    {d.top3_predictions.slice(1).map((p, i) => (
                      <Chip key={i} label={`${p.disease} ${p.confidence.toFixed(0)}%`}
                        size="small" variant="outlined"
                        sx={{ fontSize: '0.7rem', height: 22, color: 'text.secondary', borderColor: 'divider' }} />
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  )
}

interface HistoryProps { deviceId: string }

export default function History({ deviceId }: HistoryProps) {
  const theme = useTheme()
  const queryClient = useQueryClient()
  const { cachedRecords, isOnline, refresh: refreshCache } = useOfflineHistory()

  const { data: liveDiagnoses, isLoading, error } = useQuery<CachedDiagnosis[]>({
    queryKey: ['history'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/history`, { headers: { 'X-Device-Id': deviceId } })
      if (!res.ok) throw new Error('Failed to fetch history')
      return res.json()
    },
    enabled: isOnline,
  })

  useEffect(() => {
    if (!liveDiagnoses) return
    Promise.all(liveDiagnoses.slice(0, 20).map(d => cacheDiagnosis(d)))
      .then(refreshCache).catch(() => {})
  }, [liveDiagnoses, refreshCache])

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await deleteCachedDiagnosis(id)
      if (isOnline) {
        const res = await fetch(`${API_BASE_URL}/history/${id}`, {
          method: 'DELETE', headers: { 'X-Device-Id': deviceId },
        })
        if (!res.ok) throw new Error('Delete failed')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['history'] })
      refreshCache()
    },
  })

  const diagnoses: CachedDiagnosis[] = isOnline ? (liveDiagnoses ?? cachedRecords) : cachedRecords

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto' }}>
      {/* Header */}
      <AnimatedSection>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 4 }}>
          <Box sx={{
            width: 44, height: 44, borderRadius: 3,
            background: alpha(theme.palette.primary.main, 0.1),
            display: 'grid', placeItems: 'center',
          }}>
            <HistoryRoundedIcon sx={{ color: 'primary.main' }} />
          </Box>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, lineHeight: 1.1 }}>Diagnosis History</Typography>
            <Typography variant="body2" color="text.secondary">
              {diagnoses.length} record{diagnoses.length !== 1 ? 's' : ''} · {isOnline ? 'Live' : 'Offline cache'}
            </Typography>
          </Box>
        </Box>
      </AnimatedSection>

      {/* Status banners */}
      <AnimatePresence>
        {!isOnline && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
            <Alert severity="warning" icon={<WifiOffRoundedIcon />} sx={{ mb: 3, borderRadius: 3 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>Offline mode</Typography>
              <Typography variant="body2">Showing your last {cachedRecords.length} cached diagnoses.</Typography>
            </Alert>
          </motion.div>
        )}
        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <Alert severity="warning" sx={{ mb: 3, borderRadius: 3 }}>
              Couldn't reach server — showing cached records.
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading skeletons */}
      {isOnline && isLoading && <HistorySkeleton />}

      {/* Empty state */}
      {!isLoading && diagnoses.length === 0 && (
        <AnimatedSection>
          <Card sx={{ p: 6, textAlign: 'center', border: '2px dashed', borderColor: 'divider' }}>
            <Box sx={{ fontSize: '3.5rem', mb: 2 }}>🔬</Box>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>No diagnoses yet</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 320, mx: 'auto' }}>
              Run your first diagnosis to see results here. History is cached for offline viewing.
            </Typography>
            <Button component={RouterLink} to="/diagnose" variant="contained"
              endIcon={<ArrowForwardRoundedIcon />}>
              Start First Diagnosis
            </Button>
          </Card>
        </AnimatedSection>
      )}

      {/* Record list */}
      {!isLoading && diagnoses.length > 0 && (
        <Box>
          {/* Summary row */}
          <AnimatedSection>
            <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
              {[
                { label: 'Total', value: diagnoses.length, color: theme.palette.primary.main },
                {
                  label: 'Healthy',
                  value: diagnoses.filter(d => d.top3_predictions?.[0]?.is_healthy).length,
                  color: '#059669',
                },
                {
                  label: 'Disease detected',
                  value: diagnoses.filter(d => !d.top3_predictions?.[0]?.is_healthy).length,
                  color: '#ef4444',
                },
              ].map(s => (
                <Box key={s.label} sx={{
                  px: 2.5, py: 1.5, borderRadius: 3, border: '1px solid',
                  borderColor: alpha(s.color, 0.25), bgcolor: alpha(s.color, 0.05),
                  flex: '0 0 auto',
                }}>
                  <Typography variant="h5" sx={{ fontWeight: 800, color: s.color, lineHeight: 1 }}>
                    {s.value}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                    {s.label}
                  </Typography>
                </Box>
              ))}
            </Box>
          </AnimatedSection>

          <Divider sx={{ mb: 3 }} />

          <AnimatePresence>
            <Stack spacing={2}>
              {diagnoses.map((d, i) => (
                <AnimatedSection key={d.diagnosis_id} delay={i * 0.04}>
                  <DiagnosisCard
                    d={d}
                    onDelete={() => deleteMutation.mutate(d.diagnosis_id)}
                    isDeleting={deleteMutation.isPending}
                  />
                </AnimatedSection>
              ))}
            </Stack>
          </AnimatePresence>

          {isOnline && liveDiagnoses && liveDiagnoses.length >= 20 && (
            <Box sx={{ mt: 3, textAlign: 'center' }}>
              <Chip icon={<ScienceRoundedIcon />}
                label="Showing most recent 20 diagnoses"
                variant="outlined" sx={{ color: 'text.secondary', borderColor: 'divider' }} />
            </Box>
          )}
        </Box>
      )}
    </Box>
  )
}
