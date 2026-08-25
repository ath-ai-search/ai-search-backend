// =====================================================================
// 🟢 VENUE MARKETPLACE WORDMARK — pure text, no image assets. A bold
// "Venue" in mint followed by " Marketplace" in the default ink, so it
// stays crisp at any size and needs nothing from the bundle.
// =====================================================================

export function BrandMark({ size = 32 }) {
  return (
    <span className="inline-flex items-baseline whitespace-nowrap"
          style={{ fontSize: size * 0.62, lineHeight: 1 }}>
      <span className="font-extrabold text-mint">Venue</span>
      <span className="font-semibold">&nbsp;Marketplace</span>
    </span>
  )
}

export default function BrandLogo({ size = 30, stacked = false, className = '' }) {
  return (
    <span className={`inline-flex items-baseline whitespace-nowrap ${stacked ? 'justify-center' : ''} ${className}`}
          style={{ fontSize: size * 0.62, lineHeight: 1 }}>
      <span className="font-extrabold text-mint">Venue</span>
      <span className="font-semibold">&nbsp;Marketplace</span>
    </span>
  )
}
