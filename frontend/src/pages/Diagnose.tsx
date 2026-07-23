import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { cacheDiagnosis } from '../hooks/useOfflineHistory'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  CircularProgress,
  Alert,
  Avatar,
  Chip,
  Stack,
  Paper,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

interface Prediction {
  class_id: number
  crop: string
  disease: string
  is_healthy: boolean
  confidence: number
}

interface DiagnosisResult {
  diagnosis_id: string
  results: Prediction[]
  thumbnail_url: string | null
  advisory?: {
    recommended_action: string
    local_treatment_options?: string
  } | null
  low_confidence: boolean
  created_at: string
}

interface DiagnoseProps {
  deviceId: string
}

const CROPS = ['Cassava', 'Maize', 'Tomato', 'Rice']

export default function Diagnose({ deviceId }: DiagnoseProps) {
  const [image, setImage] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [cropHint, setCropHint] = useState('')
  const [retrainConsent, setRetrainConsent] = useState(false)
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const on = () => setIsOnline(true)
    const off = () => setIsOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])

  const diagnoseMutation = useMutation<DiagnosisResult, Error, FormData>({
    mutationFn: async (formData) => {
      const res = await fetch(`${API_BASE_URL}/diagnose`, {
        method: 'POST',
        headers: { 'X-Device-Id': deviceId },
        body: formData,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.message ?? 'Diagnosis failed. Please try again.')
      }
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImage(file)
    const reader = new FileReader()
    reader.onloadend = () => setPreview(reader.result as string)
    reader.readAsDataURL(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file && (file.type === 'image/jpeg' || file.type === 'image/png')) {
      setImage(file)
      const reader = new FileReader()
      reader.onloadend = () => setPreview(reader.result as string)
      reader.readAsDataURL(file)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!image) return
    const formData = new FormData()
    formData.append('leaf_image', image)
    if (cropHint) formData.append('crop_hint', cropHint)
    formData.append('retrain_consent', String(retrainConsent))
    diagnoseMutation.mutate(formData)
  }

  const resetForm = () => {
    diagnoseMutation.reset()
    setImage(null)
    setPreview(null)
    setCropHint('')
    setRetrainConsent(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // Result view
  if (diagnoseMutation.isSuccess && diagnoseMutation.data) {
    const { data } = diagnoseMutation
    return (
      <Box sx={{ maxWidth: 'sm', mx: 'auto', mt: 4 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 4, textAlign: 'center' }}>
          Diagnosis Results
        </Typography>
        <Card sx={{ p: 4, borderRadius: 5, boxShadow: 6 }}>
          <CardContent sx={{ p: 0 }}>
            {data.low_confidence && (
              <Alert severity="warning" sx={{ mb: 3 }}>
                Low confidence result. Please retake the photo in better lighting, focusing on a single leaf.
              </Alert>
            )}
            {/* Thumbnail */}
            {data.thumbnail_url && (
              <Box sx={{ textAlign: 'center', mb: 3 }}>
                <Avatar
                  src={`${API_BASE_URL.replace('/api/v1', '')}${data.thumbnail_url}`}
                  alt="Submitted leaf"
                  sx={{ width: 128, height: 128, mx: 'auto', borderRadius: 2 }}
                />
              </Box>
            )}
            {/* Top predictions */}
            <Stack spacing={1.25} sx={{ mb: 3 }}>
              {data.results.map((pred, idx) => (
                <Paper
                  key={idx}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    py: 1.5,
                    px: 2,
                    borderRadius: 3,
                    bgcolor: idx === 0 ? 'rgba(5,150,105,0.06)' : 'grey.50',
                  }}
                >
                  <Box>
                    <Typography
                      variant={idx === 0 ? 'h6' : 'body1'}
                      sx={{ fontWeight: idx === 0 ? 'bold' : 'normal' }}
                    >
                      {pred.disease}
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                      {pred.crop}
                    </Typography>
                  </Box>
                  <Chip
                    label={`${pred.confidence.toFixed(1)}%`}
                    color={pred.is_healthy ? 'success' : idx === 0 ? 'error' : 'default'}
                    variant="outlined"
                  />
                </Paper>
              ))}
            </Stack>

            {/* Healthy message */}
            {data.results[0]?.is_healthy && (
              <Alert severity="success" sx={{ mb: 3 }}>
                <Typography variant="body2">
                  <strong>✅ This leaf looks healthy!</strong> No treatment is needed.
                </Typography>
              </Alert>
            )}

            {/* Treatment advisory */}
            {data.advisory && !data.results[0]?.is_healthy && (
              <Alert severity="info" sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Treatment Advice
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  {data.advisory.recommended_action}
                </Typography>
                {data.advisory.local_treatment_options && (
                  <Typography variant="caption" sx={{ display: 'block' }}>
                    <strong>Local options:</strong> {data.advisory.local_treatment_options}
                  </Typography>
                )}
              </Alert>
            )}

            <Button
              variant="contained"
              fullWidth
              onClick={resetForm}
              sx={{ mt: 2, py: 1.5 }}
            >
              New Diagnosis
            </Button>
          </CardContent>
        </Card>
      </Box>
    )
  }

  // Upload/capture form
  return (
    <Box sx={{ maxWidth: 'sm', mx: 'auto', mt: 4 }}>
      <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 4, textAlign: 'center' }}>
        Diagnose Crop Disease
      </Typography>
      {!isOnline && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          You're offline. A network connection is required to submit a diagnosis.
        </Alert>
      )}

      <Card component="form" onSubmit={handleSubmit} sx={{ p: 4, borderRadius: 5, boxShadow: 6 }}>
        {/* Image upload */}
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel shrink id="upload-label">Leaf Image</InputLabel>
          <Box
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            sx={{
              border: 2,
              borderStyle: 'dashed',
              borderColor: isDragging ? 'primary.main' : 'divider',
              borderRadius: 2,
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              backgroundColor: isDragging ? 'action.hover' : 'background.paper',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                borderColor: 'primary.light',
                backgroundColor: 'action.hover',
              },
            }}
          >
            <CloudUploadIcon sx={{ fontSize: '4rem', color: 'primary.main', mb: 1 }} />
            <Typography variant="h6" sx={{ mb: 0.5 }}>
              Drag and drop your leaf image here, or click to select
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              JPEG or PNG · Max 8 MB · Min 224×224 px
            </Typography>
            <input
              type="file"
              accept="image/jpeg,image/png"
              capture="environment"
              ref={fileInputRef}
              onChange={handleFileChange}
              aria-label="Upload or capture a leaf image"
              style={{ display: 'none' }}
            />
          </Box>
        </FormControl>

        {/* Preview */}
        {preview && (
          <Box sx={{ mb: 3, position: 'relative' }}>
            <Box
              component="img"
              src={preview}
              alt="Selected leaf preview"
              sx={{
                maxHeight: 256,
                mx: 'auto',
                display: 'block',
                borderRadius: 2,
                boxShadow: 2,
                objectFit: 'contain',
              }}
            />
            <Button
              variant="outlined"
              size="small"
              sx={{ position: 'absolute', top: 8, right: 8, backgroundColor: 'background.paper' }}
              onClick={() => {
                setImage(null)
                setPreview(null)
                if (fileInputRef.current) fileInputRef.current.value = ''
              }}
            >
              ✕ Remove
            </Button>
          </Box>
        )}

        {/* Crop selector */}
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel id="crop-select-label">Crop Type (optional)</InputLabel>
          <Select
            labelId="crop-select-label"
            value={cropHint}
            label="Crop Type (optional)"
            onChange={(e) => setCropHint(e.target.value)}
          >
            <MenuItem value="">Select crop…</MenuItem>
            {CROPS.map((crop) => (
              <MenuItem key={crop} value={crop}>{crop}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Retrain consent */}
        <FormControlLabel
          control={
            <Checkbox
              checked={retrainConsent}
              onChange={(e) => setRetrainConsent(e.target.checked)}
            />
          }
          label="I consent to this image being used to improve the AI model. Your image will not be shared with third parties."
          sx={{ mb: 3 }}
        />

        <Button
          type="submit"
          variant="contained"
          fullWidth
          disabled={!image || diagnoseMutation.isPending || !isOnline}
          startIcon={diagnoseMutation.isPending ? <CircularProgress size={20} /> : null}
          sx={{ py: 1.5 }}
        >
          {diagnoseMutation.isPending ? 'Analysing…' : 'Diagnose'}
        </Button>

        {diagnoseMutation.isError && (
          <Alert severity="error" sx={{ mt: 3 }}>
            {diagnoseMutation.error.message}
          </Alert>
        )}
      </Card>
    </Box>
  )
}
