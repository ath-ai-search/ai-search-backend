// =====================================================================
// 🟣 THE REAL bCLOUD LOGO — the official PNG (transparent background,
// 310×184) shipped inside the bundle. Always shown DOWNSCALED from the
// source, so it stays pixel-crisp everywhere. In dark mode it sits on a
// soft white chip so the dark wordmark never disappears.
// =====================================================================
import logoPng from './assets/bcloud-logo.png'

export function BrandMark({ size = 32 }) {
  return (
    <img src={logoPng} alt="bCloud AI" className="brand-img"
         style={{ height: size, width: size * (310 / 184), maxWidth: 'none',
                  display: 'block' }} />
  )
}

export default function BrandLogo({ size = 30, stacked = false, className = '' }) {
  return (
    <span className={`inline-flex items-center ${stacked ? 'justify-center' : ''} ${className}`}>
      <img src={logoPng} alt="bCloud AI" className="brand-img"
           style={{ height: size * (stacked ? 2.3 : 1.4),
                    width: size * (stacked ? 2.3 : 1.4) * (310 / 184),
                    maxWidth: 'none', display: 'block' }} />
    </span>
  )
}
