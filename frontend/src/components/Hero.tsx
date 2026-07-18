import { useEffect, useRef } from 'react'
import { gsap, prefersReducedMotion } from '../lib/gsap'
import { scrollTo } from '../lib/site'
import RoadScene from './RoadScene'
import EtherealShadow from './EtherealShadow'
import './Hero.css'

const TICKER = [
  { label: 'System online', dot: true },
  { label: '4 signals fused' },
  { label: '0 bytes off-device' },
  { label: 'Ed25519 signed' },
  { label: '~$35 edge board' },
]

export default function Hero() {
  const root = useRef<HTMLElement>(null)

  useEffect(() => {
    if (prefersReducedMotion() || !root.current) return
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
      tl.from('.hero__eyebrow', { autoAlpha: 0, y: 14, duration: 0.7 }, 0.1)
        .from('.mask__in', { yPercent: 115, duration: 1.05, stagger: 0.08 }, 0.15)
        .from('.hero__lens', { autoAlpha: 0, scale: 0.9, duration: 1.3, ease: 'power2.out' }, 0.1)
        .from('[data-hero-fade]', { autoAlpha: 0, y: 16, duration: 0.8, stagger: 0.1 }, 0.65)
        .from('.hero__tick', { autoAlpha: 0, y: 10, duration: 0.6, stagger: 0.06 }, 0.9)
      // no scroll-parallax — it left the centre empty on scroll and read as broken
    }, root)
    return () => ctx.revert()
  }, [])

  return (
    <section id="top" className="hero on-dark" data-nav-theme="dark" ref={root}>
      <EtherealShadow tone="teal" className="hero__ether" />
      <div className="hero__grid" aria-hidden="true" />

      <div className="hero__stage">
        <div className="hero__eyebrow u-label">
          <span className="hero__eyebrow-dot" />
          On-device fatigue &amp; crash intelligence for fleets
        </div>

        <h1 className="hero__title hero__title--top display">
          <span className="mask"><span className="mask__in">We don&rsquo;t detect</span></span>
          <span className="mask"><span className="mask__in">drowsiness.</span></span>
        </h1>

        <div className="hero__lens">
          <RoadScene />
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
            real. No crying wolf. No covered cameras.
          </p>
          <button className="hero__scroll" onClick={() => scrollTo('#intro')} type="button">
            <span className="hero__scroll-line" />
            See how it works
          </button>
        </div>
      </div>

      <div className="hero__ticker">
        {TICKER.map((t) => (
          <span className="hero__tick u-label" key={t.label}>
            {t.dot && <span className="hero__tick-dot" />}
            {t.label}
          </span>
        ))}
      </div>
    </section>
  )
}
