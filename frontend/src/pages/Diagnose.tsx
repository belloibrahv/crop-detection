import { useState, useRef, useEffect, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { cacheDiagnosis } from '../hooks/useOfflineHistory'
import {
  Box, Typography, Button, Card, CardContent, Select, MenuItem,
  FormControlLabel, Checkbox, CircularProgress, Alert, Avatar,
  Chip, Stack, Paper, LinearProgress, alpha, useTheme, Divider,
  FormControl, InputLabel, Tooltip, IconButton,
} from '@mui/material'
import CloudUploadRoundedIcon from '@mui/icons-material/CloudUploadRounded'
import CameraAltRoundedIcon from '@mui/icons-material/CameraAltRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import RestartAltRoundedIcon from '@mui/icons-material/RestartAltRounded'
import DeleteRoundedIcon from '@mui/icons-material/DeleteRounded'
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import { AnimatedSection } from '../components/AnimatedSection'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

interface Prediction {
  class_id: number; crop: string; disease: string
  is_healthy: boolean; confidence: number
}
interface DiagnosisResult {
  diagnosis_id: string; results: Prediction[]
  thumbnail_url: string | null
  advisory?: { recommended_action: string; local_treatment_options?: string } | null
  low_confidence: boolean; created_at: string
}
interface DiagnoseProps { deviceId: string }

const CROPS = ['Cassava', 'Maize', 'Rice', 'Tomato']

const CROP_COLORS: Record<string, string> = {
  Cassava: '#059669', Maize: '#d97706', Rice: '#0284c7', Tomato: '#dc2626',
}

function confidenceColor(pct: number, healthy: boolean) {
  if (healthy) return '#059669'
  if (pct >= 75) return '#dc2626'
  if (pct >= 50) return '#d97706'
  return '#64748b'
}

// ── Upload Zone ──────────────────────────────────────────────────────────────
interface UploadZoneProps {
  preview: string | null
  isDragging: boolean
  onFile: (f: File) => void
  onDragOver: (e: React.DragEvent) => void
  onDragLeave: () => void
  onDrop: (e: React.DragEvent) => void
  onClear: () => void
  inputRef: React.RefObject<HTMLInputElement>
  disabled: boolean
}
function UploadZone({ preview, isDragging, onFile, onDragOver, onDragLeave, onDrop, onClear, inputRef, disabled }: UploadZoneProps) {
  const theme = useTheme()
  return (
    <Box sx={{ position: 'relative' }}>
      <input
        type="file" accept="image/jpeg,image/png" capture="environment"
        ref={inputRef}
        onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f) }}
        style={{ display: 'none' }}
        aria-label="Upload or capture a leaf image"
      />
      <AnimatePresence mode="wait">
        {preview ? (
          <motion.div key="preview" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.22 }}>
            <Box sx={{ position: 'relative', borderRadius: 4, overflow: 'hidden', border: '2px solid', borderColor: 'primary.main' }}>
              <Box component="img" src={preview} alt="Leaf preview"
                sx={{ width: '100%', maxHeight: 320, objectFit: 'cover', display: 'block' }} />
              <Box sx={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(to top, rgba(0,0,0,0.55) 0%, transparent 50%)',
              }} />
              <Box sx={{ position: 'absolute', bottom: 12, left: 12, right: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <Chip label="Image selected ✓" size="small" sx={{ bgcolor: 'rgba(5,150,105,0.9)', color: '#fff', fontWeight: 700 }} />
                <Tooltip title="Remove image">
                  <IconButton size="small" onClick={onClear} disabled={disabled}
                    sx={{ bgcolor: 'rgba(0,0,0,0.55)', color: '#fff', '&:hover': { bgcolor: 'rgba(0,0,0,0.75)' } }}>
                    <DeleteRoundedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
          </motion.div>
        ) : (
          <motion.div key="dropzone" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Box
              onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
              onClick={() => !disabled && inputRef.current?.click()}
              sx={{
                border: '2px dashed',
                borderColor: isDragging ? 'primary.main' : alpha(theme.palette.primary.main, 0.35),
                borderRadius: 4, py: 6, px: 3, textAlign: 'center',
                cursor: disabled ? 'default' : 'pointer',
                background: isDragging ? alpha(theme.palette.primary.main, 0.05) : 'transparent',
                transition: 'all 0.2s ease',
                '&:hover': !disabled ? {
                  borderColor: 'primary.main',
                  background: alpha(theme.palette.primary.main, 0.04),
                } : {},
              }}
            >
              <motion.div animate={isDragging ? { scale: 1.1 } : { scale: 1 }} transition={{ duration: 0.2 }}>
                <Box sx={{
                  width: 72, height: 72, borderRadius: '50%', mx: 'auto', mb: 2.5,
                  background: alpha(theme.palette.primary.main, 0.1),
                  display: 'grid', placeItems: 'center',
                }}>
                  <CloudUploadRoundedIcon sx={{ fontSize: 36, color: 'primary.main' }} />
                </Box>
              </motion.div>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                {isDragging ? 'Drop it here!' : 'Drag & drop or click to upload'}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
                JPEG or PNG · Max 8 MB · Min 224 × 224 px
              </Typography>
              <Stack direction="row" spacing={1.5} sx={{ justifyContent: 'center' }}>
                <Button variant="contained" size="small" startIcon={<CloudUploadRoundedIcon />}
                  onClick={e => { e.stopPropagation(); !disabled && inputRef.current?.click() }} disabled={disabled}>
                  Browse files
                </Button>
                <Button variant="outlined" size="small" startIcon={<CameraAltRoundedIcon />}
                  onClick={e => { e.stopPropagation(); !disabled && inputRef.current?.click() }} disabled={disabled}>
                  Use camera
                </Button>
              </Stack>
            </Box>
          </motion.div>
        )}
      </AnimatePresence>
    </Box>
  )
}

// ── Result Card ──────────────────────────────────────────────────────────────
function ResultCard({ data, onReset }: { data: DiagnosisResult; onReset: () => void }) {
  const theme = useTheme()
  const top = data.results[0]
  const isHealthy = top?.is_healthy ?? false

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}>
      <Box>
        {/* Header strip */}
        <Box sx={{
          p: 3.5, borderRadius: '20px 20px 0 0',
          background: isHealthy
            ? 'linear-gradient(135deg, #047857, #10b981)'
            : `linear-gradient(135deg, ${theme.palette.error.dark}, ${theme.palette.error.main})`,
          color: '#fff', display: 'flex', alignItems: 'center', gap: 2.5,
        }}>
          {data.thumbnail_url && (
            <Avatar src={`${API_BASE_URL.replace('/api/v1', '')}${data.thumbnail_url}`}
              alt="Submitted leaf"
              sx={{ width: 64, height: 64, borderRadius: 3, border: '2px solid rgba(255,255,255,0.4)', flexShrink: 0 }} />
          )}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              {isHealthy
                ? <CheckCircleRoundedIcon sx={{ fontSize: 22 }} />
                : <WarningAmberRoundedIcon sx={{ fontSize: 22 }} />}
              <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.85)', fontWeight: 700 }}>
                {isHealthy ? 'Healthy Leaf' : 'Disease Detected'}
              </Typography>
            </Box>
            <Typography variant="h5" sx={{ fontWeight: 800, color: '#fff', lineHeight: 1.2 }}>
              {top?.disease ?? 'Unknown'}
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)', mt: 0.5 }}>
              {top?.crop} · {new Date(data.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
            </Typography>
          </Box>
          <Box sx={{ textAlign: 'right', flexShrink: 0 }}>
            <Typography sx={{ fontSize: '2rem', fontWeight: 900, color: '#fff', lineHeight: 1 }}>
              {top?.confidence.toFixed(0)}%
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>confidence</Typography>
          </Box>
        </Box>

        {/* Body */}
        <Card sx={{ borderRadius: '0 0 20px 20px', border: '1px solid', borderColor: 'divider', borderTop: 'none' }}>
          <CardContent sx={{ p: 3.5 }}>
            {data.low_confidence && (
              <Alert severity="warning" icon={<WarningAmberRoundedIcon />} sx={{ mb: 3, borderRadius: 3 }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>Low confidence</Typography>
                <Typography variant="body2">Retake in natural light, one leaf filling the frame.</Typography>
              </Alert>
            )}

            {/* Top-3 predictions */}
            <Typography variant="overline" color="primary.main" sx={{ mb: 1.5, display: 'block' }}>
              Top predictions
            </Typography>
            <Stack spacing={1.25} sx={{ mb: 3 }}>
              {data.results.map((pred, i) => {
                const pct = pred.confidence
                const color = confidenceColor(pct, pred.is_healthy)
                return (
                  <motion.div key={i} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.08 }}>
                    <Paper sx={{
                      p: 2, borderRadius: 3,
                      border: '1px solid', borderColor: i === 0 ? alpha(color, 0.4) : 'divider',
                      bgcolor: i === 0 ? alpha(color, 0.04) : 'background.paper',
                    }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: i === 0 ? 1.25 : 0 }}>
                        <Box sx={{
                          width: 32, height: 32, borderRadius: 2, flexShrink: 0,
                          bgcolor: alpha(CROP_COLORS[pred.crop] ?? '#059669', 0.1),
                          display: 'grid', placeItems: 'center',
                          fontSize: '1rem',
                        }}>
                          {pred.crop === 'Cassava' ? '🌿' : pred.crop === 'Maize' ? '🌽' : pred.crop === 'Rice' ? '🌾' : '🍅'}
                        </Box>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant={i === 0 ? 'subtitle1' : 'body2'} sx={{ fontWeight: i === 0 ? 700 : 500 }}>
                            {pred.disease}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">{pred.crop}</Typography>
                        </Box>
                        <Chip
                          label={`${pct.toFixed(1)}%`} size="small"
                          sx={{ bgcolor: alpha(color, 0.12), color, fontWeight: 700, border: `1px solid ${alpha(color, 0.3)}` }}
                        />
                      </Box>
                      {i === 0 && (
                        <Box>
                          <LinearProgress variant="determinate" value={Math.min(pct, 100)}
                            sx={{
                              height: 6, borderRadius: 999,
                              bgcolor: alpha(color, 0.12),
                              '& .MuiLinearProgress-bar': { bgcolor: color },
                            }} />
                        </Box>
                      )}
                    </Paper>
                  </motion.div>
                )
              })}
            </Stack>

            {/* Treatment advisory */}
            {isHealthy ? (
              <Alert severity="success" icon={<CheckCircleRoundedIcon />} sx={{ mb: 3, borderRadius: 3 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Leaf looks healthy!</Typography>
                <Typography variant="body2">No disease treatment is required.</Typography>
              </Alert>
            ) : data.advisory && (
              <Box sx={{ p: 3, borderRadius: 3, bgcolor: alpha('#3b82f6', 0.05), border: '1px solid', borderColor: alpha('#3b82f6', 0.2) }}>
                <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
                  <InfoOutlinedIcon sx={{ color: '#3b82f6', fontSize: 20, flexShrink: 0, mt: 0.25 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#1d4ed8' }}>Treatment Advice</Typography>
                </Box>
                <Typography variant="body2" sx={{ mb: 1.5, lineHeight: 1.75 }}>{data.advisory.recommended_action}</Typography>
                {data.advisory.local_treatment_options && (
                  <>
                    <Divider sx={{ my: 1.5 }} />
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Local options: </Typography>
                    <Typography variant="caption" color="text.secondary">{data.advisory.local_treatment_options}</Typography>
                  </>
                )}
              </Box>
            )}

            <Button variant="contained" fullWidth size="large" onClick={onReset}
              startIcon={<RestartAltRoundedIcon />} sx={{ mt: 2, py: 1.5, fontWeight: 700 }}>
              New Diagnosis
            </Button>
          </CardContent>
        </Card>
      </Box>
    </motion.div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function Diagnose({ deviceId }: DiagnoseProps) {
  const theme = useTheme()
  const [image, setImage] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [cropHint, setCropHint] = useState('')
  const [consent, setConsent] = useState(false)
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null!)

  useEffect(() => {
    const on = () => setIsOnline(true); const off = () => setIsOnline(false)
    window.addEventListener('online', on); window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])

  const setFile = useCallback((f: File) => {
    setImage(f)
    const reader = new FileReader()
    reader.onloadend = () => setPreview(reader.result as string)
    reader.readAsDataURL(f)
  }, [])

  const clearImage = useCallback(() => {
    setImage(null); setPreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [])

  const mutation = useMutation<DiagnosisResult, Error, FormData>({
    mutationFn: async (fd) => {
      const res = await fetch(`${API_BASE_URL}/diagnose`, {
        method: 'POST', headers: { 'X-Device-Id': deviceId }, body: fd,
      })
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.message ?? 'Diagnosis failed.') }
      return res.json()
    },
    onSuccess: (data) => {
      cacheDiagnosis({
        diagnosis_id: data.diagnosis_id,
        predicted_class_id: data.results[0]?.class_id ?? null,
        confidence_score: data.results[0]?.confidence ?? null,
        top3_predictions: data.results,
        created_at: data.created_at,
      }).catch(() => {})
    },
  })

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f && (f.type === 'image/jpeg' || f.type === 'image/png')) setFile(f)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault(); if (!image) return
    const fd = new FormData()
    fd.append('leaf_image', image)
    if (cropHint) fd.append('crop_hint', cropHint)
    fd.append('retrain_consent', String(consent))
    mutation.mutate(fd)
  }

  if (mutation.isSuccess && mutation.data) {
    return (
      <Box sx={{ maxWidth: 600, mx: 'auto' }}>
        <ResultCard data={mutation.data} onReset={() => {
          mutation.reset(); clearImage(); setCropHint(''); setConsent(false)
        }} />
      </Box>
    )
  }

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto' }}>
      <AnimatedSection>
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
            <Box sx={{
              width: 44, height: 44, borderRadius: 3,
              background: alpha(theme.palette.primary.main, 0.1),
              display: 'grid', placeItems: 'center',
            }}>
              <AutoAwesomeRoundedIcon sx={{ color: 'primary.main' }} />
            </Box>
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 800, lineHeight: 1.1 }}>Diagnose Crop Disease</Typography>
              <Typography variant="body2" color="text.secondary">AI-powered analysis in under 5 seconds</Typography>
            </Box>
          </Box>
        </Box>
      </AnimatedSection>

      {!isOnline && (
        <Alert severity="warning" sx={{ mb: 3, borderRadius: 3 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>You're offline</Typography>
          <Typography variant="body2">A network connection is required to submit a diagnosis.</Typography>
        </Alert>
      )}

      {mutation.isError && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 3 }} onClose={() => mutation.reset()}>
          {mutation.error?.message}
        </Alert>
      )}

      <Card component="form" onSubmit={handleSubmit} sx={{ overflow: 'visible' }}>
        <CardContent sx={{ p: { xs: 3, md: 4 } }}>
          {/* Upload zone */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 0.5 }}>
              Leaf Image <Typography component="span" sx={{ color: 'error.main', fontWeight: 700 }}>*</Typography>
            </Typography>
            <UploadZone
              preview={preview} isDragging={isDragging}
              onFile={setFile}
              onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop} onClear={clearImage}
              inputRef={fileInputRef} disabled={mutation.isPending}
            />
          </Box>

          {/* Crop hint */}
          <FormControl fullWidth sx={{ mb: 2.5 }}>
            <InputLabel>Crop type (optional)</InputLabel>
            <Select value={cropHint} label="Crop type (optional)" onChange={e => setCropHint(e.target.value)}
              disabled={mutation.isPending} sx={{ borderRadius: 3 }}>
              <MenuItem value=""><em>Auto-detect</em></MenuItem>
              {CROPS.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </Select>
          </FormControl>

          {/* Consent */}
          <FormControlLabel
            control={<Checkbox checked={consent} onChange={e => setConsent(e.target.checked)} color="primary" />}
            label={
              <Typography variant="body2" color="text.secondary">
                I consent to my image being used to improve the model
              </Typography>
            }
            sx={{ mb: 3 }}
          />

          <Button type="submit" variant="contained" fullWidth size="large" disabled={!image || mutation.isPending || !isOnline}
            endIcon={mutation.isPending ? <CircularProgress size={18} color="inherit" /> : <ArrowForwardRoundedIcon />}
            sx={{ py: 1.6, fontWeight: 700, fontSize: '1rem' }}>
            {mutation.isPending ? 'Analysing…' : 'Run Diagnosis'}
          </Button>

          {mutation.isPending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Box sx={{ mt: 2.5 }}>
                <LinearProgress sx={{ borderRadius: 999 }} />
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 1 }}>
                  Running AI inference — usually under 3 seconds
                </Typography>
              </Box>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* Info chips */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 3, justifyContent: 'center' }}>
        {['24 disease classes', '4 crops', 'Cassava · Maize · Rice · Tomato'].map(t => (
          <Chip key={t} label={t} size="small"
            sx={{ bgcolor: alpha(theme.palette.primary.main, 0.08), color: 'primary.dark', fontWeight: 600 }} />
        ))}
      </Box>
    </Box>
  )
}
