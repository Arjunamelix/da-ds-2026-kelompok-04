import { useMemo } from 'react'
import { CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { WARNA, fmtAngka, fmtPct, fmtRp, keMs, labelTanggal } from './util.js'
import './viz.css'

const PENDEK = {
  'Tahun Baru Masehi': 'Tahun Baru',
  'Tahun Baru Imlek': 'Imlek',
  'Awal Ramadan': 'Ramadan',
  Idulfitri: 'Idulfitri',
  Iduladha: 'Iduladha',
  Natal: 'Natal',
}
const AMBANG_LONJAKAN = 15 // % perubahan dibanding laporan sebelumnya
const CELAH_HARI = 14

// Deret waktu beranotasi: harga harian + garis hari besar + area tanpa laporan + titik lonjakan terbesar.
//   titik: [{ tanggal, harga, pasar }], hariBesar: [{ tanggal, nama }]
export function anotasi(titik, hariBesar) {
  const data = titik.map((p) => ({ t: keMs(p.tanggal), tanggal: p.tanggal, harga: p.harga, pasar: p.pasar }))
  const celah = []
  const lonjakan = []
  for (let i = 1; i < data.length; i++) {
    const hari = (data[i].t - data[i - 1].t) / 86400000
    if (hari > CELAH_HARI) celah.push({ dari: data[i - 1].t, sampai: data[i].t, hari })
    const pct = (data[i].harga / data[i - 1].harga - 1) * 100
    if (Math.abs(pct) >= AMBANG_LONJAKAN && hari <= CELAH_HARI) lonjakan.push({ ...data[i], pct })
  }
  lonjakan.sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct))
  // Gabungkan hari besar yang berdekatan (<= 10 hari, mis. Idulfitri 2 hari, Natal dan Tahun Baru,
  // Imlek dan awal Ramadan) menjadi satu garis berlabel ganda agar labelnya tidak bertumpuk.
  const hb = []
  for (const h of hariBesar) {
    const t = keMs(h.tanggal)
    const nama = PENDEK[h.nama] || h.nama
    const akhir = hb[hb.length - 1]
    if (akhir && t - akhir.tAkhir <= 10 * 86400000) {
      if (!akhir.nama.includes(nama)) akhir.nama.push(nama)
      akhir.tAkhir = t
      continue
    }
    hb.push({ t, tAkhir: t, nama: [nama], tanggal: h.tanggal })
  }
  return { data, celah, lonjakan: lonjakan.slice(0, 5), hariBesar: hb }
}

export default function DeretBeranotasi({ titik, hariBesar, satuan, tinggi = 340 }) {
  const a = useMemo(() => anotasi(titik, hariBesar), [titik, hariBesar])
  if (a.data.length < 2) return null
  const rentangHari = (a.data[a.data.length - 1].t - a.data[0].t) / 86400000
  const tampilLabelHB = rentangHari <= 420
  const tahun = rentangHari > 300

  return (
    <>
      <div className="grafik" style={{ height: tinggi }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={a.data} margin={{ top: 22, right: 18, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--garis, #e5e7eb)" vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(t) => {
                const s = new Date(t).toISOString().slice(0, 10)
                return tahun ? labelTanggal(s).split(' ').slice(1).join(' ') : labelTanggal(s).split(' ').slice(0, 2).join(' ')
              }}
              minTickGap={48}
              tick={{ fontSize: 11 }}
            />
            <YAxis domain={['auto', 'auto']} tickFormatter={(v) => fmtAngka(v)} width={64} tick={{ fontSize: 11 }} />
            <Tooltip
              labelFormatter={(t) => labelTanggal(new Date(t).toISOString())}
              formatter={(v, _n, item) => [`${fmtRp(v)} / ${satuan} · ${item.payload.pasar} pasar`, 'Harga']}
            />
            {a.celah.map((c) => (
              <ReferenceArea
                key={c.dari}
                x1={c.dari}
                x2={c.sampai}
                fill="#9aa3b2"
                fillOpacity={0.14}
                ifOverflow="extendDomain"
                label={c.hari > 25 ? { value: `tanpa laporan ${Math.round(c.hari)} hari`, position: 'insideTop', fontSize: 10, fill: '#6b7280' } : undefined}
              />
            ))}
            {a.hariBesar.map((h) => (
              <ReferenceLine
                key={h.t}
                x={h.t}
                stroke="#9aa3b2"
                strokeDasharray="2 3"
                label={tampilLabelHB ? { value: h.nama.join(' · '), position: 'top', fontSize: 10, fill: '#6b7280' } : undefined}
              />
            ))}
            <Line dataKey="harga" stroke={WARNA.biru} strokeWidth={2} dot={false} isAnimationActive={false} />
            {a.lonjakan.map((p) => (
              <ReferenceDot
                key={p.t}
                x={p.t}
                y={p.harga}
                r={5}
                fill={p.pct > 0 ? WARNA.oranye : WARNA.biru}
                stroke="#fff"
                strokeWidth={2}
                label={{ value: fmtPct(p.pct, { digit: 0 }), position: p.pct > 0 ? 'top' : 'bottom', fontSize: 11, fill: '#374151' }}
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="catatan">
        Garis putus abu = hari besar{tampilLabelHB ? '' : ' (persempit rentang waktu untuk melihat namanya)'} · area abu = tidak ada laporan lebih dari {CELAH_HARI} hari ·
        titik = {a.lonjakan.length} perubahan terbesar (minimal {AMBANG_LONJAKAN}% dari laporan sebelumnya).
      </p>
    </>
  )
}
