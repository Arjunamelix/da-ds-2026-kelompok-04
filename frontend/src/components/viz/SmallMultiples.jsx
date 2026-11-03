import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { WARNA, fmtPct, fmtRp, labelTanggal } from './util.js'
import './viz.css'

// Skala sendiri per panel, tetapi rentang minimal 10% dari harga rata-rata, supaya perubahan Rp100
// pada komoditas yang stabil (mis. beras) tidak tampak seperti lonjakan.
function domainMin(data) {
  const v = data.map((d) => d.harga)
  const lo = Math.min(...v)
  const hi = Math.max(...v)
  const tengah = (lo + hi) / 2
  const minRentang = tengah * 0.1
  if (hi - lo >= minRentang) return [lo - (hi - lo) * 0.05, hi + (hi - lo) * 0.05]
  return [tengah - minRentang / 2, tengah + minRentang / 2]
}

// Small multiples: satu panel kecil per komoditas, masing-masing dengan skala sumbu y sendiri,
// supaya pola naik-turun bisa dibandingkan walau tingkat harganya sangat berbeda.
//   titik: [{ komoditas, nama, satuan, sumber, minggu, harga }]
export default function SmallMultiples({ titik, komoditasAktif, onPilih }) {
  const per = new Map()
  for (const t of titik) {
    const k = per.get(t.komoditas) || { komoditas: t.komoditas, nama: t.nama, satuan: t.satuan, sumber: t.sumber, data: [] }
    k.data.push({ minggu: t.minggu, harga: t.harga })
    per.set(t.komoditas, k)
  }
  const panel = [...per.values()].filter((p) => p.data.length >= 2)
  if (!panel.length) return <p className="catatan">Tidak ada data mingguan pada rentang ini.</p>

  return (
    <div className="vz-sm">
      {panel.map((p) => {
        const awal = p.data[0].harga
        const akhir = p.data[p.data.length - 1].harga
        const ubah = awal ? (akhir / awal - 1) * 100 : null
        const aktif = p.komoditas === komoditasAktif
        return (
          <button
            key={p.komoditas}
            type="button"
            className={'vz-sm-kartu' + (aktif ? ' aktif' : '')}
            onClick={() => onPilih?.(p.komoditas)}
            aria-pressed={aktif}
            aria-label={`${p.nama}: ${fmtRp(akhir)} per ${p.satuan}, ${fmtPct(ubah)} sepanjang rentang`}
          >
            <div className="vz-sm-kepala">
              <strong>{p.nama}</strong>
              <span className={ubah > 0 ? 'naik' : ubah < 0 ? 'turun' : ''}>{fmtPct(ubah)}</span>
            </div>
            <div className="vz-sm-kepala">
              <span className="redup">
                {fmtRp(akhir)} / {p.satuan}
              </span>
            </div>
            <div style={{ height: 80 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={p.data} margin={{ top: 6, right: 2, left: 2, bottom: 0 }}>
                  <XAxis dataKey="minggu" hide />
                  <YAxis hide domain={domainMin(p.data)} />
                  <Tooltip
                    formatter={(v) => [fmtRp(v), 'Rata-rata minggu']}
                    labelFormatter={(m) => `Minggu ${labelTanggal(m)}`}
                    contentStyle={{ fontSize: 12 }}
                  />
                  <Line dataKey="harga" stroke={aktif ? WARNA.oranye : WARNA.biru} strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </button>
        )
      })}
    </div>
  )
}
