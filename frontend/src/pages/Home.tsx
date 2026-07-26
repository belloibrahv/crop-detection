import { useState, useEffect, useCallback } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Box, Typography, Button, Card, CardContent, Chip, Stack,
  Paper, Avatar, Divider, alpha, useTheme,
} from '@mui/material'
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import CameraAltRoundedIcon from '@mui/icons-material/CameraAltRounded'
import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import VerifiedRoundedIcon from '@mui/icons-material/VerifiedRounded'
import SchoolRoundedIcon from '@mui/icons-material/SchoolRounded'
import ChevronLeftRoundedIcon from '@mui/icons-material/ChevronLeftRounded'
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded'
import { AnimatedSection } from '../components/AnimatedSection'
import { SectionTitle } from '../components/SectionTitle'
import { StatCard } from '../components/StatCard'

// ── Data ────────────────────────────────────────────────────────────────────
const CROPS = [
  { name: 'Cassava', emoji: '🌿', diseases: 5,  color: '#059669', bg: '#ecfdf5',
    desc: 'Mosaic disease, bacterial blight, green mottle & more' },
  { name: 'Maize',   emoji: '🌽', diseases: 6,  color: '#d97706', bg: '#fffbeb',
    desc: 'Common rust, leaf blight, fall armyworm & more' },
  { name: 'Rice',    emoji: '🌾', diseases: 5,  color: '#0284c7', bg: '#eff6ff',
    desc: 'Blast, bacterial leaf blight, brown spot & more' },
  { name: 'Tomato',  emoji: '🍅', diseases: 8,  color: '#dc2626', bg: '#fef2f2',
    desc: 'Late blight, early blight, leaf curl virus & more' },
]

const STEPS = [
  { icon: <CameraAltRoundedIcon sx={{ fontSize: 28 }} />, step: '01',
    title: 'Photograph a leaf', color: '#059669',
    body: 'Snap a clear photo of the affected leaf using your phone camera or upload an existing image from your gallery.' },
  { icon: <AutoAwesomeRoundedIcon sx={{ fontSize: 28 }} />, step: '02',
    title: 'AI analyses the image', color: '#7c3aed',
    body: 'Our MobileNetV2 deep learning model classifies the disease across 24 classes in under 3 seconds.' },
  { icon: <VerifiedRoundedIcon sx={{ fontSize: 28 }} />, step: '03',
    title: 'Get your diagnosis', color: '#0284c7',
    body: 'Receive the top-3 predictions with confidence scores and plain-language treatment advice in your language.' },
]

const FEATURES = [
  '24 disease classes across 4 crops',
  'Works on any smartphone browser',
  'No app installation required',
  'Offline history viewing',
  'Plain-language treatment advice',
  'Results in under 5 seconds',
  'Based on MobileNetV2 transfer learning',
  'Free for Nigerian smallholder farmers',
]

const SLIDES = [
  { title: 'Real-time AI Diagnosis',     body: 'Upload a leaf photo and receive an AI-powered diagnosis in seconds — no specialist needed.', emoji: '🔬', accent: '#059669' },
  { title: 'Locally Relevant Crops',     body: 'Trained on cassava, maize, rice and tomato — the four crops most affected by disease in Nigeria.', emoji: '🌾', accent: '#d97706' },
  { title: 'Designed for Rural Access',  body: 'A Progressive Web App that works on entry-level smartphones with minimal data usage.', emoji: '📱', accent: '#0284c7' },
  { title: 'Treatment Recommendations',  body: 'Each diagnosis includes locally appropriate treatment advice linked to available inputs.', emoji: '💊', accent: '#7c3aed' },
]

const TEAM = [
  {
    name: 'Adenuga Joshua Oluwasegun',
    matric: '20220294006',
    role: 'Student Researcher',
    department: 'Computer & Information Science',
    avatar: 'AJ',
    color: '#059669',
  },
  {
    name: 'Abiodun Taiwo Caleb',
    matric: '20220294017',
    role: 'Student Researcher',
    department: 'Computer & Information Science',
    avatar: 'AT',
    color: '#7c3aed',
  },
  {
    name: 'Prof. A. A. Owoade',
    matric: null,
    role: 'Project Supervisor',
    department: 'Tai Solarin University of Education',
    avatar: 'PO',
    color: '#0284c7',
    isSupervisor: true,
  },
]

// ── Carousel ────────────────────────────────────────────────────────────────
function HeroCarousel() {
  const [idx, setIdx] = useState(0)
  const [dir, setDir] = useState(1)

  const go = useCallback((next: number) => {
    setDir(next > idx ? 1 : -1)
    setIdx(next)
  }, [idx])

  useEffect(() => {
    const t = setInterval(() => go((idx + 1) % SLIDES.length), 4500)
    return () => clearInterval(t)
  }, [idx, go])

  const enter = useCallback((d: number) => ({ x: d > 0 ? 60 : -60, opacity: 0 }), [])
  const exitAnim = useCallback((d: number) => ({ x: d > 0 ? -60 : 60, opacity: 0 }), [])

  const slide = SLIDES[idx]
  return (
    <Box sx={{ position: 'relative', overflow: 'hidden', borderRadius: 4, minHeight: 220 }}>
      <AnimatePresence initial={false} custom={dir} mode="wait">
        <motion.div key={idx} custom={dir}
          initial={enter(dir)}
          animate={{ x: 0, opacity: 1, transition: { duration: 0.45, ease: 'easeOut' } }}
          exit={exitAnim(dir)}
        >
          <Paper sx={{
            p: { xs: 4, md: 5 }, borderRadius: 4, textAlign: 'center',
            background: `linear-gradient(135deg, ${alpha(slide.accent, 0.07)}, ${alpha(slide.accent, 0.02)})`,
            border: `1px solid ${alpha(slide.accent, 0.2)}`,
          }}>
            <Typography sx={{ fontSize: '3.5rem', mb: 2, lineHeight: 1 }}>{slide.emoji}</Typography>
            <Typography variant="h5" sx={{ fontWeight: 800, mb: 1.5, color: slide.accent }}>
              {slide.title}
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 480, mx: 'auto', lineHeight: 1.75 }}>
              {slide.body}
            </Typography>
          </Paper>
        </motion.div>
      </AnimatePresence>

      {/* Dots + arrows */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1.5, mt: 2.5 }}>
        <Button onClick={() => go((idx - 1 + SLIDES.length) % SLIDES.length)}
          size="small" sx={{ minWidth: 32, width: 32, height: 32, p: 0, borderRadius: '50%',
            border: '1px solid', borderColor: 'divider', color: 'text.secondary' }}>
          <ChevronLeftRoundedIcon sx={{ fontSize: 18 }} />
        </Button>
        {SLIDES.map((_, i) => (
          <Box key={i} onClick={() => go(i)} sx={{
            width: i === idx ? 24 : 8, height: 8, borderRadius: 999,
            bgcolor: i === idx ? 'primary.main' : 'divider',
            cursor: 'pointer', transition: 'all 0.3s ease',
          }} />
        ))}
        <Button onClick={() => go((idx + 1) % SLIDES.length)}
          size="small" sx={{ minWidth: 32, width: 32, height: 32, p: 0, borderRadius: '50%',
            border: '1px solid', borderColor: 'divider', color: 'text.secondary' }}>
          <ChevronRightRoundedIcon sx={{ fontSize: 18 }} />
        </Button>
      </Box>
    </Box>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
export default function Home() {
  const theme = useTheme()

  return (
    <Stack spacing={0}>

      {/* ══ HERO ══ */}
      <Box sx={{ pt: { xs: 4, md: 6 }, pb: { xs: 8, md: 10 } }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 6, alignItems: 'center' }}>
          {/* Left: text */}
          <AnimatedSection>
            <Chip label="🎓 TASUED Final Year Project · 2026" size="small"
              sx={{ mb: 3, bgcolor: alpha(theme.palette.primary.main, 0.1),
                color: 'primary.dark', fontWeight: 700, border: '1px solid', borderColor: alpha(theme.palette.primary.main, 0.25) }} />
            <Typography variant="h1" sx={{ mb: 3, fontWeight: 900 }}>
              Crop Disease{' '}
              <Box component="span" sx={{
                background: 'linear-gradient(135deg, #047857, #10b981)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
              }}>
                Detection
              </Box>{' '}
              for Nigerian Farmers
            </Typography>
            <Typography variant="body1" color="text.secondary"
              sx={{ mb: 4, maxWidth: 520, fontSize: '1.1rem', lineHeight: 1.8 }}>
              Photograph a diseased leaf — get an AI diagnosis with plain-language treatment advice
              in under 5 seconds. No specialist. No app download. No delay.
            </Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <Button component={RouterLink} to="/diagnose" variant="contained" size="large"
                endIcon={<ArrowForwardRoundedIcon />}
                sx={{ px: 4, py: 1.6, fontSize: '1rem', fontWeight: 700 }}>
                Start Free Diagnosis
              </Button>
              <Button component={RouterLink} to="/history" variant="outlined" size="large"
                sx={{ px: 4, py: 1.6, fontSize: '1rem', fontWeight: 700 }}>
                View History
              </Button>
            </Stack>
            <Stack direction="row" spacing={3} sx={{ mt: 4 }}>
              {['Free to use', 'No install needed', 'Works offline'].map(f => (
                <Box key={f} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  <CheckCircleRoundedIcon sx={{ fontSize: 16, color: 'primary.main' }} />
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>{f}</Typography>
                </Box>
              ))}
            </Stack>
          </AnimatedSection>

          {/* Right: carousel */}
          <AnimatedSection delay={0.15} direction="right">
            <HeroCarousel />
          </AnimatedSection>
        </Box>
      </Box>

      {/* ══ STATS ══ */}
      <Box sx={{ py: { xs: 7, md: 10 }, borderTop: '1px solid', borderBottom: '1px solid', borderColor: 'divider',
        background: 'linear-gradient(135deg, #f8fafc, #ecfdf5)' }}>
        <AnimatedSection>
          <Typography variant="overline" sx={{ display: 'block', textAlign: 'center', color: 'primary.main', mb: 4 }}>
            Project at a glance
          </Typography>
        </AnimatedSection>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2,1fr)', md: 'repeat(4,1fr)' }, gap: 3 }}>
          {[
            { value: 24,    suffix: '',   label: 'Disease Classes',      icon: '🦠', color: '#059669' },
            { value: 48163, suffix: '+',  label: 'Training Images',       icon: '🖼️', color: '#7c3aed' },
            { value: 54,    suffix: '/54',label: 'Tests Passing',          icon: '✅', color: '#0284c7' },
            { value: 5,     suffix: 's',  label: 'Avg. Response Time',     icon: '⚡', color: '#d97706' },
          ].map((s, i) => (
            <AnimatedSection key={s.label} delay={i * 0.08}>
              <StatCard {...s} />
            </AnimatedSection>
          ))}
        </Box>
      </Box>

      {/* ══ HOW IT WORKS ══ */}
      <Box sx={{ py: { xs: 8, md: 12 } }}>
        <SectionTitle overline="Simple Process" title='How it <em>works</em>'
          subtitle="Three steps from symptom to solution — all from your smartphone browser." />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3,1fr)' }, gap: 3 }}>
          {STEPS.map(({ icon, step, title, body, color }, i) => (
            <AnimatedSection key={step} delay={i * 0.1}>
              <Card className="card-hover" sx={{ p: 0.5, height: '100%' }}>
                <CardContent sx={{ p: 3.5 }}>
                  <Box sx={{
                    width: 56, height: 56, borderRadius: 3, mb: 2.5,
                    background: alpha(color, 0.1), display: 'grid', placeItems: 'center',
                    color, border: `1px solid ${alpha(color, 0.2)}`,
                  }}>
                    {icon}
                  </Box>
                  <Typography variant="overline" sx={{ color, fontWeight: 800, mb: 0.75, display: 'block' }}>
                    Step {step}
                  </Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.25 }}>{title}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.75 }}>{body}</Typography>
                </CardContent>
              </Card>
            </AnimatedSection>
          ))}
        </Box>
      </Box>

      {/* ══ SUPPORTED CROPS ══ */}
      <Box sx={{ py: { xs: 8, md: 12 }, bgcolor: '#f8fafc', mx: -3, px: 3, borderRadius: 6 }}>
        <SectionTitle overline="Coverage" title='Supported <em>Crops</em>'
          subtitle="Four staple crops covering 24 disease classes — all documented in the 2024 NAERLS Nigeria agricultural survey." />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2,1fr)', md: 'repeat(4,1fr)' }, gap: 3 }}>
          {CROPS.map(({ name, emoji, diseases, color, bg, desc }, i) => (
            <AnimatedSection key={name} delay={i * 0.08}>
              <Card className="card-hover" sx={{ height: '100%', overflow: 'hidden' }}>
                <Box sx={{ height: 6, background: color }} />
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{
                    width: 52, height: 52, borderRadius: 3, mb: 2, fontSize: '1.75rem',
                    background: bg, display: 'grid', placeItems: 'center',
                  }}>{emoji}</Box>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>{name}</Typography>
                  <Chip label={`${diseases} diseases`} size="small"
                    sx={{ mb: 1.5, bgcolor: alpha(color, 0.12), color, fontWeight: 700 }} />
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.65 }}>{desc}</Typography>
                </CardContent>
              </Card>
            </AnimatedSection>
          ))}
        </Box>
      </Box>

      {/* ══ FEATURES GRID ══ */}
      <Box sx={{ py: { xs: 8, md: 12 } }}>
        <SectionTitle overline="Why AgroScan NG" title='Built for <em>real</em> conditions'
          subtitle="Designed around the connectivity, device, and language constraints of Nigerian smallholder farming." />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2,1fr)', md: 'repeat(4,1fr)' }, gap: 2 }}>
          {FEATURES.map((f, i) => (
            <AnimatedSection key={f} delay={i * 0.05}>
              <Box sx={{
                p: 2.5, borderRadius: 3, border: '1px solid', borderColor: 'divider',
                display: 'flex', alignItems: 'center', gap: 1.5, bgcolor: 'background.paper',
                transition: 'border-color 0.2s', '&:hover': { borderColor: 'primary.main' },
              }}>
                <CheckCircleRoundedIcon sx={{ color: 'primary.main', fontSize: 20, flexShrink: 0 }} />
                <Typography variant="body2" sx={{ fontWeight: 500 }}>{f}</Typography>
              </Box>
            </AnimatedSection>
          ))}
        </Box>
      </Box>

      {/* ══ TEAM & SUPERVISOR ══ */}
      <Box sx={{ py: { xs: 8, md: 12 }, bgcolor: '#f8fafc', mx: -3, px: 3, borderRadius: 6 }}>
        <SectionTitle overline="The Team" title='Student <em>Researchers</em> &amp; Supervisor'
          subtitle="This project was developed in partial fulfilment of the B.Sc. Computer Science degree at TASUED, Ijagun." />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3,1fr)' }, gap: 3, maxWidth: 900, mx: 'auto' }}>
          {TEAM.map(({ name, matric, role, department, avatar, color, isSupervisor }, i) => (
            <AnimatedSection key={name} delay={i * 0.1}>
              <Card className="card-hover" sx={{
                p: 0, height: '100%', textAlign: 'center',
                ...(isSupervisor && {
                  border: '2px solid', borderColor: color,
                  boxShadow: `0 8px 32px ${alpha(color, 0.18)}`,
                }),
              }}>
                {isSupervisor && (
                  <Box sx={{ bgcolor: color, py: 0.75, px: 2 }}>
                    <Typography variant="overline" sx={{ color: '#fff', fontWeight: 800, fontSize: '0.65rem' }}>
                      Project Supervisor
                    </Typography>
                  </Box>
                )}
                <CardContent sx={{ p: 3.5 }}>
                  <Avatar sx={{
                    width: 72, height: 72, mx: 'auto', mb: 2,
                    bgcolor: color, fontSize: '1.5rem', fontWeight: 800,
                    boxShadow: `0 4px 20px ${alpha(color, 0.35)}`,
                  }}>
                    {avatar}
                  </Avatar>
                  {isSupervisor && (
                    <SchoolRoundedIcon sx={{ color, mb: 1, fontSize: 22 }} />
                  )}
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>{name}</Typography>
                  <Typography variant="body2" sx={{ color, fontWeight: 600, mb: 0.75 }}>{role}</Typography>
                  {matric && (
                    <Chip label={`Matric: ${matric}`} size="small"
                      sx={{ mb: 1.25, bgcolor: alpha(color, 0.1), color, fontWeight: 700 }} />
                  )}
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.6 }}>
                    {department}
                  </Typography>
                </CardContent>
              </Card>
            </AnimatedSection>
          ))}
        </Box>

        {/* Institution badge */}
        <AnimatedSection delay={0.3}>
          <Box sx={{
            mt: 5, p: 3, borderRadius: 4, maxWidth: 560, mx: 'auto', textAlign: 'center',
            background: 'linear-gradient(135deg, #ecfdf5, #d1fae5)',
            border: '1px solid', borderColor: alpha('#059669', 0.3),
          }}>
            <Typography variant="overline" sx={{ color: 'primary.dark', fontWeight: 700, mb: 1, display: 'block' }}>
              Institution
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 800, color: 'primary.dark' }}>
              Tai Solarin University of Education (TASUED)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Department of Computer &amp; Information Science ·{' '}
              College of Science and Information Technology · Ijagun, Ogun State, Nigeria
            </Typography>
          </Box>
        </AnimatedSection>
      </Box>

      {/* ══ PWA CTA ══ */}
      <Box sx={{ py: { xs: 8, md: 10 } }}>
        <AnimatedSection>
          <Paper sx={{
            p: { xs: 5, md: 7 }, textAlign: 'center', borderRadius: 6,
            background: 'linear-gradient(135deg, #047857 0%, #059669 50%, #10b981 100%)',
            color: '#fff', border: 'none', overflow: 'hidden', position: 'relative',
          }}>
            {/* Background decoration */}
            <Box sx={{
              position: 'absolute', width: 300, height: 300, borderRadius: '50%',
              background: 'rgba(255,255,255,0.05)', top: -100, right: -80,
            }} />
            <Box sx={{
              position: 'absolute', width: 200, height: 200, borderRadius: '50%',
              background: 'rgba(255,255,255,0.04)', bottom: -60, left: -40,
            }} />

            <Typography sx={{ fontSize: '3rem', mb: 2, position: 'relative' }}>📲</Typography>
            <Typography variant="h3" sx={{ fontWeight: 900, mb: 2, color: '#fff', position: 'relative' }}>
              Install AgroScan NG
            </Typography>
            <Typography variant="body1"
              sx={{ mb: 4, color: 'rgba(255,255,255,0.88)', maxWidth: 520, mx: 'auto', lineHeight: 1.75, position: 'relative' }}>
              Add to your home screen for instant one-tap access — no app store, no storage used.
              Cached diagnoses remain viewable even without internet.
            </Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'center', position: 'relative' }}>
              <Button component={RouterLink} to="/diagnose" size="large"
                sx={{
                  bgcolor: '#fff', color: 'primary.dark', fontWeight: 700,
                  px: 4, '&:hover': { bgcolor: 'rgba(255,255,255,0.92)' },
                  boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
                }}
                endIcon={<ArrowForwardRoundedIcon />}>
                Try It Now — Free
              </Button>
            </Stack>
            <Divider sx={{ my: 4, borderColor: 'rgba(255,255,255,0.2)', position: 'relative' }} />
            <Stack direction="row" spacing={4} sx={{ justifyContent: 'center', flexWrap: 'wrap', position: 'relative' }}>
              {['54,000+ hectares affected annually', '24 disease classes', '5-second diagnosis'].map(stat => (
                <Box key={stat} sx={{ textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.75)', fontWeight: 500 }}>{stat}</Typography>
                </Box>
              ))}
            </Stack>
          </Paper>
        </AnimatedSection>
      </Box>

    </Stack>
  )
}
