import { useEffect, useRef, useState } from 'react'
import { Box, Typography, type SxProps } from '@mui/material'
import { useInView } from 'framer-motion'

interface Props {
  value: number
  suffix?: string
  label: string
  icon: string
  color?: string
  sx?: SxProps
}

function useCountUp(target: number, active: boolean, duration = 1800) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (!active) return
    let start = 0
    const step = target / (duration / 16)
    const timer = setInterval(() => {
      start += step
      if (start >= target) { setCount(target); clearInterval(timer) }
      else setCount(Math.floor(start))
    }, 16)
    return () => clearInterval(timer)
  }, [active, target, duration])
  return count
}

export function StatCard({ value, suffix = '', label, icon, color = '#059669', sx }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })
  const count = useCountUp(value, inView)

  return (
    <Box
      ref={ref}
      className="card-hover"
      sx={{
        p: 3.5,
        borderRadius: 4,
        background: '#fff',
        border: '1px solid #e2e8f0',
        textAlign: 'center',
        cursor: 'default',
        ...sx,
      }}
    >
      <Box sx={{
        fontSize: '2.5rem', mb: 1.5,
        width: 60, height: 60, borderRadius: 3,
        background: `${color}18`,
        display: 'grid', placeItems: 'center', mx: 'auto',
      }}>
        {icon}
      </Box>
      <Typography
        variant="h3"
        sx={{ fontWeight: 900, color, lineHeight: 1, mb: 0.5 }}
      >
        {count.toLocaleString()}{suffix}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
        {label}
      </Typography>
    </Box>
  )
}
