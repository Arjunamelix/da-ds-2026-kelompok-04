import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client.js'
import { useApp } from '../AppContext.jsx'
import { Galat, Kosong, Memuat, PilihKomoditas } from '../components/Umum.jsx'
import { gabungSeri, labelTick, potongTerakhir, rupiah, tanggalID } from '../lib/format.js'

const WARNA = ['#2a78d6', '#eb6834', '#1baf7a'] // maksimal 3 seri (Project.md 6.6)
const RENTANG = [
  { nilai: 30, label: '30 hari' },
  { nilai: 90, label: '90 hari' },
  { nilai: 180, label: '6 bulan' },
  { nilai: 365, label: '1 tahun' },
  { nilai: 0, label: 'Semua' },
]

export default function Tren() {
  const { ref, versiModel } = useApp()
  const [params, setParams] = useSearchParams()
  const komoditas = params.get('komoditas') || ref.komoditas[0].kode
  const dipilih = params.getAll('kecamatan')
  const kecamatan = dipilih.length ? dipilih : [ref.kota.kecamatan]
  const [rentang, setRentang] = useState(90)
  const [data, setData] = useState(null)
  const [galat, setGalat] = useState(null)

  const set = (k, v) => {
    const p = new URLSearchParams(params)
    p.set(k, v)
    setParams(p, { replace: true })
  }
  const toggleKec = (k) => {
    const sekarang = new Set(kecamatan)
    if (sekarang.has(k)) sekarang.delete(k)
    else if (sekarang.size < 3) sekarang.add(k)
    if (sekarang.size === 0) return
    const p = new URLSearchParams(params)
    p.delete('kecamatan')
    sekarang.forEach((x) => p.append('kecamatan', x))
    setParams(p, { replace: true })
  }

  useEffect(() => {
    let batal = false
    setGalat(null)
    api
      .tren({ komoditas, kecamatan })
      .then((d) => !batal && setData(d))
      .catch((e) => !batal && setGalat(e))
    return () => {
      batal = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [komoditas, kecamatan.join('|'), versiModel])

  const baris = useMemo(() => (data ? potongTerakhir(gabungSeri(data.seri), rentang) : []), [data, rentang])
  const adaData = data && data.seri.some((s) => s.titik.length > 0)

  return (
    <>
      <div className="bar-judul">
        <h1>Tren harga</h1>
      </div>
      <div className="filter">
        <PilihKomoditas nilai={komoditas} onChange={(v) => set('komoditas', v)} referensi={ref} />
        <div className="field">
          <span>Rentang waktu</span>
          <div className="segmen" role="group" aria-label="Rentang waktu">
            {RENTANG.map((r) => (
              <button key={r.nilai} className={rentang === r.nilai ? 'aktif' : ''} onClick={() => setRentang(r.nilai)}>
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <fieldset className="kecamatan-pilih">
        <legend>Kecamatan (maksimal 3 per grafik)</legend>
        {[ref.kota.kecamatan, ...ref.kecamatan].map((k) => {
          const aktif = kecamatan.includes(k)
          return (
            <label key={k} className={aktif ? 'cek aktif' : 'cek'}>
              <input type="checkbox" checked={aktif} disabled={!aktif && kecamatan.length >= 3} onChange={() => toggleKec(k)} />
              {k}
            </label>
          )
        })}
      </fieldset>

      <Galat pesan={galat?.message} detail={galat?.detail} />
      {!data && !galat && <Memuat />}
      {data && !adaData && <Kosong>Belum ada data untuk komoditas dan kecamatan ini.</Kosong>}
      {adaData && (
        <div className="panel">
          <h2>
            {data.nama} <small>(Rp per {data.satuan})</small>
          </h2>
          <div className="grafik">
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={baris} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--garis)" />
                <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={labelTick} minTickGap={40} />
                <YAxis domain={['auto', 'auto']} tickFormatter={(v) => v.toLocaleString('id-ID')} width={72} />
                <Tooltip labelFormatter={(t) => tanggalID(new Date(t).toISOString())} formatter={(v) => rupiah(v)} />
                {data.seri.length > 1 && <Legend />}
                {data.seri.map((s, i) => (
                  <Line
                    key={s.kecamatan}
                    type="monotone"
                    dataKey={'s' + i}
                    name={s.kecamatan === ref.kota.kecamatan ? 'KOTA MEDAN' : s.kecamatan}
                    stroke={WARNA[i]}
                    dot={false}
                    strokeWidth={2}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <ul className="catatan daftar-acuan">
            {data.seri.map((s) => (
              <li key={s.kecamatan}>
                {s.kecamatan}:{' '}
                {s.tanpa_data
                  ? 'belum ada data'
                  : s.kecamatan === ref.kota.kecamatan
                    ? `median harga semua pasar (${s.sumber})`
                    : s.pasar_acuan === ref.kota.nama_pasar
                      ? `rata-rata harga pasar di kecamatan (${s.sumber})`
                      : s.pasar_sendiri
                        ? `${s.pasar_acuan} (${s.sumber})`
                        : `mengacu pada ${s.pasar_acuan} (${s.sumber})`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}