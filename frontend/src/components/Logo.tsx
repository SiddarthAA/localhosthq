type Props = { className?: string; size?: number }

/** RidewMe logomark — an eye watching a road that converges to its pupil. */
export default function Logo({ className, size = 30 }: Props) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="2.4" y="2.4" width="35.2" height="35.2" rx="11.5" strokeOpacity="0.55" />
      {/* upper eyelid */}
      <path d="M11 18.2 Q20 11.4 29 18.2" />
      {/* road converging to the pupil */}
      <path d="M10.5 30.5 L17.6 21.2" />
      <path d="M29.5 30.5 L22.4 21.2" />
      {/* lane dash */}
      <path d="M20 30.5 L20 27.5" strokeOpacity="0.6" />
      {/* pupil / vanishing point */}
      <circle cx="20" cy="19.4" r="2.3" fill="currentColor" stroke="none" />
    </svg>
  )
}
