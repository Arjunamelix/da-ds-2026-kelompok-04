import { useCallback, useState } from 'react'
import './viz.css'

// Tooltip mengambang yang mengikuti kursor (untuk visual SVG/HTML buatan sendiri).
export function useTooltip() {
  const [tip, setTip] = useState(null)
  const tampil = useCallback((e, konten) => {
    const x = e.clientX ?? e.target.getBoundingClientRect?.().left ?? 0
    const y = e.clientY ?? e.target.getBoundingClientRect?.().top ?? 0
    setTip({ x, y, konten })
  }, [])
  const sembunyi = useCallback(() => setTip(null), [])
  return { tip, tampil, sembunyi }
}

export function Tooltip({ tip }) {
  if (!tip) return null
  const lebar = typeof window !== 'undefined' ? window.innerWidth : 1200
  const kiri = tip.x + 300 > lebar ? tip.x - 290 : tip.x + 14
  return (
    <div className="vz-tooltip" role="tooltip" style={{ left: Math.max(8, kiri), top: tip.y + 14 }}>
      {tip.konten}
    </div>
  )
}
