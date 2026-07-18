import { useEffect, useState, type MouseEvent } from 'react'
import { scrollTo } from '../lib/site'
import Logo from './Logo'
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
    const onScroll = () => setScrolled(window.scrollY > 40)
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
      <div className="nav__bar" aria-hidden="true" />
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
        aria-label="RidewMe — home"
      >
        <Logo className="nav__mark" size={28} />
        RidewMe
      </a>

      <div className="nav__contact">
        <a href="mailto:hello@ridewme.io">hello@ridewme.io</a>
        {/* wire to real auth later — for now routes to the dashboard */}
        <a className="nav__demo" href="/login">
          Login
        </a>
      </div>
    </header>
  )
}
