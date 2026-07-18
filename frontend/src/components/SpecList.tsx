import Reveal from './Reveal'
import './SpecList.css'

export type Spec = { k: string; v: React.ReactNode }

export default function SpecList({ items }: { items: Spec[] }) {
  return (
    <Reveal className="spec" as="ul" stagger={0.06}>
      {items.map((it, i) => (
        <li className="spec__row" key={i}>
          <span className="spec__k u-label">{it.k}</span>
          <span className="spec__v">{it.v}</span>
        </li>
      ))}
    </Reveal>
  )
}
