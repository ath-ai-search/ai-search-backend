// =====================================================================
// 🤖 BLU v2 — the bCloud robot, one component used EVERYWHERE
// (login greeter + in-portal assistant). Glossy 3D shell, dark glass
// visor, GLOWING eyes that follow the mouse, moods, ground shadow.
//   mood: 'happy' | 'shy' (password typing 🙈) | 'sad' | 'think'
// =====================================================================
import { useEffect, useRef } from 'react'

export default function BluBot({ mood = 'happy', size = 150, follow = true,
                                 shake = false, legs = true, walking = false,
                                 className = '' }) {
  const ref = useRef(null)

  // 👀 eyes + a gentle 3D head-tilt follow the mouse
  useEffect(() => {
    if (!follow) return
    const onMove = (e) => {
      const el = ref.current
      if (!el) return
      const b = el.getBoundingClientRect()
      const dx = Math.max(-1, Math.min(1, (e.clientX - (b.left + b.width / 2)) / 240))
      const dy = Math.max(-1, Math.min(1, (e.clientY - (b.top + b.height / 2)) / 240))
      el.style.setProperty('--ex', `${(dx * 3.2).toFixed(1)}px`)
      el.style.setProperty('--ey', `${(dy * 2.6).toFixed(1)}px`)
      el.style.setProperty('--rx', `${(dx * 7).toFixed(1)}deg`)
      el.style.setProperty('--ry', `${(-dy * 5).toFixed(1)}deg`)
    }
    window.addEventListener('mousemove', onMove)
    return () => window.removeEventListener('mousemove', onMove)
  }, [follow])

  const glow = '#9b7bff'
  return (
    <div ref={ref} className={`blu-tilt ${shake ? 'blu-shake' : ''} ${className}`}
         style={{ width: size, height: size * 0.94 }}>
      <svg viewBox="0 0 150 141" className="w-full h-full overflow-visible">
        <defs>
          {/* glossy ceramic shell */}
          <radialGradient id="bShell" cx="0.35" cy="0.22" r="1.05">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="55%" stopColor="#f6f3fc" />
            <stop offset="100%" stopColor="#cfc8e8" />
          </radialGradient>
          {/* dark glass visor */}
          <linearGradient id="bVisor" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#241b4d" />
            <stop offset="100%" stopColor="#120c2e" />
          </linearGradient>
          <linearGradient id="bArm" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#6d4aff" />
            <stop offset="100%" stopColor="#5b3bd6" />
          </linearGradient>
          <radialGradient id="bHalo">
            <stop offset="0%" stopColor={glow} stopOpacity="0.9" />
            <stop offset="100%" stopColor={glow} stopOpacity="0" />
          </radialGradient>
          <filter id="bShadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="5" stdDeviation="5"
                          floodColor="#261a5a" floodOpacity="0.22" />
          </filter>
          <filter id="bEyeGlow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="1.7" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* breathing ground shadow — sells the float */}
        <ellipse className={legs ? '' : 'blu-ground'} cx="75" cy={legs ? 139 : 135}
                 rx={legs ? 24 : 30} ry="4" fill="rgba(20,16,43,0.16)" />

        <g className={legs ? '' : 'blu-float'}>
          {/* antenna with glowing tip */}
          <line x1="75" y1="10" x2="75" y2="22" stroke="#5b3bd6" strokeWidth="3"
                strokeLinecap="round" />
          <circle className="blu-halo" cx="75" cy="8" r="9" fill="url(#bHalo)" />
          <circle className="blu-tip" cx="75" cy="8" r="4.2" fill={glow} />

          {/* ear pods */}
          <rect x="17" y="50" width="9" height="22" rx="4.5" fill="url(#bArm)" />
          <rect x="124" y="50" width="9" height="22" rx="4.5" fill="url(#bArm)" />

          {/* arms — from the BODY shoulders, long reach, real mitt hands
              (up at ear height they blended into the ear pods) */}
          <g className="blu-arm-l">
            <line x1="56" y1="103" x2="31" y2="121" stroke="url(#bArm)" strokeWidth="6"
                  strokeLinecap="round" />
            <circle cx="29" cy="123" r="6.5" fill="#6d4aff" stroke="#4a30b8"
                    strokeWidth="1.5" />
          </g>
          <g className="blu-arm-r">
            <line x1="94" y1="103" x2="119" y2="121" stroke="url(#bArm)" strokeWidth="6"
                  strokeLinecap="round" />
            <circle cx="121" cy="123" r="6.5" fill="#6d4aff" stroke="#4a30b8"
                    strokeWidth="1.5" />
          </g>

          {/* neck joint between head and body */}
          <rect x="66" y="90" width="18" height="8" rx="3" fill="#5b3bd6" />

          {/* head — glossy metal shell with rim shading, seam and screws */}
          <rect x="27" y="20" width="96" height="74" rx="26" fill="url(#bShell)"
                stroke="#c7c0e2" strokeWidth="1.5" filter="url(#bShadow)" />
          <ellipse cx="75" cy="87" rx="42" ry="8" fill="rgba(38,26,90,0.10)" />
          <ellipse cx="52" cy="32" rx="19" ry="8" fill="#ffffff" opacity="0.55" />
          <circle cx="109" cy="29" r="3.5" fill="#ffffff" opacity="0.4" />
          <path d="M 33 84 Q 75 92 117 84" stroke="#cbc3e6" strokeWidth="1"
                fill="none" opacity="0.8" />
          <circle cx="36" cy="87" r="1.7" fill="#a89fd0" />
          <circle cx="114" cy="87" r="1.7" fill="#a89fd0" />

          {/* face screen — dark glass with a soft sheen */}
          <rect x="39" y="34" width="72" height="47" rx="16" fill="url(#bVisor)" />
          <path d="M 41 48 Q 75 36 109 48 L 109 40 Q 75 30 41 40 Z"
                fill="#ffffff" opacity="0.06" />

          {/* 👀 eyes — glowing, mood-aware */}
          {mood === 'shy' ? (
            <g>
              <path d="M 53 58 Q 60 51 67 58" stroke={glow} strokeWidth="3"
                    fill="none" strokeLinecap="round" filter="url(#bEyeGlow)" />
              <path d="M 83 58 Q 90 51 97 58" stroke={glow} strokeWidth="3"
                    fill="none" strokeLinecap="round" filter="url(#bEyeGlow)" />
            </g>
          ) : mood === 'sad' ? (
            <g className="blu-eye">
              <circle className="blu-pupil" cx="60" cy="59" r="5" fill={glow}
                      filter="url(#bEyeGlow)" />
              <circle className="blu-pupil" cx="90" cy="59" r="5" fill={glow}
                      filter="url(#bEyeGlow)" />
              <path d="M 52 50 L 66 54" stroke={glow} strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 98 50 L 84 54" stroke={glow} strokeWidth="2.5" strokeLinecap="round" />
            </g>
          ) : mood === 'think' ? (
            <g className="blu-eye">
              <circle className="blu-pupil blu-scan" cx="60" cy="58" r="5.5" fill={glow}
                      filter="url(#bEyeGlow)" />
              <circle className="blu-pupil blu-scan" cx="90" cy="58" r="5.5" fill={glow}
                      filter="url(#bEyeGlow)" />
            </g>
          ) : (
            <g className="blu-eye">
              <circle className="blu-pupil" cx="60" cy="58" r="6.5" fill={glow}
                      filter="url(#bEyeGlow)" />
              <circle className="blu-pupil" cx="90" cy="58" r="6.5" fill={glow}
                      filter="url(#bEyeGlow)" />
              <circle className="blu-pupil" cx="62" cy="56" r="2" fill="#f1ebff" />
              <circle className="blu-pupil" cx="92" cy="56" r="2" fill="#f1ebff" />
            </g>
          )}

          {/* mouth */}
          {mood === 'sad' ? (
            <path d="M 63 75 Q 75 67 87 75" stroke={glow} strokeWidth="2.5"
                  fill="none" strokeLinecap="round" filter="url(#bEyeGlow)" />
          ) : mood === 'think' ? (
            <ellipse cx="75" cy="73" rx="4.5" ry="3" fill="none" stroke={glow}
                     strokeWidth="2.2" filter="url(#bEyeGlow)" />
          ) : (
            <path d="M 62 70 Q 75 79 88 70" stroke={glow} strokeWidth="2.5"
                  fill="none" strokeLinecap="round" filter="url(#bEyeGlow)" />
          )}

          {/* soft cheeks on the glass */}
          <circle cx="49" cy="68" r="4" fill="#ff9d8a" opacity="0.28" />
          <circle cx="101" cy="68" r="4" fill="#ff9d8a" opacity="0.28" />

          {/* 🦵 little stepping legs (walker mode) */}
          {legs && (
            <g>
              <g className={`blu-leg ${walking ? 'blu-step-l' : ''}`}>
                <line x1="66" y1="121" x2="66" y2="132" stroke="url(#bArm)"
                      strokeWidth="6" strokeLinecap="round" />
                <ellipse cx="65" cy="134.5" rx="6.5" ry="3.4" fill="#5b3bd6" />
              </g>
              <g className={`blu-leg ${walking ? 'blu-step-r' : ''}`}>
                <line x1="84" y1="121" x2="84" y2="132" stroke="url(#bArm)"
                      strokeWidth="6" strokeLinecap="round" />
                <ellipse cx="85" cy="134.5" rx="6.5" ry="3.4" fill="#5b3bd6" />
              </g>
            </g>
          )}

          {/* body with a glowing heart-light */}
          <rect x="52" y="96" width="46" height="27" rx="13" fill="url(#bShell)"
                stroke="#c7c0e2" strokeWidth="1.5" filter="url(#bShadow)" />
          <ellipse cx="64" cy="102" rx="8" ry="3.5" fill="#ffffff" opacity="0.5" />
          <circle className="blu-halo" cx="75" cy="109" r="8" fill="url(#bHalo)" />
          <circle className="blu-tip" cx="75" cy="109" r="3.8" fill={glow} />
        </g>
      </svg>
    </div>
  )
}
