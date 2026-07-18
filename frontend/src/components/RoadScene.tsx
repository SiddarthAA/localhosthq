import './RoadScene.css'

/** Hero centerpiece: a live "dashcam" view of the road with the RidewMe HUD
    tracking the vehicle ahead — the co-pilot watching the drive. */
export default function RoadScene() {
  return (
    <div className="scene" aria-hidden="true">
      <div className="scene__chip scene__chip--ear u-label">EAR 0.31</div>
      <div className="scene__chip scene__chip--perclos u-label">PERCLOS 4%</div>

      <div className="scene__frame">
        <div className="scene__sky" />
        <div className="scene__road" />

        <svg className="scene__lanes" viewBox="0 0 300 225" preserveAspectRatio="none">
          <line className="scene__edge" x1="20" y1="225" x2="146" y2="103" />
          <line className="scene__edge" x1="280" y1="225" x2="154" y2="103" />
          <line className="scene__center" x1="150" y1="225" x2="150" y2="105" />
        </svg>

        <div className="scene__wash" />
        <div className="scene__horizon" />

        <div className="scene__vehicle">
          <span className="scene__cab" />
          <span className="scene__tail scene__tail--l" />
          <span className="scene__tail scene__tail--r" />
        </div>

        <div className="scene__hud">
          <span className="scene__bracket scene__bracket--tl" />
          <span className="scene__bracket scene__bracket--tr" />
          <span className="scene__bracket scene__bracket--bl" />
          <span className="scene__bracket scene__bracket--br" />
          <span className="scene__scan" />
        </div>

        <span className="scene__hud-label u-label">Tracking · driver + road</span>
        <span className="scene__readout u-label">Gap 42 m · 104 km/h</span>

        <div className="scene__scanlines" />
        <div className="scene__vignette" />
      </div>

      <div className="scene__status">
        <span className="scene__dot" />
        <span className="u-label">Awake · baseline locked</span>
      </div>
    </div>
  )
}
