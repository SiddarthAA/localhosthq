import { useState, type FormEvent } from 'react'
import Reveal from './Reveal'
import './FooterCTA.css'

export default function FooterCTA() {
  const [sent, setSent] = useState(false)

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setSent(true)
  }

  return (
    <section id="contact" className="cta section on-dark" data-nav-theme="dark">
      <span className="cta__ghost" aria-hidden="true">
        RideWMe
      </span>

      <div className="shell cta__inner">
        <Reveal className="cta__lead" stagger={0.1}>
          <p className="u-label cta__eyebrow">For fleet inquiries</p>
          <h2 className="cta__title">
            Zero video out.
            <br />
            Every decision in.
          </h2>
          <p className="cta__sub">
            The moment that matters, caught on the edge. RideWMe turns any
            vehicle into one that watches out for its driver — and proves it
            did. Bring it to your fleet.
          </p>
          <a className="cta__mail" href="mailto:hello@ridewme.io">
            hello@ridewme.io
          </a>
        </Reveal>

        <div className="cta__form-wrap">
          {sent ? (
            <div className="cta__thanks" role="status">
              <span className="cta__thanks-dot" />
              <h3>Thanks — we’ll be in touch.</h3>
              <p>
                A RideWMe engineer will reach out within one business day to set
                up your demo.
              </p>
            </div>
          ) : (
            <form className="cta__form" onSubmit={onSubmit}>
              <div className="field">
                <label htmlFor="f-name">Name</label>
                <input id="f-name" name="name" type="text" autoComplete="name" required />
              </div>
              <div className="field">
                <label htmlFor="f-email">Work email</label>
                <input id="f-email" name="email" type="email" autoComplete="email" required />
              </div>
              <div className="field">
                <label htmlFor="f-fleet">Fleet size</label>
                <select id="f-fleet" name="fleet" defaultValue="">
                  <option value="" disabled>
                    Select a range
                  </option>
                  <option>1–25 vehicles</option>
                  <option>25–100 vehicles</option>
                  <option>100–500 vehicles</option>
                  <option>500+ vehicles</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="f-msg">Message</label>
                <textarea id="f-msg" name="message" rows={3} />
              </div>
              <button className="cta__send" type="submit">
                Send
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <p className="cta__consent">
                By submitting, you agree to our Privacy Policy.
              </p>
            </form>
          )}
        </div>
      </div>

      <footer className="foot">
        <div className="shell foot__row">
          <span className="foot__brand">
            <svg className="foot__eye" viewBox="0 0 32 20" aria-hidden="true">
              <path d="M2 10C5 4 10 1.5 16 1.5S27 4 30 10c-3 6-8 8.5-14 8.5S5 16 2 10Z" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <circle cx="16" cy="10" r="3.4" fill="currentColor" />
            </svg>
            RideWMe
          </span>
          <span className="foot__copy">
            © 2026 RideWMe. All rights reserved. · Privacy Policy
          </span>
          <span className="foot__note u-label">Video never leaves the edge</span>
        </div>
      </footer>
    </section>
  )
}
