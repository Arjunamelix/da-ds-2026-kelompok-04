import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.js'
import { useApp } from '../../AppContext.jsx'
import { useMuat } from './useMuat.js'
import { WARNA, domainBerlabel, fmtAngka, fmtPct, fmtRp, labelTanggal } from './util.js'
import './viz.css'

// Empat kartu KPI level Kota Medan, masing-masing dengan pembanding, ditambah grafik batang divergen
// perubahan harga 7 hari per komoditas. Sumber: GET /api/analitik/kpi (data warehouse).

function formatNilai(k, v) {
  if (v == null) return '-'
  if (k.satuan === '%') return fmtPct(v, { tanda: k.kode === 'perubahan_7h' })
  return fmtAngka(v, Number.isInteger(v) ? 0 : 1)
}

function KartuKPI({ k }) {
  const ada = k.nilai != null && k.pembanding != null
  const selisih = ada ? k.nilai - k.pembanding : null
  const buruk = selisih != null && selisih !== 0 && (k.naik_buruk ? selisih > 0 : selisih < 0)
  const baik = selisih != null && selisih !== 0 && !buruk
  const arah = selisih > 0 ? '▲' : selisih < 0 ? '▼' : '■'
  const besarSelisih =
    selisih == null ? '-' : k.satuan === '%' ? `${fmtAngka(Math.abs(selisih), 1)} poin` : fmtAngka(Math.abs(selisih), Number.isInteger(selisih) ? 0 : 1)
  return (
    <div className="vz-kpi-kartu">
      <span className="vz-kpi-judul">{k.judul}</span>
      <span className="vz-kpi-nilai">
        {formatNilai(k, k.nilai)}
        {k.satuan !== '%' && <small>{k.satuan}</small>}
        {k.target != null && <small>/ {k.target}</small>}
      </span>
      <span className={'vz-kpi-banding ' + (buruk ? 'naik' : baik ? 'turun' : '')}>
        {arah} {besarSelisih} vs {k.label_pembanding} ({formatNilai(k, k.pembanding)})
      </span>
      <span className="vz-kpi-ket">{k.keterangan}</span>
    </div>
  )
}

export default function PanelKPI({ tampilKartu = true, tampilGrafik = true }) {
  const { versiModel } = useApp()
  const { data, galat } = useMuat(() => api.analitik.kpi(), `kpi|${versiModel}`)
  if (galat) return tampilKartu ? <p className="catatan">KPI belum bisa dimuat: {galat.message}</p> : null
  if (!data) return tampilKartu ? <div className="vz-kpi" aria-busy="true" /> : null

  const batang = data.komoditas
    .filter((k) => k.perubahan_7h_pct != null)
    .map((k) => ({ ...k, nilai: Math.round(k.perubahan_7h_pct * 10) / 10 }))
    .sort((a, b) => b.nilai - a.nilai)

  return (
    <section aria-label="Indikator utama Kota Medan">
      {tampilKartu && (
        <>
          <p className="catatan" style={{ marginTop: 0 }}>
            Indikator utama Kota Medan per {labelTanggal(data.tanggal)} · dihitung dari data warehouse ·{' '}
            <Link to="/analisis">analisis lengkap</Link>
          </p>
          <div className="vz-kpi">
            {data.kpi.map((k) => (
              <KartuKPI key={k.kode} k={k} />
            ))}
          </div>
        </>
      )}
      {tampilGrafik && batang.length > 0 && (
        <div className="panel">
          <h2>
            Perubahan harga 7 hari per komoditas <small>(median harga pasar se-Kota Medan)</small>
          </h2>
          <div className="grafik" style={{ height: Math.max(220, batang.length * 28 + 30) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={batang} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--garis, #e5e7eb)" horizontal={false} />
                <XAxis type="number" domain={domainBerlabel()} tickFormatter={(v) => fmtPct(v, { digit: 0 })} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="nama" width={140} tick={{ fontSize: 12 }} />
                <ReferenceLine x={0} stroke="#6b7280" />
                <Tooltip
                  formatter={(v, _n, item) => [
                    `${fmtPct(v)} (${fmtRp(item.payload.harga_7h)} → ${fmtRp(item.payload.harga)} / ${item.payload.satuan})`,
                    'Perubahan 7 hari',
                  ]}
                />
                <Bar dataKey="nilai" radius={4} isAnimationActive={false}>
                  {batang.map((k) => (
                    <Cell key={k.komoditas} fill={k.nilai > 0 ? WARNA.oranye : k.nilai < 0 ? WARNA.biru : WARNA.abu} />
                  ))}
                  <LabelList dataKey="nilai" position="right" formatter={(v) => fmtPct(v)} style={{ fontSize: 11, fill: '#374151' }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="catatan">
            <span className="titik" style={{ background: WARNA.oranye }} /> naik · <span className="titik" style={{ background: WARNA.biru }} /> turun ·
            dibandingkan dengan harga terakhir 7 sampai 14 hari sebelumnya. Garam halus dan susu bubuk tidak tampil karena tidak punya angka level kota.
          </p>
        </div>
      )}
    </section>
  )
}
