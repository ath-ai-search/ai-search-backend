// =====================================================================
// AzureCloud3D.jsx — the Azure page's 3D animation (raw Three.js)
// =====================================================================
// A particle globe = the VM. Five orbiting satellites = the five
// platform services (OpenSearch, PostgreSQL, Redis, Indexer, Search) —
// each glows GREEN when its service answers, RED when it is down.
// The core breathes and shifts azure-blue -> emerald as health improves.
//
// Fast + mobile friendly: ~1600 particles, pixel ratio capped at 2,
// and the animation PAUSES when the browser tab is hidden.
// =====================================================================
import { useRef, useEffect } from 'react'
import * as THREE from 'three'

export default function AzureCloud3D({ services = [] }) {
  const mountRef = useRef(null)
  const servicesRef = useRef(services)
  useEffect(() => { servicesRef.current = services }, [services])

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    let width = mount.clientWidth || 320
    let height = mount.clientHeight || 240

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 100)
    camera.position.z = 4.4

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mount.appendChild(renderer.domElement)

    const group = new THREE.Group()
    scene.add(group)

    // ---- particle globe (the VM) — azure blue, fibonacci spread ----
    const COUNT = 1600
    const pos = new Float32Array(COUNT * 3)
    for (let i = 0; i < COUNT; i++) {
      const phi = Math.acos(1 - 2 * (i + 0.5) / COUNT)
      const theta = Math.PI * (1 + Math.sqrt(5)) * i
      const r = 1.45
      pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i * 3 + 2] = r * Math.cos(phi)
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const mat = new THREE.PointsMaterial({
      color: 0x38bdf8, size: 0.028, transparent: true, opacity: 0.85,
      blending: THREE.AdditiveBlending, depthWrite: false,
    })
    group.add(new THREE.Points(geo, mat))

    // ---- inner wireframe (the machine skeleton) ----
    const wire = new THREE.Mesh(
      new THREE.OctahedronGeometry(0.92, 1),
      new THREE.MeshBasicMaterial({ color: 0x0078d4, wireframe: true, transparent: true, opacity: 0.3 })
    )
    group.add(wire)

    // ---- glowing health core ----
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.4, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending })
    )
    group.add(core)

    // ---- 5 service satellites on a tilted orbit ----
    const SAT_COUNT = 5
    const sats = []
    const orbit = new THREE.Group()
    orbit.rotation.x = Math.PI / 2.4
    for (let i = 0; i < SAT_COUNT; i++) {
      const sat = new THREE.Mesh(
        new THREE.SphereGeometry(0.09, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0x34d399, transparent: true, opacity: 0.95 })
      )
      const halo = new THREE.Mesh(
        new THREE.SphereGeometry(0.16, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0x34d399, transparent: true, opacity: 0.2, blending: THREE.AdditiveBlending })
      )
      sat.add(halo)
      orbit.add(sat)
      sats.push({ mesh: sat, halo, angle: (i / SAT_COUNT) * Math.PI * 2 })
    }
    group.add(orbit)

    // ---- thin orbit trail ----
    const RING = 180
    const rpos = new Float32Array(RING * 3)
    for (let i = 0; i < RING; i++) {
      const a = (i / RING) * Math.PI * 2
      rpos[i * 3] = Math.cos(a) * 2.1
      rpos[i * 3 + 1] = 0
      rpos[i * 3 + 2] = Math.sin(a) * 2.1
    }
    const rgeo = new THREE.BufferGeometry()
    rgeo.setAttribute('position', new THREE.BufferAttribute(rpos, 3))
    const trail = new THREE.Points(rgeo, new THREE.PointsMaterial({
      color: 0x38bdf8, size: 0.02, transparent: true, opacity: 0.4,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }))
    orbit.add(trail)

    const GREEN = new THREE.Color(0x34d399)
    const RED = new THREE.Color(0xf87171)

    let raf = null
    let running = true
    const animate = (t) => {
      if (!running) return
      const svc = servicesRef.current || []
      const upRatio = svc.length ? svc.filter(s => s.up).length / svc.length : 1

      group.rotation.y += 0.0022
      wire.rotation.y -= 0.003
      wire.rotation.x += 0.0014

      // satellites orbit; each shows ITS service's real status
      sats.forEach((s, i) => {
        s.angle += 0.006
        s.mesh.position.set(Math.cos(s.angle) * 2.1, 0, Math.sin(s.angle) * 2.1)
        const ok = svc[i] ? svc[i].up : true
        s.mesh.material.color.copy(ok ? GREEN : RED)
        s.halo.material.color.copy(ok ? GREEN : RED)
        const pulse = 1 + Math.sin(t * 0.004 + i) * (ok ? 0.12 : 0.35)
        s.halo.scale.setScalar(pulse)
      })

      // core: azure blue -> emerald with health, breathing
      const breathe = Math.sin(t * 0.002) * 0.06
      core.scale.setScalar(0.85 + upRatio * 0.5 + breathe)
      core.material.color.setHSL(0.52 - upRatio * 0.14, 0.85, 0.58)
      mat.color.setHSL(0.56 - upRatio * 0.1, 0.85, 0.62)

      group.rotation.x = Math.sin(t * 0.00025) * 0.14
      renderer.render(scene, camera)
      raf = requestAnimationFrame(animate)
    }
    raf = requestAnimationFrame(animate)

    // ⚡ pause the whole animation when the tab is hidden (battery + speed)
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
      // dispose EVERYTHING (geometries + materials) so switching pages
      // many times never leaks WebGL memory
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
