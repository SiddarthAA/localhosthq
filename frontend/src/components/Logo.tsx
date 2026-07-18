type Props = { className?: string; size?: number }

/** RidewMe logomark (raster brand asset in /public). */
export default function Logo({ className, size = 30 }: Props) {
  return (
    <img
      className={className}
      src="/logo.png"
      alt=""
      aria-hidden="true"
      style={{ height: size, width: 'auto' }}
    />
  )
}
