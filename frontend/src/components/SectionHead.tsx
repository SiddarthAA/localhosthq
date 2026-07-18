import Reveal from './Reveal'
import './SectionHead.css'

type Props = {
  eyebrow?: string
  title: React.ReactNode
  intro?: React.ReactNode
  align?: 'left' | 'center'
  className?: string
}

export default function SectionHead({
  eyebrow,
  title,
  intro,
  align = 'left',
  className = '',
}: Props) {
  return (
    <Reveal className={`sec-head sec-head--${align} ${className}`} stagger={0.1}>
      {eyebrow && (
        <p className="u-label sec-head__eyebrow">
          <span className="sec-head__tick" aria-hidden="true" />
          {eyebrow}
        </p>
      )}
      <h2 className="sec-head__title">{title}</h2>
      {intro && <p className="sec-head__intro">{intro}</p>}
    </Reveal>
  )
}
