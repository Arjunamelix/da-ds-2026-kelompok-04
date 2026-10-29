import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client.js'
import { useApp } from '../AppContext.jsx'
import { Galat, Memuat, PilihKomoditas } from '../components/Umum.jsx'
import { persen, rupiah, tanggalID } from '../lib/format.js'

const BIRU = '#2a78d6'
const ORANYE = '#eb6834'
const AQUA = '#1baf7a'

export default function Perbandingan() {
  const { ref, versiModel } = useApp()
  const [params, setParams] = useSearchParams()
  const komoditas = params.get('komoditas') || ref.komoditas[0].kode
  const [data, setData] = useState(null)
  const [galat, setGalat] = useState(null)

  useEffect(() => {
    let batal = false
    setGalat(null)
    api
      .perbandingan({ komoditas })
      .then((d) => !batal && setData(d))
      .catch((e) => !batal && setGalat(e))
    return () => {
      batal = true
    }
  }, [komoditas, versiModel])

  const ada = data?.kecamatan.filter((k) => k.harga != null) ?? []
  const termahal = ada[0]
  const termurah = ada[ada.length - 1]
  const rata = data?.rata_rata_kota

  return (
    <>
      <div className="bar-judul">
        <h1>Perbandingan antar kecamatan</h1>
        <PilihKomoditas nilai={komoditas} onChange={(v) => setParams({ komoditas: v })} referensi={ref} />
      </div>
      <Galat pesan={galat?.message} detail={galat?.detail} />
      {!data && !galat && <Memuat />}

      {data && (
        <>
          <div className="ringkas">
            <div className="ringkas-item">
              <span>Rata-rata Kota Medan</span>
              <strong>{rata ? rupiah(rata) : '-'}</strong>
              <small>{data.dasar_rata_rata || 'belum ada data'}</small>
            </div>
            <div className="ringkas-item">
              <span>Termahal</span>
              <strong>{termahal ? termahal.kecamatan : '-'}</strong>
              <small>{termahal ? `${rupiah(termahal.harga)} (${persen(termahal.selisih_pct_vs_kota)})` : ''}</small>
            </div>
            <div className="ringkas-item">
              <span>Termurah</span>
              <strong>{termurah ? termurah.kecamatan : '-'}</strong>
              <small>{termurah ? `${rupiah(termurah.harga)} (${persen(termurah.selisih_pct_vs_kota)})` : ''}</small>
            </div>
          </div>

          {ada.length > 0 && (
            <div className="panel">
              <h2>
                Harga {data.nama} <small>(Rp per {data.satuan}, urut dari termahal)</small>
              </h2>
              <div className="grafik">
                <ResponsiveContainer width="100%" height={Math.max(240, ada.length * 26 + 40)}>
                  <BarChart data={ada} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--garis)" horizontal={false} />
                    <XAxis type="number" domain={['dataMin - 1000', 'dataMax + 500']} tickFormatter={(v) => v.toLocaleString('id-ID')} />
                    <YAxis type="category" dataKey="kecamatan" width={120} />
                    <Tooltip formatter={(v) => rupiah(v)} />
                    {rata && <ReferenceLine x={rata} stroke="#6b7280" strokeDasharray="4 3" label={{ value: 'rata-rata kota', position: 'top', fontSize: 11 }} />}
                    <Bar dataKey="harga" name="Harga" radius={[0, 3, 3, 0]}>
                      {ada.map((k) => (
                        <Cell key={k.kecamatan} fill={k.selisih_pct_vs_kota > 0 ? ORANYE : k.selisih_pct_vs_kota < 0 ? AQUA : BIRU} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="catatan">
                <span className="titik" style={{ background: ORANYE }} /> di atas rata-rata kota{' '}
                <span className="titik" style={{ background: AQUA }} /> di bawah rata-rata kota
              </p>
            </div>
          )}

          <div className="panel">
            <h2>Rincian 21 kecamatan</h2>
            <div className="tabel-gulir">
              <table>
                <thead>
                  <tr>
                    <th>Kecamatan</th>
                    <th>Dasar harga</th>
                    <th className="kanan">Harga</th>
                    <th className="kanan">Selisih vs rata-rata kota</th>
                    <th>Per tanggal</th>
                  </tr>
                </thead>
                <tbody>
                  {data.kecamatan.map((k) => (
                    <tr key={k.kecamatan} className={k.tanpa_data ? 'redup' : ''}>
                      <td>
                        {k.kecamatan}
                        {k === termahal && <span className="tag tag-oranye">termahal</span>}
                        {k === termurah && ada.length > 1 && <span className="tag tag-aqua">termurah</span>}
                      </td>
                      <td>{k.pasar_acuan ? (k.pasar_acuan === ref.kota.nama_pasar ? `rata-rata ${k.jumlah_pasar} pasar` : k.pasar_sendiri ? k.pasar_acuan : <em>mengacu pada {k.pasar_acuan}</em>) : '-'}</td>
                      <td className="kanan">{k.harga != null ? rupiah(k.harga) : <em>{k.tanpa_data && !k.pasar_acuan ? k.keterangan : 'belum ada data'}</em>}</td>
                      <td className={'kanan ' + (k.selisih_pct_vs_kota > 0 ? 'naik' : k.selisih_pct_vs_kota < 0 ? 'turun' : '')}>
                        {k.selisih_pct_vs_kota != null ? persen(k.selisih_pct_vs_kota) : '-'}
                      </td>
                      <td>{k.tanggal_data ? tanggalID(k.tanggal_data) : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="catatan">
              Harga kecamatan adalah rata-rata harga pasar yang terpantau di kecamatan itu; selisih dihitung terhadap median harga semua pasar se-Kota Medan.
              Kecamatan tanpa pasar di sumber data tetap ditampilkan sebagai &quot;tidak ada data&quot; dan tidak diisi tebakan.
            </p>
          </div>
        </>
      )}
    </>
  )
}