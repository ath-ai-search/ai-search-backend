// =====================================================================
// Sphere3D.jsx — the Overview's 3D index globe  (Azure edition v2)
// =====================================================================
// Double counter-rotating particle shells + inner wireframe core +
// a distant starfield + an orbit ring with a flying COMET. The core
// breathes and the whole globe shifts azure-blue -> emerald as the
// indexing progress grows.
// Fast: capped pixel ratio, pauses when the tab is hidden, full
// GPU-memory disposal on unmount.
// =====================================================================
import { useRef, useEffect } from 'react'
import * as THREE from 'three'

export default function Sphere3D({ progress = 0, active = false }) {
  const mountRef = useRef(null)
  const progressRef = useRef(progress)
  const activeRef = useRef(active)
  useEffect(() => { progressRef.current = progress }, [progress])
  useEffect(() => { activeRef.current = active }, [active])

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    let width = mount.clientWidth || 320
    let height = mount.clientHeight || 260

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 100)
    camera.position.z = 4.2

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mount.appendChild(renderer.domElement)

    const group = new THREE.Group()
    scene.add(group)

    const fib = (count, radius) => {
      const pos = new Float32Array(count * 3)
      for (let i = 0; i < count; i++) {
        const phi = Math.acos(1 - 2 * (i + 0.5) / count)
        const theta = Math.PI * (1 + Math.sqrt(5)) * i
        pos[i * 3]     = radius * Math.sin(phi) * Math.cos(theta)
        pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
        pos[i * 3 + 2] = radius * Math.cos(phi)
      }
      return pos
    }
    const points = (positions, color, size, opacity) => {
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      return new THREE.Points(g, new THREE.PointsMaterial({
        color, size, transparent: true, opacity,
        blending: THREE.AdditiveBlending, depthWrite: false,
      }))
    }

    // ---- outer shell (azure) + mid shell (violet), counter-rotating ----
    const outer = points(fib(2200, 1.62), 0x5f95ff, 0.028, 0.85)
    const mid   = points(fib(1200, 1.18), 0x9d7bff, 0.024, 0.65)
    group.add(outer, mid)

    // ---- distant starfield (slow, calm depth) ----
    const starPos = new Float32Array(700 * 3)
    for (let i = 0; i < 700; i++) {
      const r = 6 + Math.random() * 6
      const a = Math.random() * Math.PI * 2
      const b = Math.acos(2 * Math.random() - 1)
      starPos[i * 3]     = r * Math.sin(b) * Math.cos(a)
      starPos[i * 3 + 1] = r * Math.sin(b) * Math.sin(a)
      starPos[i * 3 + 2] = r * Math.cos(b)
    }
    const stars = points(starPos, 0x8fa3c8, 0.02, 0.5)
    scene.add(stars)

    // ---- inner wireframe + glowing core ----
    const wire = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.95, 1),
      new THREE.MeshBasicMaterial({ color: 0x7c5cff, wireframe: true, transparent: true, opacity: 0.3 })
    )
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.42, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0x4c9aff, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending })
    )
    group.add(wire, core)

    // ---- orbit ring + a flying comet with a glow ----
    const RING = 220
    const rpos = new Float32Array(RING * 3)
    for (let i = 0; i < RING; i++) {
      const a = (i / RING) * Math.PI * 2
      rpos[i * 3]     = Math.cos(a) * 2.15
      rpos[i * 3 + 1] = Math.sin(a * 6) * 0.06
      rpos[i * 3 + 2] = Math.sin(a) * 2.15
    }
    const ring = points(rpos, 0x3ecfad, 0.03, 0.5)
    ring.rotation.x = Math.PI / 2.6
    group.add(ring)

    const comet = new THREE.Mesh(
      new THREE.SphereGeometry(0.055, 12, 12),
      new THREE.MeshBasicMaterial({ color: 0x7fe9cd, transparent: true, opacity: 0.95 })
    )
    const cometGlow = new THREE.Mesh(
      new THREE.SphereGeometry(0.13, 12, 12),
      new THREE.MeshBasicMaterial({ color: 0x3ecfad, transparent: true, opacity: 0.25, blending: THREE.AdditiveBlending })
    )
    comet.add(cometGlow)
    ring.add(comet)

    let raf = null
    let running = true
    let cometA = 0
    const animate = (t) => {
      if (!running) return
      const p = Math.max(0, Math.min(1, progressRef.current / 100))
      // 🚀 EXCITEMENT MODE while indexing runs: everything spins faster,
      // the comet races, the core beats harder - the globe is 'eating' data
      const boost = activeRef.current ? 3.2 : 1

      outer.rotation.y += 0.0022 * boost
      outer.rotation.x += 0.0007 * boost
      mid.rotation.y   -= 0.0031 * boost  // counter-rotation = feeling of depth
      mid.rotation.x   -= 0.0009 * boost
      wire.rotation.y  -= 0.0035 * boost
      wire.rotation.x  += 0.0016 * boost
      ring.rotation.z  += 0.0035 * boost
      stars.rotation.y += 0.0003 * boost

      cometA += 0.012 * boost
      comet.position.set(Math.cos(cometA) * 2.15, Math.sin(cometA * 6) * 0.06, Math.sin(cometA) * 2.15)

      const beat = activeRef.current ? 0.0065 : 0.0022      // faster heartbeat
      const amp  = activeRef.current ? 0.14 : 0.05           // stronger beat
      const pulse = Math.sin(t * beat) * amp
      core.scale.setScalar(0.55 + p * 1.05 + pulse)
      outer.material.opacity = activeRef.current ? 1.0 : 0.85
      cometGlow.material.opacity = activeRef.current ? 0.5 : 0.25
      outer.material.color.setHSL(0.62 - p * 0.23, 0.85, 0.64)
      mid.material.color.setHSL(0.72 - p * 0.3, 0.75, 0.7)
      core.material.color.setHSL(0.6 - p * 0.22, 0.9, 0.62)

      group.rotation.y = Math.sin(t * 0.0003) * 0.18
      group.rotation.x = Math.sin(t * 0.00022) * 0.08
      renderer.render(scene, camera)
      raf = requestAnimationFrame(animate)
    }
    raf = requestAnimationFrame(animate)

    // pause when the browser tab is hidden — battery + smoothness
    const onVisibility = () => {
      running = !document.hidden
      if (running) raf = requestAnimationFrame(animate)
      else if (raf) cancelAnimationFrame(raf)
    }
    document.addEventListener('visibilitychange', onVisibility)

    const onResize = () => {
      width = mount.clientWidth; height = mount.clientHeight
      if (!width || !height) return
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height)
    }
    window.addEventListener('resize', onResize)

    return () => {
      running = false
      if (raf) cancelAnimationFrame(raf)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('resize', onResize)
      scene.traverse(obj => {
        if (obj.geometry) obj.geometry.dispose()
        if (obj.material) (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach(m => m.dispose())
      })
      renderer.dispose()
      if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement)
    }
  }, [])

  return <div ref={mountRef} className="w-full h-full" />
}
