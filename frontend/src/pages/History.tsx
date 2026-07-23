import { useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Typography,
  Card,
  CardContent,
  IconButton,
  Chip,
  Alert,
  CircularProgress
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import {
  useOfflineHistory,
  cacheDiagnosis,
  deleteCachedDiagnosis,
  type CachedDiagnosis,
} from '../hooks/useOfflineHistory'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

interface HistoryProps {
  deviceId: string
}

export default function History({ deviceId }: HistoryProps) {
  const queryClient = useQueryClient()
  const { cachedRecords, isOnline, refresh: refreshCache } = useOfflineHistory()

  // Fetch live data when online
  const { data: liveDiagnoses, isLoading, error } = useQuery<CachedDiagnosis[]>({
    queryKey: ['history'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/history`, {
        headers: { 'X-Device-Id': deviceId },
      })
      if (!res.ok) throw new Error('Failed to fetch history')
      return res.json()
    },
    enabled: isOnline,
  })

  // Keep IDB cache in sync with live data
  useEffect(() => {
    if (!liveDiagnoses) return
    const toCache = liveDiagnoses.slice(0, 20)
    Promise.all(toCache.map(d => cacheDiagnosis(d))).then(refreshCache).catch(() => {})
  }, [liveDiagnoses, refreshCache])

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await deleteCachedDiagnosis(id)
      if (isOnline) {
        const res = await fetch(`${API_BASE_URL}/history/${id}`, {
          method: 'DELETE',
          headers: { 'X-Device-Id': deviceId },
        })
        if (!res.ok) throw new Error('Failed to delete on server')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['history'] })
      refreshCache()
    },
  })

  // When online prefer live data; when offline fall back to IDB cache
  const diagnoses: CachedDiagnosis[] = isOnline
    ? (liveDiagnoses ?? cachedRecords)
    : cachedRecords

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 2 }}>
        Diagnosis History
      </Typography>
      {/* Offline banner */}
      {!isOnline && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          You're offline. Showing your last {cachedRecords.length} cached diagnoses.
        </Alert>
      )}
      {isOnline && isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}
      {isOnline && error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error loading history. Showing cached records.
        </Alert>
      )}
      {diagnoses.length === 0 ? (
        <Card sx={{ p: 4, textAlign: 'center', mt: 4, borderRadius: 5, boxShadow: 4 }}>
          <Typography color="text.secondary">No diagnosis history yet. Start by diagnosing a crop!</Typography>
        </Card>
      ) : (
        <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {diagnoses.map((d) => (
            <Card key={d.diagnosis_id} sx={{ p: 2, borderRadius: 4, boxShadow: 3 }}>
              <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box sx={{ flex: 1, minWidth: 0, pr: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                      {d.top3_predictions?.[0]?.disease ?? 'Unknown'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {d.top3_predictions?.[0]?.crop}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                      {new Date(d.created_at).toLocaleDateString()} at{' '}
                      {new Date(d.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </Typography>
                    {d.confidence_score != null && (
                      <Chip
                        label={`Confidence: ${d.confidence_score.toFixed(1)}%`}
                        size="small"
                        color={d.confidence_score >= 60 ? 'success' : 'warning'}
                        sx={{ mt: 1 }}
                      />
                    )}
                  </Box>
                  <IconButton
                    aria-label={`Delete diagnosis from ${new Date(d.created_at).toLocaleDateString()}`}
                    onClick={() => deleteMutation.mutate(d.diagnosis_id)}
                    disabled={deleteMutation.isPending}
                  >
                    <DeleteIcon color="error" />
                  </IconButton>
                </Box>
                {/* Alternative predictions */}
                {d.top3_predictions && d.top3_predictions.length > 1 && (
                  <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                      Other possibilities
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {d.top3_predictions.slice(1).map((pred, idx) => (
                        <Chip
                          key={idx}
                          label={`${pred.disease} (${pred.confidence.toFixed(0)}%)`}
                          size="small"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  )
}
