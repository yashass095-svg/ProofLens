interface IntroOverlayProps {
  onExplore: () => void
}

export default function IntroOverlay({ onExplore }: IntroOverlayProps) {
  return (
    <section className="intro-overlay" aria-label="ProofLens AI introduction">
      <div className="intro-grid" aria-hidden="true" />
      <div className="intro-scanline" aria-hidden="true" />
      <div className="intro-particles" aria-hidden="true">
        <i /><i /><i /><i /><i /><i />
      </div>
      <button className="intro-skip" type="button" onClick={onExplore}>Skip intro <span aria-hidden="true">↗</span></button>
      <div className="intro-content">
        <div className="intro-brand">
          <span className="intro-brand-mark" aria-hidden="true"><i /></span>
          <span>PROOFLENS <b>AI</b></span>
        </div>
        <p className="intro-kicker"><span /> DOCUMENT INTELLIGENCE, WITH RECEIPTS</p>
        <h1>Don't Just Trust AI.<br /><span>Verify It.</span></h1>
        <p className="intro-subtitle">Evidence-backed answers. Transparent verification.</p>
        <button className="intro-enter" type="button" onClick={onExplore}>
          Explore ProofLens AI <span aria-hidden="true">→</span>
        </button>
        <div className="intro-foot"><span>01</span><i /> SOURCE-LED ANALYSIS</div>
      </div>
      <div className="intro-corner-note" aria-hidden="true">EVIDENCE / TRACE / REVIEW</div>
    </section>
  )
}