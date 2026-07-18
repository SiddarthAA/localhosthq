import { useEffect, useRef, type ReactNode } from 'react'
import { gsap, prefersReducedMotion } from '../lib/gsap'

type Props = {
  children: ReactNode
  /** rise distance in px */
  y?: number
  delay?: number
  /** stagger direct children instead of the wrapper as one block */
  stagger?: number
  className?: string
  as?: 'div' | 'section' | 'ul' | 'ol' | 'li' | 'header'
}

/** Fade-and-rise on scroll into view. Respects reduced-motion (renders as-is). */
export default function Reveal({
  children,
  y = 26,
  delay = 0,
  stagger,
  className,
  as = 'div',
}: Props) {
  const ref = useRef<HTMLElement>(null)
  const Tag = as as 'div'

  useEffect(() => {
    const el = ref.current
    if (!el || prefersReducedMotion()) return

    const targets =
      stagger != null ? (Array.from(el.children) as HTMLElement[]) : [el]

    const anim = gsap.fromTo(
      targets,
      { y, autoAlpha: 0 },
      {
        y: 0,
        autoAlpha: 1,
        duration: 0.95,
        ease: 'power3.out',
        delay,
        stagger: stagger ?? 0,
        scrollTrigger: { trigger: el, start: 'top 86%', once: true },
      },
    )
    return () => {
      anim.scrollTrigger?.kill()
      anim.kill()
    }
  }, [y, delay, stagger])

  return (
    <Tag ref={ref as never} className={className}>
      {children}
    </Tag>
  )
}
