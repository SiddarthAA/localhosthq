import Reveal from './Reveal'
import Logo from './Logo'
import EtherealShadow from './EtherealShadow'
import './FooterCTA.css'

export default function FooterCTA() {
  return (
    <section id="contact" className="cta section on-dark" data-nav-theme="dark">
      <EtherealShadow tone="mixed" className="cta__ether" />
      <span className="cta__ghost" aria-hidden="true">RidewMe</span>

      <div className="shell cta__inner">
        <Reveal className="cta__lead" stagger={0.12}>
          <p className="u-label cta__eyebrow">Ready when you are</p>
          <h2 className="cta__title">
            Zero video out.
            <br />
            Every decision in.
          </h2>
          <p className="cta__sub">
            The moment that matters, caught on the edge. RidewMe turns any
            vehicle into one that watches out for its driver — and proves it did.
          </p>
          <div className="cta__actions">
            <a className="cta__primary" href="/login">
              Login
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </a>
            <a className="cta__secondary" href="mailto:hello@ridewme.io">
              hello@ridewme.io
            </a>
          </div>
        </Reveal>
      </div>

      <footer className="foot">
        <div className="shell foot__row">
          <span className="foot__brand">
            <Logo size={26} />
            RidewMe
          </span>
          <span className="foot__copy">
            © 2026 RidewMe. All rights reserved. · Privacy Policy
          </span>
          <span className="foot__note u-label">Video never leaves the edge</span>
        </div>
      </footer>
    </section>
  )
}
