import { useRef } from 'react'
import { motion, useInView, type Transition } from 'framer-motion'
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  delay?: number
  direction?: 'up' | 'left' | 'right' | 'none'
  className?: string
}

export function AnimatedSection({ children, delay = 0, direction = 'up', className }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  const transition: Transition = {
    duration: 0.55,
    delay,
    ease: 'easeOut',
  }

  const hidden = {
    opacity: 0,
    y: direction === 'up' ? 32 : 0,
    x: direction === 'left' ? -32 : direction === 'right' ? 32 : 0,
  }

  const visible = {
    opacity: 1,
    y: 0,
    x: 0,
  }

  return (
    <motion.div
      ref={ref}
      initial={hidden}
      animate={inView ? { ...visible, transition } : hidden}
      className={className}
    >
      {children}
    </motion.div>
  )
}
