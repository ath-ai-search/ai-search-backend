// =====================================================================
// 🌌 REAL 3D (three.js) — the portal's signature visuals
//   <Constellation points={n}/>  every dot = one of THEIR products,
//                                orbiting as a living sphere, mouse parallax
//   <Starfield/>                 slow drifting depth-field for the login page
// Both stop cleanly on unmount and respect reduced-motion.
// =====================================================================
import { useEffect, useRef } from 'react'
import * as THREE from 'three'

const REDUCED = typeof matchMedia !== 'undefined' &&
  matchMedia('(prefers-reduced-motion: reduce)').matches

function useThree(build) {
  const mount = useRef(null)
  useEffect(() => {
    const el = mount.current
    if (!el) return
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    el.appendChild(renderer.domElement)

    const size = () => {
      const w = el.clientWidth, h = el.clientHeight
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    size()
    const ro = new ResizeObserver(size)
    ro.observe(el)

    const cleanupExtra = build({ scene, camera, renderer, el }) || (() => {})
    let raf
    let running = true
    const tick = (t) => {
      if (!running) return
      renderer.render(scene, camera)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    // 🔋 battery + smoothness: stop rendering while the tab is hidden
    const onVis = () => {
      running = !document.hidden
      if (running) raf = requestAnimationFrame(tick)
      else if (raf) cancelAnimationFrame(raf)
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      running = false
      cancelAnimationFrame(raf)
      document.removeEventListener('visibilitychange', onVis)
      ro.disconnect()
      cleanupExtra()
      scene.traverse(obj => {
        if (obj.geometry) obj.geometry.dispose()
        if (obj.material) (Array.isArray(obj.material) ? obj.material
          : [obj.material]).forEach(m => m.dispose())
      })
      renderer.dispose()
      el.removeChild(renderer.domElement)
    }
  }, [])
  return mount
}

export function Constellation({ points = 500 }) {
  const mount = useThree(({ scene, camera, el }) => {
    camera.position.z = 2.3
    const n = Math.max(60, Math.min(3000, points))

    // dots on a fuzzy sphere — THEIR catalogue as a tiny galaxy
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(n * 3)
    const col = new Float32Array(n * 3)
    const mintC = new THREE.Color('#6d4aff'), tealC = new THREE.Color('#4a30b8')
    const sandC = new THREE.Color('#e0821f')
    for (let i = 0; i < n; i++) {
      const r = 1.15 + Math.random() * 0.55
      const th = Math.random() * Math.PI * 2
      const ph = Math.acos(2 * Math.random() - 1)
      pos[i * 3] = r * Math.sin(ph) * Math.cos(th)
      pos[i * 3 + 1] = r * Math.cos(ph) * 0.72
      pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th)
      const c = Math.random() < 0.08 ? sandC : (Math.random() < 0.5 ? mintC : tealC)
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3))
    const cloud = new THREE.Points(geo, new THREE.PointsMaterial({
      size: 0.045, vertexColors: true, transparent: true, opacity: 0.85,
      depthWrite: false,
    }))
    scene.add(cloud)

    // glowing core
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.22, 24, 24),
      new THREE.MeshBasicMaterial({ color: '#6d4aff', transparent: true, opacity: 0.30 }))
    scene.add(core)
    const wire = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.62, 1),
      new THREE.MeshBasicMaterial({ color: '#5b3bd6', wireframe: true,
                                    transparent: true, opacity: 0.22 }))
    scene.add(wire)

    // mouse parallax + slow orbit
    let mx = 0, my = 0
    const onMove = (e) => {
      const b = el.getBoundingClientRect()
      mx = ((e.clientX - b.left) / b.width - 0.5) * 0.6
      my = ((e.clientY - b.top) / b.height - 0.5) * 0.4
    }
    el.addEventListener('mousemove', onMove)
    const spin = () => {
      if (!REDUCED) {
        cloud.rotation.y += 0.0016
        wire.rotation.y -= 0.002
        wire.rotation.x += 0.001
        cloud.rotation.x += (my * 0.4 - cloud.rotation.x) * 0.04
        cloud.rotation.z += (mx * 0.3 - cloud.rotation.z) * 0.04
        core.scale.setScalar(1 + Math.sin(Date.now() / 600) * 0.08)
      }
      spinRaf = requestAnimationFrame(spin)
    }
    let spinRaf = requestAnimationFrame(spin)
    return () => { cancelAnimationFrame(spinRaf); el.removeEventListener('mousemove', onMove) }
  })
  return <div ref={mount} className="w-full h-full" />
}

// 🌍 THE bCLOUD GLOBE — the ADMIN dashboard's signature 3D (the design the
// CEO approved), retinted to the portal's mint family: double counter-
// rotating particle shells, breathing wireframe core, an orbit ring with
// flying comets, distant stars, gentle sway + mouse parallax.
export function SearchGlobe() {
  const mount = useThree(({ scene, camera, el }) => {
    const aspect = Math.max(1, el.clientWidth / Math.max(1, el.clientHeight))
    camera.fov = 55
    camera.position.set(0, 0, 4.6)
    camera.updateProjectionMatrix()

    const world = new THREE.Group()
    // dead-center in its box (brand object, not a side decoration)
    const visHalfH = 4.6 * Math.tan((55 * Math.PI) / 360)
    // everything scales from the panel height -> full round globe, no crop
    const S = (visHalfH * 0.62) / 1.62
    world.scale.setScalar(S)
    scene.add(world)

    const fib = (count, radius) => {
      const pos = new Float32Array(count * 3)
      for (let i = 0; i < count; i++) {
        const phi = Math.acos(1 - 2 * (i + 0.5) / count)
        const theta = Math.PI * (1 + Math.sqrt(5)) * i
        pos[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
        pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
        pos[i * 3 + 2] = radius * Math.cos(phi)
      }
      return pos
    }
    const mkPoints = (positions, color, size, opacity) => {
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      return new THREE.Points(g, new THREE.PointsMaterial({
        color, size, transparent: true, opacity,
        blending: THREE.AdditiveBlending, depthWrite: false,
      }))
    }

    // ---- double shells, counter-rotating — dots painted along the LOGO
    // gradient (blue -> violet -> purple) with WHITE sparkles + orange bits ----
    const mkCloud = (count, radius, palette, size, opacity) => {
      const posArr = fib(count, radius)
      const col = new Float32Array(count * 3)
      for (let i = 0; i < count; i++) {
        const r = Math.random()
        const c = new THREE.Color(
          r < 0.12 ? '#ffffff' : r < 0.15 ? '#ff8a3c'
            : palette[(Math.random() * palette.length) | 0])
        col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
      }
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.BufferAttribute(posArr, 3))
      g.setAttribute('color', new THREE.BufferAttribute(col, 3))
      return new THREE.Points(g, new THREE.PointsMaterial({
        size, vertexColors: true, transparent: true, opacity,
        blending: THREE.AdditiveBlending, depthWrite: false }))
    }
    const outer = mkCloud(2200, 1.62,
      ['#4f7dff', '#7c5cff', '#a05cff', '#8b6bff'], 0.03, 0.95)
    const mid = mkCloud(1200, 1.18,
      ['#5b3bd6', '#6f4fe8', '#4353d9'], 0.024, 0.75)
    world.add(outer, mid)

    // ---- distant stars for depth ----
    const starPos = new Float32Array(600 * 3)
    for (let i = 0; i < 600; i++) {
      const r = 6 + Math.random() * 6
      const a = Math.random() * Math.PI * 2
      const b = Math.acos(2 * Math.random() - 1)
      starPos[i * 3] = r * Math.sin(b) * Math.cos(a)
      starPos[i * 3 + 1] = r * Math.sin(b) * Math.sin(a)
      starPos[i * 3 + 2] = -Math.abs(r * Math.cos(b)) - 1
    }
    const stars = mkPoints(starPos, 0xbfb6ea, 0.022, 0.6)
    scene.add(stars)

    // ---- inner wireframe + breathing glowing core ----
    const wire = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.95, 1),
      new THREE.MeshBasicMaterial({ color: 0x8f7bff, wireframe: true,
                                    transparent: true, opacity: 0.38 }))
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.42, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0xcabfff, transparent: true,
                                    opacity: 0.4, blending: THREE.AdditiveBlending }))
    world.add(wire, core)

    // ---- orbit ring with TWO flying comets (searches racing the globe) ----
    const RING = 220
    const rpos = new Float32Array(RING * 3)
    for (let i = 0; i < RING; i++) {
      const a = (i / RING) * Math.PI * 2
      rpos[i * 3] = Math.cos(a) * 2.15
      rpos[i * 3 + 1] = Math.sin(a * 6) * 0.06
      rpos[i * 3 + 2] = Math.sin(a) * 2.15
    }
    const ring = mkPoints(rpos, 0xb9a8ff, 0.03, 0.6)
    ring.rotation.x = Math.PI / 2.6
    world.add(ring)

    const mkComet = (main, glowC) => {
      const c = new THREE.Mesh(
        new THREE.SphereGeometry(0.055, 12, 12),
        new THREE.MeshBasicMaterial({ color: main, transparent: true, opacity: 0.98 }))
      c.add(new THREE.Mesh(
        new THREE.SphereGeometry(0.13, 12, 12),
        new THREE.MeshBasicMaterial({ color: glowC, transparent: true,
                                      opacity: 0.4, blending: THREE.AdditiveBlending })))
      ring.add(c)
      return c
    }
    const comet1 = mkComet(0xffb26b, 0xff8a3c)     // the logo's orange arrow
    const comet2 = mkComet(0xffffff, 0xb9a8ff)     // a white glowing spark

    let mx = 0, my = 0
    const onMove = (e) => {
      const b = el.getBoundingClientRect()
      mx = ((e.clientX - b.left) / b.width - 0.5)
      my = ((e.clientY - b.top) / b.height - 0.5)
    }
    el.addEventListener('mousemove', onMove)

    let t = 0, cometA = 0
    const spin = () => {
      if (!REDUCED) {
        t += 16
        outer.rotation.y += 0.0022
        outer.rotation.x += 0.0007
        mid.rotation.y -= 0.0031          // counter-rotation = depth
        mid.rotation.x -= 0.0009
        wire.rotation.y -= 0.0035
        wire.rotation.x += 0.0016
        ring.rotation.z += 0.0035
        stars.rotation.y += 0.0003
        cometA += 0.012
        comet1.position.set(Math.cos(cometA) * 2.15,
                            Math.sin(cometA * 6) * 0.06, Math.sin(cometA) * 2.15)
        const a2 = cometA + Math.PI
        comet2.position.set(Math.cos(a2) * 2.15,
                            Math.sin(a2 * 6) * 0.06, Math.sin(a2) * 2.15)
        core.scale.setScalar(1 + Math.sin(t * 0.0022) * 0.08)
        // gentle sway + sideways-only parallax (x-tilt squashes the sphere)
        world.rotation.y = Math.sin(t * 0.0003) * 0.18 + mx * 0.25
        world.rotation.x = Math.sin(t * 0.00022) * 0.04
      }
      raf = requestAnimationFrame(spin)
    }
    let raf = requestAnimationFrame(spin)
    return () => { cancelAnimationFrame(raf); el.removeEventListener('mousemove', onMove) }
  })
  return <div ref={mount} className="w-full h-full" />
}

export function Starfield() {
  const mount = useThree(({ scene, camera }) => {
    camera.position.z = 2
    const n = 900
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 10
      pos[i * 3 + 1] = (Math.random() - 0.5) * 6
      pos[i * 3 + 2] = -Math.random() * 6
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const stars = new THREE.Points(geo, new THREE.PointsMaterial({
      color: '#6d4aff', size: 0.014, transparent: true, opacity: 0.55,
      depthWrite: false,
    }))
    scene.add(stars)
    const drift = () => {
      if (!REDUCED) {
        const p = geo.attributes.position
        for (let i = 0; i < n; i++) {
          p.array[i * 3 + 2] += 0.0035
          if (p.array[i * 3 + 2] > 2) p.array[i * 3 + 2] = -6
        }
        p.needsUpdate = true
      }
      raf = requestAnimationFrame(drift)
    }
    let raf = requestAnimationFrame(drift)
    return () => cancelAnimationFrame(raf)
  })
  return <div ref={mount} className="absolute inset-0" />
}
