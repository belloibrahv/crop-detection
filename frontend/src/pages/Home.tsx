import { Link as RouterLink } from 'react-router-dom'
import heroImage from '../assets/hero.png'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Avatar,
  Paper,
  Stack,
  Alert,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'

const CROPS = [
  { name: 'Cassava', emoji: '🌿', diseases: 1 },
  { name: 'Maize', emoji: '🌽', diseases: 4 },
  { name: 'Tomato', emoji: '🍅', diseases: 8 },
  { name: 'Rice', emoji: '🌾', diseases: 1 },
]

const STEPS = [
  {
    step: '1',
    title: 'Photograph a leaf',
    body: 'Use your phone camera or upload an existing photo from your gallery.',
    icon: '📷',
  },
  {
    step: '2',
    title: 'Select crop type',
    body: 'Optionally tell the app which crop you are photographing.',
    icon: '🌱',
  },
  {
    step: '3',
    title: 'Get your diagnosis',
    body: 'Receive an AI-generated result with treatment advice in seconds.',
    icon: '🤖',
  },
]

export default function Home() {
  const theme = useTheme()

  return (
    <Stack spacing={{ xs: 6, md: 8 }} sx={{ pb: 6 }}>
      {/* Hero section */}
      <Box
        sx={{
          textAlign: 'center',
          pt: { xs: 2, md: 3 },
          px: { xs: 1, md: 0 },
        }}
      >
        <Box
          component="img"
          src={heroImage}
          alt="Farmer inspecting crop leaves"
          sx={{
            mx: 'auto',
            mb: 4,
            width: '100%',
            maxWidth: 860,
            maxHeight: 360,
            objectFit: 'cover',
            borderRadius: 6,
            boxShadow: theme.shadows[8],
          }}
        />
        <Typography
          variant="h3"
          component="h1"
          sx={{
            fontWeight: 800,
            mb: 2,
            color: 'text.primary',
            fontSize: { xs: '2rem', md: '3.2rem' },
          }}
        >
          Crop disease detection for Nigerian farmers
        </Typography>
        <Typography
          variant="body1"
          sx={{
            color: 'text.secondary',
            maxWidth: 700,
            mx: 'auto',
            mb: 4,
            fontSize: { xs: '1rem', md: '1.1rem' },
          }}
        >
          Photograph a diseased leaf and get an AI diagnosis — with plain-language
          treatment advice — in under 5 seconds.
        </Typography>
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            gap: 2,
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          <Button
            component={RouterLink}
            to="/diagnose"
            variant="contained"
            size="large"
            sx={{ px: 4.5, py: 1.6, fontSize: '1rem', fontWeight: 700, borderRadius: 999 }}
          >
            Start Diagnosis
          </Button>
          <Button
            component={RouterLink}
            to="/history"
            variant="outlined"
            size="large"
            sx={{ px: 4.5, py: 1.6, fontSize: '1rem', fontWeight: 700, borderRadius: 999 }}
          >
            View History
          </Button>
        </Box>
      </Box>

      {/* Model limitations notice */}
      <Alert severity="info" sx={{ maxWidth: 800, mx: 'auto', borderRadius: 2 }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          Current Model Coverage
        </Typography>
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          The AI model currently supports Cassava, Maize, Tomato, and Rice. Yam detection is not yet available due to limited training data. We're working to expand coverage.
        </Typography>
      </Alert>

      {/* How it works section */}
      <Box>
        <Typography variant="h4" component="h2" sx={{ fontWeight: 800, textAlign: 'center', mb: 4 }}>
          How it works
        </Typography>
        <Box
          sx={{
            display: 'grid',
            gap: 3,
            gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' },
          }}
        >
          {STEPS.map(({ step, title, body, icon }) => (
            <Card
              key={step}
              sx={{
                height: '100%',
                textAlign: 'center',
                p: 3,
                borderRadius: 5,
                boxShadow: theme.shadows[3],
              }}
            >
                <CardContent>
                  <Typography sx={{ fontSize: '3rem', mb: 1 }}>{icon}</Typography>
                  <Avatar
                    sx={{
                      width: 32,
                      height: 32,
                      mx: 'auto',
                      mb: 1.5,
                      backgroundColor: theme.palette.primary.light,
                      color: theme.palette.primary.contrastText,
                      fontWeight: 700,
                    }}
                  >
                    {step}
                  </Avatar>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                    {title}
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    {body}
                  </Typography>
                </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {/* Supported crops section */}
      <Box>
        <Typography variant="h4" component="h2" sx={{ fontWeight: 800, textAlign: 'center', mb: 4 }}>
          Supported crops
        </Typography>
        <Box
          sx={{
            display: 'grid',
            gap: 2,
            gridTemplateColumns: {
              xs: 'repeat(2, minmax(0, 1fr))',
              md: 'repeat(5, minmax(0, 1fr))',
            },
          }}
        >
          {CROPS.map(({ name, emoji, diseases }) => (
            <Card
              key={name}
              sx={{
                textAlign: 'center',
                p: 2,
                height: '100%',
                borderRadius: 4,
                boxShadow: theme.shadows[2],
              }}
            >
                <Typography sx={{ fontSize: '2.5rem', mb: 1 }}>{emoji}</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {name}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  {diseases} disease{diseases !== 1 ? 's' : ''} detected
                </Typography>
            </Card>
          ))}
        </Box>
      </Box>

      {/* PWA install prompt section */}
      <Box>
        <Paper
          sx={{
            p: 4,
            textAlign: 'center',
            borderRadius: 6,
            background: 'linear-gradient(135deg, rgba(16,185,129,0.14), rgba(4,120,87,0.08))',
            border: `1px solid ${theme.palette.primary.light}`,
          }}
        >
          <Typography sx={{ fontSize: '2.5rem', mb: 1 }}>📲</Typography>
          <Typography variant="h5" sx={{ fontWeight: 800, color: theme.palette.primary.dark, mb: 1 }}>
            Install AgroScan NG
          </Typography>
          <Typography variant="body2" sx={{ color: theme.palette.primary.dark }}>
            Add to your home screen for one-tap access — no app store needed. Works offline for viewing past diagnoses.
          </Typography>
        </Paper>
      </Box>
    </Stack>
  )
}
