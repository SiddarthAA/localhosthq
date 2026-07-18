import './EtherealShadow.css'

type Props = {
  className?: string
  /** 'teal' | 'red' | 'mixed' — accent bias of the drifting glow */
  tone?: 'teal' | 'red' | 'mixed'
}

/** Animated atmospheric background — drifting glow blobs + grain.
    Inspired by 21st.dev "ethereal shadow". Purely decorative. */
export default function EtherealShadow({ className = '', tone = 'teal' }: Props) {
  return (
    <div className={`ether ether--${tone} ${className}`} aria-hidden="true">
      <div className="ether__blob ether__blob--a" />
      <div className="ether__blob ether__blob--b" />
      <div className="ether__blob ether__blob--c" />
      <div className="ether__grain" />
    </div>
  )
}
