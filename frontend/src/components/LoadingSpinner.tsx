import { CircularProgress, Box, Typography } from '@mui/material'

interface LoadingSpinnerProps {
  size?: number
  message?: string
}

export default function LoadingSpinner({ size = 40, message }: LoadingSpinnerProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 4,
      }}
    >
      <CircularProgress size={size} />
      {message && (
        <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary' }}>
          {message}
        </Typography>
      )}
    </Box>
  )
}
