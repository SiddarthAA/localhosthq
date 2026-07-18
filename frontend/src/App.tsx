import { useSite } from './lib/site'
import Nav from './components/Nav'
import BookPill from './components/BookPill'
import Hero from './components/Hero'
import Statement from './components/Statement'
import Pillars from './components/Pillars'
import Engine from './components/Engine'
import Crash from './components/Crash'
import SmarterSystem from './components/SmarterSystem'
import Reach from './components/Reach'
import FooterCTA from './components/FooterCTA'

export default function App() {
  useSite()
  return (
    <>
      <a className="skip-link" href="#intro">
        Skip to content
      </a>
      <Nav />
      <main>
        <Hero />
        <Statement />
        <Pillars />
        <Engine />
        <Crash />
        <SmarterSystem />
        <Reach />
        <FooterCTA />
      </main>
      <BookPill />
    </>
  )
}
