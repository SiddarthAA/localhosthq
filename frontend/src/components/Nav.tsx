import { useEffect, useState, type MouseEvent } from 'react'
import { scrollTo } from '../lib/site'
import './Nav.css'

const LINKS = [
  { label: 'The Engine', href: '#engine' },
  { label: 'How It Works', href: '#how' },
  { label: 'Why It Wins', href: '#why' },
  { label: 'Deploy', href: '#contact' },
]

export default function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () =>
      setScrolled(window.scrollY > window.innerHeight * 0.55)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const go = (e: MouseEvent, href: string) => {
    e.preventDefault()
    scrollTo(href)
  }

  return (
    <header className={`nav${scrolled ? ' nav--scrolled' : ''}`}>
      <nav className="nav__links" aria-label="Primary">
        {LINKS.map((l) => (
          <a key={l.href} href={l.href} onClick={(e) => go(e, l.href)}>
            {l.label}
          </a>
        ))}
      </nav>

      <a
        className="nav__wordmark"
        href="#top"
        onClick={(e) => go(e, '#top')}
        aria-label="RideWMe — home"
      >
        <svg className="nav__eye" viewBox="0 0 32 20" aria-hidden="true">
          <path
            d="M2 10C5 4 10 1.5 16 1.5S27 4 30 10c-3 6-8 8.5-14 8.5S5 16 2 10Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <circle cx="16" cy="10" r="3.4" fill="currentColor" />
        </svg>
        RideWMe
      </a>

      <div className="nav__contact">
        <a href="mailto:hello@ridewme.io">hello@ridewme.io</a>
        <a
          className="nav__demo"
          href="#contact"
          onClick={(e) => go(e, '#contact')}
        >
          Book a demo
        </a>
      </div>
    </header>
  )
}
