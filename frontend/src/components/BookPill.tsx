import { useEffect, useState } from 'react'
import './BookPill.css'

/** Persistent floating CTA — a single clean Login button (auth wired later). */
export default function BookPill() {
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    const target = document.querySelector('#contact')
    if (!target) return
    const io = new IntersectionObserver(
      ([entry]) => setHidden(entry.isIntersecting),
      { rootMargin: '0px 0px -30% 0px' },
    )
    io.observe(target)
    return () => io.disconnect()
  }, [])

  return (
    <a className={`bookpill${hidden ? ' bookpill--hidden' : ''}`} href="/dashboard">
      <span className="bookpill__dot" aria-hidden="true" />
      Login
    </a>
  )
}
