import { Tooltip, useTooltip } from './Tooltip.jsx'
import { fmtAngka, fmtPct, fmtRp, teksDiAtas, warnaDivergen } from './util.js'
import './viz.css'

// Treemap hierarki Kota Medan > kecamatan > pasar.
// Luas kotak = banyak laporan harga (kelengkapan data); warna = rata-rata selisih terhadap median kota.
// Klik kecamatan untuk turun ke pasar-pasarnya (drill-down); remah roti untuk naik lagi.

// Algoritme squarified (Bruls dkk.): susun kotak agar rasio sisinya mendekati persegi.
function squarify(items, x, y, w, h) {
  const total = items.reduce((s, d) => s + d.nilai, 0)
  if (!total) return []
  const skala = (w * h) / total
  const sisa = items.map((d) => ({ ...d, luas: d.nilai * skala })).sort((a, b) => b.luas - a.luas)
  const hasil = []
  let baris = []
  let kotak = { x, y, w, h }

  const terburuk = (b, sisi) => {
    const s = b.reduce((t, d) => t + d.luas, 0)
    const mx = Math.max(...b.map((d) => d.luas))
    const mn = Math.min(...b.map((d) => d.luas))
    return Math.max((sisi * sisi * mx) / (s * s), (s * s) / (sisi * sisi * mn))
  }
  const letakkan = (b) => {
    const s = b.reduce((t, d) => t + d.luas, 0)
    if (kotak.w >= kotak.h) {
      const lebar = s / kotak.h
      let yy = kotak.y
      for (const d of b) {
        const tinggi = d.luas / lebar
        hasil.push({ ...d, x: kotak.x, y: yy, w: lebar, h: tinggi })
        yy += tinggi
      }
      kotak = { x: kotak.x + lebar, y: kotak.y, w: kotak.w - lebar, h: kotak.h }
    } else {
      const tinggi = s / kotak.w
      let xx = kotak.x
      for (const d of b) {
        const lebar = d.luas / tinggi
        hasil.push({ ...d, x: xx, y: kotak.y, w: lebar, h: tinggi })
        xx += lebar
      }
      kotak = { x: kotak.x, y: kotak.y + tinggi, w: kotak.w, h: kotak.h - tinggi }
    }
  }
  for (const d of sisa) {
    const sisi = Math.min(kotak.w, kotak.h)
    if (!baris.length || terburuk([...baris, d], sisi) <= terburuk(baris, sisi)) {
      baris.push(d)
    } else {
      letakkan(baris)
      baris = [d]
    }
  }
  if (baris.length) letakkan(baris)
  return hasil
}

// pasar: [{ kecamatan, nama_pasar, laporan, rata_harga, selisih_pct }]
export function kelompokkanKecamatan(pasar) {
  const m = new Map()
  for (const p of pasar) {
    const k = m.get(p.kecamatan) || { kecamatan: p.kecamatan, laporan: 0, bobot: 0, pasar: 0 }
    k.laporan += p.laporan
    k.bobot += (p.selisih_pct ?? 0) * p.laporan
    k.pasar += 1
    m.set(p.kecamatan, k)
  }
  return [...m.values()].map((k) => ({ ...k, selisih_pct: k.laporan ? k.bobot / k.laporan : null }))
}

export default function TreemapWilayah({ pasar, kecamatan, onPilihKecamatan, satuKomoditas, jumlahKecamatanSemua = 21 }) {
  const { tip, tampil, sembunyi } = useTooltip()
  const W = 640
  const H = 360

  const level = kecamatan ? 'pasar' : 'kecamatan'
  const item =
    level === 'kecamatan'
      ? kelompokkanKecamatan(pasar).map((k) => ({ kunci: k.kecamatan, label: k.kecamatan, nilai: k.laporan, selisih: k.selisih_pct, info: k }))
      : pasar
          .filter((p) => p.kecamatan === kecamatan)
          .map((p) => ({ kunci: p.nama_pasar, label: p.nama_pasar, nilai: p.laporan, selisih: p.selisih_pct, info: p }))
  const kotak = squarify(item.filter((d) => d.nilai > 0), 0, 0, W, H)
  const kecamatanBerdata = new Set(pasar.map((p) => p.kecamatan)).size

  return (
    <div>
      <nav className="vz-remah" aria-label="Tingkat wilayah">
        {kecamatan ? (
          <>
            <button type="button" onClick={() => onPilihKecamatan('')}>
              Kota Medan
            </button>
            <span aria-hidden="true">›</span>
            <strong>{kecamatan}</strong>
          </>
        ) : (
          <strong>Kota Medan</strong>
        )}
        <span className="redup">
          · {level === 'kecamatan' ? `${kecamatanBerdata} dari ${jumlahKecamatanSemua} kecamatan punya pasar terpantau; klik kecamatan untuk melihat pasarnya` : `${item.length} pasar`}
        </span>
      </nav>
      {kotak.length === 0 ? (
        <p className="catatan">Tidak ada laporan harga untuk pilihan ini.</p>
      ) : (
        <svg className="vz-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Treemap ${level} menurut banyak laporan`}>
          {kotak.map((d) => {
            const latar = warnaDivergen(d.selisih, 10)
            const teks = teksDiAtas(latar)
            const muatLabel = d.w > 70 && d.h > 30
            const isi = (
              <>
                <strong>{d.label}</strong>
                {level === 'kecamatan' && `${d.info.pasar} pasar · `}
                {fmtAngka(d.nilai)} laporan harga
                <br />
                Rata-rata selisih terhadap median kota: {fmtPct(d.selisih)}
                {level === 'pasar' && satuKomoditas && (
                  <>
                    <br />
                    Rata-rata harga: {fmtRp(d.info.rata_harga)}
                  </>
                )}
                {level === 'pasar' && !satuKomoditas && (
                  <>
                    <br />
                    {d.info.komoditas} komoditas dilaporkan
                  </>
                )}
                {level === 'kecamatan' && (
                  <>
                    <br />
                    <em>Klik untuk melihat pasar</em>
                  </>
                )}
              </>
            )
            const bisaKlik = level === 'kecamatan'
            return (
              <g
                key={d.kunci}
                className={bisaKlik ? 'vz-klik' : ''}
                tabIndex={bisaKlik ? 0 : undefined}
                role={bisaKlik ? 'button' : undefined}
                aria-label={`${d.label}: ${fmtAngka(d.nilai)} laporan, selisih ${fmtPct(d.selisih)}`}
                onMouseMove={(e) => tampil(e, isi)}
                onMouseLeave={sembunyi}
                onClick={bisaKlik ? () => onPilihKecamatan(d.kunci) : undefined}
                onKeyDown={(e) => bisaKlik && (e.key === 'Enter' || e.key === ' ') && onPilihKecamatan(d.kunci)}
              >
                <rect x={d.x + 1} y={d.y + 1} width={Math.max(0, d.w - 2)} height={Math.max(0, d.h - 2)} rx="4" fill={latar} />
                {muatLabel && (
                  <>
                    <text x={d.x + 8} y={d.y + 18} fontSize="12" fontWeight="600" fill={teks}>
                      {d.label.length * 7 > d.w - 12 ? d.label.slice(0, Math.max(3, Math.floor((d.w - 12) / 7))) + '…' : d.label}
                    </text>
                    {d.h > 44 && (
                      <text x={d.x + 8} y={d.y + 34} fontSize="11" fill={teks}>
                        {fmtPct(d.selisih)}
                      </text>
                    )}
                  </>
                )}
              </g>
            )
          })}
        </svg>
      )}
    </div>
  )
}
