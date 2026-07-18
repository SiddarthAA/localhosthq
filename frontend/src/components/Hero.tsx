import { useEffect, useRef } from 'react'
import { gsap, prefersReducedMotion } from '../lib/gsap'
import { scrollTo } from '../lib/site'
import Lens from './Lens'
import './Hero.css'

export default function Hero() {
  const root = useRef<HTMLElement>(null)

  useEffect(() => {
    if (prefersReducedMotion() || !root.current) return
    const ctx = gsap.context(() => {
      // intro sequence — .from() resolves to the natural (visible) end state,
      // so a StrictMode double-invoke can never leave content stuck hidden.
      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
      tl.from('.hero__eyebrow', { autoAlpha: 0, y: 14, duration: 0.7 }, 0.1)
        .from('.mask__in', { yPercent: 115, duration: 1.05, stagger: 0.08 }, 0.15)
        .from(
          '.hero__lens',
          { autoAlpha: 0, scale: 0.9, duration: 1.3, ease: 'power2.out' },
          0.1,
        )
        .from(
          '[data-hero-fade]',
          { autoAlpha: 0, y: 16, duration: 0.8, stagger: 0.12 },
          0.7,
        )

      // scroll parallax — text drifts apart, lens swells & dims as it leaves
      const scrub = {
        trigger: root.current,
        start: 'top top',
        end: 'bottom top',
        scrub: 0.6,
      }
      gsap.to('.hero__title--top', { yPercent: -34, ease: 'none', scrollTrigger: scrub })
      gsap.to('.hero__title--bot', { yPercent: 30, ease: 'none', scrollTrigger: scrub })
      gsap.to('.hero__lens', {
        scale: 1.18,
        autoAlpha: 0.25,
        ease: 'none',
        scrollTrigger: scrub,
      })
    }, root)
    return () => ctx.revert()
  }, [])

  return (
    <section
      id="top"
      className="hero on-dark"
      data-nav-theme="dark"
      ref={root}
    >
      <div className="hero__stage">
        <div className="hero__eyebrow u-label">
          On-device fatigue &amp; crash intelligence for fleets
        </div>

        <h1 className="hero__title hero__title--top display">
          <span className="mask"><span className="mask__in">We don&rsquo;t detect</span></span>
          <span className="mask"><span className="mask__in">drowsiness.</span></span>
        </h1>

        <div className="hero__lens">
          <Lens />
        </div>

        <div className="hero__title-wrap">
          <h2 className="hero__title hero__title--bot display">
            <span className="mask"><span className="mask__in">We decide</span></span>
            <span className="mask"><span className="mask__in">when it matters.</span></span>
          </h2>
          <p className="hero__sub" data-hero-fade>
            The co-pilot your drivers won&rsquo;t rip out.
          </p>
        </div>

        <div className="hero__lede" data-hero-fade>
          <p>
            Every alert is earned — tuned to the driver behind the wheel,
            corroborated across independent signals, and silent until fatigue is
            real. No crying wolf. No covered cameras. Just the moment that counts.
          </p>
        </div>

        <button
          className="hero__scroll u-label"
          data-hero-fade
          onClick={() => scrollTo('#intro')}
          type="button"
        >
          <span className="hero__scroll-chevrons" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M4 8l8 8 8-8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            <svg viewBox="0 0 24 24"><path d="M4 8l8 8 8-8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </span>
          See how it works
        </button>
      </div>
    </section>
  )
}
