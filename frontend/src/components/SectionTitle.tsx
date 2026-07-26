import { Box, Typography, type SxProps } from '@mui/material'
import { AnimatedSection } from './AnimatedSection'

interface Props {
  overline?: string
  title: string
  subtitle?: string
  align?: 'left' | 'center'
  sx?: SxProps
}

export function SectionTitle({ overline, title, subtitle, align = 'center', sx }: Props) {
  return (
    <AnimatedSection>
      <Box sx={{ textAlign: align, mb: { xs: 5, md: 7 }, ...sx }}>
        {overline && (
          <Typography
            variant="overline"
            sx={{
              color: 'primary.main',
              fontWeight: 700,
              letterSpacing: '0.12em',
              mb: 1.5,
              display: 'block',
            }}
          >
            {overline}
          </Typography>
        )}
        <Typography
          variant="h2"
          sx={{
            fontWeight: 800,
            mb: subtitle ? 2 : 0,
            '& em': {
              fontStyle: 'normal',
              background: 'linear-gradient(135deg, #047857, #10b981)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            },
          }}
          dangerouslySetInnerHTML={{ __html: title }}
        />
        {subtitle && (
          <Typography
            variant="subtitle1"
            color="text.secondary"
            sx={{ maxWidth: 640, mx: align === 'center' ? 'auto' : 0, lineHeight: 1.75 }}
          >
            {subtitle}
          </Typography>
        )}
      </Box>
    </AnimatedSection>
  )
}
