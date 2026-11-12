import { Tooltip, useTooltip } from './Tooltip.jsx'
import { WARNA, fmtAngka, fmtRp, labelBulan, labelBulanPendek } from './util.js'
import './viz.css'

// Box plot sebaran harga antarpasar per bulan.
// Kotak = kuartil 1 sampai 3, garis tengah = median, kumis = persentil 5 sampai 95.
//   data: [{ tahun_bulan, n, pasar, p05, q1, median, q3, p95, minimum, maksimum }]
function skalaRapi(lo, hi, n = 5) {
  const rentang = hi - lo || 1
  const langkahKasar = rentang / n
  const pangkat = 10 ** Math.floor(Math.log10(langkahKasar))
  const langkah = [1, 2, 2.5, 5, 10].map((m) => m * pangkat).find((s) => s >= langkahKasar)
  const awal = Math.floor(lo / langkah) * langkah
  const akhir = Math.ceil(hi / langkah) * langkah
  const tik = []
  for (let v = awal; v <= akhir + 1e-9; v += langkah) tik.push(v)
  return { awal, akhir, tik }
}

export default function BoxPlot({ data, satuan, onKlikBulan, bulanAktif }) {
  const { tip, tampil, sembunyi } = useTooltip()
  if (!data?.length) return null

  const kiri = 64
  const kanan = 12
  const atas = 12
  const bawah = 34
  const lebarKotak = 26
  const jarak = 36
  const W = kiri + kanan + data.length * jarak
  const H = 280
  const lo = Math.min(...data.map((d) => d.p05))
  const hi = Math.max(...data.map((d) => d.p95))
  const { awal, akhir, tik } = skalaRapi(lo, hi)
  const y = (v) => atas + (H - atas - bawah) * (1 - (v - awal) / (akhir - awal || 1))
  const tiapLabel = data.length > 18 ? 3 : data.length > 9 ? 2 : 1

  return (
    <div className="vz-gulir">
      <svg className="vz-svg" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: Math.min(W, 560) }} role="img"
        aria-label={`Box plot harga antarpasar per bulan, ${data.length} bulan`}>
        {tik.map((v) => (
          <g key={v}>
            <line x1={kiri} x2={W - kanan} y1={y(v)} y2={y(v)} stroke="#e5e7eb" />
            <text x={kiri - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fill="#6b7280">
              {fmtAngka(v)}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const cx = kiri + jarak * i + jarak / 2
          const aktif = bulanAktif === d.tahun_bulan
          const isi = (
            <>
              <strong>{labelBulan(d.tahun_bulan)}</strong>
              Median {fmtRp(d.median)} / {satuan}
              <br />
              Kuartil 1–3: {fmtRp(d.q1)} – {fmtRp(d.q3)}
              <br />
              Persentil 5–95: {fmtRp(d.p05)} – {fmtRp(d.p95)}
              <br />
              Termurah–termahal: {fmtRp(d.minimum)} – {fmtRp(d.maksimum)}
              <br />
              {fmtAngka(d.n)} laporan dari {d.pasar} pasar
              {onKlikBulan && (
                <>
                  <br />
                  <em>Klik untuk menelusuri bulan ini</em>
                </>
              )}
            </>
          )
          return (
            <g
              key={d.tahun_bulan}
              className={onKlikBulan ? 'vz-klik' : ''}
              tabIndex={onKlikBulan ? 0 : undefined}
              role={onKlikBulan ? 'button' : undefined}
              aria-label={`${labelBulan(d.tahun_bulan)}: median ${fmtRp(d.median)}`}
              onMouseMove={(e) => tampil(e, isi)}
              onMouseLeave={sembunyi}
              onClick={onKlikBulan ? () => onKlikBulan(d.tahun_bulan) : undefined}
              onKeyDown={(e) => onKlikBulan && (e.key === 'Enter' || e.key === ' ') && onKlikBulan(d.tahun_bulan)}
            >
              <rect x={cx - jarak / 2} y={atas} width={jarak} height={H - atas - bawah} fill={aktif ? '#eef4fc' : 'transparent'} />
              <line x1={cx} x2={cx} y1={y(d.p95)} y2={y(d.q3)} stroke="#6b7280" strokeWidth="1.5" />
              <line x1={cx} x2={cx} y1={y(d.q1)} y2={y(d.p05)} stroke="#6b7280" strokeWidth="1.5" />
              <line x1={cx - 6} x2={cx + 6} y1={y(d.p95)} y2={y(d.p95)} stroke="#6b7280" strokeWidth="1.5" />
              <line x1={cx - 6} x2={cx + 6} y1={y(d.p05)} y2={y(d.p05)} stroke="#6b7280" strokeWidth="1.5" />
              <rect
                x={cx - lebarKotak / 2}
                y={y(d.q3)}
                width={lebarKotak}
                height={Math.max(2, y(d.q1) - y(d.q3))}
                rx="4"
                fill={WARNA.biru}
                fillOpacity={aktif ? 0.55 : 0.28}
                stroke={WARNA.biru}
                strokeWidth="1.5"
              />
              <line x1={cx - lebarKotak / 2} x2={cx + lebarKotak / 2} y1={y(d.median)} y2={y(d.median)} stroke="#1f2937" strokeWidth="2.5" />
              {i % tiapLabel === 0 && (
                <text x={cx} y={H - bawah + 18} textAnchor="middle" fontSize="11" fill="#6b7280">
                  {labelBulanPendek(d.tahun_bulan)}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  )
}
