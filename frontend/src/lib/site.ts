import { useEffect } from 'react'
import Lenis from 'lenis'
import { gsap, ScrollTrigger, prefersReducedMotion } from './gsap'

let lenis: Lenis | null = null

/** Smooth-scroll to a section (Lenis when active, native as a fallback). */
export function scrollTo(target: string | HTMLElement) {
  if (lenis) {
    lenis.scrollTo(target, { offset: -20, duration: 1.2 })
    return
  }
  const el =
    typeof target === 'string'
      ? document.querySelector<HTMLElement>(target)
      : target
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/**
 * Site-wide setup: Lenis smooth scroll wired into GSAP's ticker + ScrollTrigger,
 * and a scan that flips the fixed nav/CTA between light and dark as themed
 * sections pass under the header.
 */
export function useSite() {
  useEffect(() => {
    const reduce = prefersReducedMotion()

    if (!reduce) {
      lenis = new Lenis({
        duration: 1.1,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
      })
      ;(window as unknown as { __lenis?: Lenis }).__lenis = lenis
      lenis.on('scroll', ScrollTrigger.update)
      const raf = (time: number) => lenis?.raf(time * 1000)
      gsap.ticker.add(raf)
      gsap.ticker.lagSmoothing(0)

      // sync the nav theme to whichever section sits under the header line
      const sections = gsap.utils.toArray<HTMLElement>('[data-nav-theme]')
      const NAV_LINE = 44
      const applyTheme = () => {
        for (const sec of sections) {
          const r = sec.getBoundingClientRect()
          if (r.top <= NAV_LINE && r.bottom > NAV_LINE) {
            const t = sec.dataset.navTheme || 'light'
            if (document.body.dataset.nav !== t) document.body.dataset.nav = t
            return
          }
        }
      }
      const st = ScrollTrigger.create({ start: 0, end: 'max', onUpdate: applyTheme })
      applyTheme()

      // fonts shift layout — recompute trigger positions once they land
      document.fonts?.ready.then(() => ScrollTrigger.refresh())

      return () => {
        gsap.ticker.remove(raf)
        st.kill()
        lenis?.destroy()
        lenis = null
      }
    }
    return undefined
  }, [])
}
