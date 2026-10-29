import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client.js'
import { useApp } from '../AppContext.jsx'
import { Galat, KeteranganAcuan, Kosong, Memuat, PilihKecamatan, PilihKomoditas, StatusBadge } from '../components/Umum.jsx'
import { angka, gabungSeri, keMs, labelTick, persen, potongTerakhir, rupiah, tambahHari, tanggalID } from '../lib/format.js'

const BIRU = '#2a78d6'
const ORANYE = '#eb6834'

function bangunGrafik(titik, prediksi) {
  const baris = potongTerakhir(gabungSeri([{ titik }]), 90).map((b) => ({ t: b.t, harga: b.s0 }))
  if (!prediksi.length) return baris
  const dasar = prediksi[0]
  const tDasar = keMs(dasar.tanggal_dasar)
  let b = baris.find((x) => x.t === tDasar)
  if (!b) {
    b = { t: tDasar, harga: dasar.harga_dasar }
    baris.push(b)
  }
  b.prediksi = dasar.harga_dasar // titik awal garis prediksi
  b.rentang = [dasar.harga_dasar, dasar.harga_dasar]
  for (const p of prediksi) {
    baris.push({
      t: keMs(tambahHari(dasar.tanggal_dasar, p.horizon)),
      prediksi: p.harga_prediksi,
      rentang: [p.batas_bawah, p.batas_atas],
    })
  }
  return baris.sort((a, c) => a.t - c.t)
}

function TabelEvaluasi({ evaluasi }) {
  if (!evaluasi?.length) return null
  return (
    <div className="tabel-gulir">
      <table>
        <thead>
          <tr>
            <th>Horizon</th>
            <th className="kanan">Hari uji</th>
            <th className="kanan">MAE model</th>
            <th className="kanan">MAE baseline</th>
            <th className="kanan">RMSE model / baseline</th>
            <th className="kanan">MAPE model / baseline</th>
            <th>Mengalahkan baseline?</th>
          </tr>
        </thead>
        <tbody>
          {evaluasi.map((e) => (
            <tr key={e.horizon}>
              <td>{e.horizon} hari</td>
              <td className="kanan">{e.n_uji}</td>
              <td className="kanan">{angka(e.mae_model)}</td>
              <td className="kanan">{angka(e.mae_baseline)}</td>
              <td className="kanan">
                {angka(e.rmse_model)} / {angka(e.rmse_baseline)}
              </td>
              <td className="kanan">
                {persen(e.mape_model, { tanda: false, digit: 2 })} / {persen(e.mape_baseline, { tanda: false, digit: 2 })}
              </td>
              <td>
                <span className={e.mengalahkan_baseline ? 'tag tag-aqua' : 'tag tag-abu'}>{e.mengalahkan_baseline ? 'Ya' : 'Tidak'}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Prediksi() {
  const { ref, versiModel, menghitung, picuPolling } = useApp()
  const [params, setParams] = useSearchParams()
  const komoditas = params.get('komoditas') || ref.komoditas[0].kode
  const kecamatan = params.get('kecamatan') || ref.kota.kecamatan
  const [data, setData] = useState(null)
  const [tren, setTren] = useState(null)
  const [evStatus, setEvStatus] = useState(null)
  const [galat, setGalat] = useState(null)
  const [pesanLatih, setPesanLatih] = useState('')

  const set = (k, v) => {
    const p = new URLSearchParams(params)
    p.set(k, v)
    setParams(p, { replace: true })
  }

  useEffect(() => {
    let batal = false
    setGalat(null)
    Promise.all([api.prediksi({ komoditas, kecamatan }), api.tren({ komoditas, kecamatan }), api.evaluasi(komoditas)])
      .then(([p, t, e]) => {
        if (batal) return
        setData(p)
        setTren(t)
        setEvStatus(e.status.find((s) => s.komoditas === komoditas) || null)
      })
      .catch((e) => !batal && setGalat(e))
    return () => {
      batal = true
    }
  }, [komoditas, kecamatan, versiModel])

  const latih = async () => {
    setPesanLatih('')
    try {
      await api.latihUlang()
      picuPolling()
    } catch (e) {
      setPesanLatih(e.message)
    }
  }

  const grafik = useMemo(() => (data && tren ? bangunGrafik(tren.seri[0]?.titik ?? [], data.prediksi ?? []) : []), [data, tren])
  const adaPrediksi = data?.prediksi?.length > 0
  const dasar = adaPrediksi ? data.prediksi[0] : null

  return (
    <>
      <div className="bar-judul">
        <h1>Prediksi harga 7 dan 14 hari</h1>
        <button className="tombol" onClick={latih} disabled={menghitung}>
          {menghitung ? 'Sedang menghitung…' : 'Latih ulang'}
        </button>
      </div>
      {pesanLatih && <Galat pesan={pesanLatih} />}
      <div className="filter">
        <PilihKomoditas nilai={komoditas} onChange={(v) => set('komoditas', v)} referensi={ref} />
        <PilihKecamatan nilai={kecamatan} onChange={(v) => set('kecamatan', v)} referensi={ref} />
      </div>
      {data && (
        <KeteranganAcuan
          kecamatan={kecamatan}
          pasarAcuan={data.pasar_acuan}
          sumber={data.sumber}
          pasarSendiri={data.pasar_sendiri}
          kotaNama={ref.kota.kecamatan}
          jumlahPasar={ref.pasar.filter((p) => p.kecamatan === kecamatan).length}
        />
      )}
      <Galat pesan={galat?.message} detail={galat?.detail} />
      {!data && !galat && <Memuat />}
      {data?.tanpa_data && <Kosong>Tidak ada data pasar untuk kecamatan ini di SIMPANG (belum ada pasar terpantau atau datanya kosong).</Kosong>}
      {data?.dilewati && (
        <Kosong>
          <strong>Data belum cukup untuk memodelkan deret ini.</strong>
          <br />
          {data.dilewati.alasan} (tersedia {data.dilewati.n_hari} hari data asli)
        </Kosong>
      )}
      {data && !data.tanpa_data && !adaPrediksi && !data.dilewati && (
        <Kosong>Belum ada prediksi untuk deret ini. Pastikan data sudah diimpor, lalu klik &quot;Latih ulang&quot;.</Kosong>
      )}

      {adaPrediksi && (
        <>
          <div className="panel">
            <h2>
              Harga dan prediksi <small>(Rp)</small>
            </h2>
            <div className="grafik">
              <ResponsiveContainer width="100%" height={360}>
                <ComposedChart data={grafik} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--garis)" />
                  <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={labelTick} minTickGap={40} />
                  <YAxis domain={['auto', 'auto']} tickFormatter={(v) => v.toLocaleString('id-ID')} width={72} />
                  <Tooltip
                    labelFormatter={(t) => tanggalID(new Date(t).toISOString())}
                    formatter={(v, nama) => (Array.isArray(v) ? `${rupiah(v[0])} – ${rupiah(v[1])}` : rupiah(v))}
                  />
                  <Legend />
                  <Area dataKey="rentang" name="Rentang 80%" stroke="none" fill={ORANYE} fillOpacity={0.18} connectNulls isAnimationActive={false} />
                  <Line dataKey="harga" name="Harga aktual" stroke={BIRU} strokeWidth={2} dot={false} connectNulls />
                  <Line dataKey="prediksi" name="Prediksi" stroke={ORANYE} strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3 }} connectNulls />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="catatan">Prediksi dihitung dari data sampai {tanggalID(dasar.tanggal_dasar)}. Area oranye = rentang 80% dari galat uji walk-forward.</p>
          </div>

          <div className="dua-kolom">
            <div className="panel">
              <h2>Hasil prediksi</h2>
              <table>
                <thead>
                  <tr>
                    <th>Horizon</th>
                    <th>Tanggal target</th>
                    <th className="kanan">Prediksi</th>
                    <th className="kanan">Rentang 80%</th>
                    <th className="kanan">vs harga terakhir</th>
                  </tr>
                </thead>
                <tbody>
                  {data.prediksi.map((p) => {
                    const d = (p.harga_prediksi / p.harga_dasar - 1) * 100
                    return (
                      <tr key={p.horizon}>
                        <td>{p.horizon} hari</td>
                        <td>{tanggalID(tambahHari(p.tanggal_dasar, p.horizon))}</td>
                        <td className="kanan">
                          <strong>{rupiah(p.harga_prediksi)}</strong>
                        </td>
                        <td className="kanan">
                          {rupiah(p.batas_bawah)} – {rupiah(p.batas_atas)}
                        </td>
                        <td className={'kanan ' + (d > 0 ? 'naik' : d < 0 ? 'turun' : '')}>{persen(d)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="panel">
              <h2>Status harga</h2>
              {data.status ? (
                <>
                  <p>
                    <StatusBadge status={data.status.status} />
                  </p>
                  <p className="catatan">
                    Perubahan 7 hari yang diprediksi: <strong>{persen(data.status.perubahan_prediksi_pct)}</strong>
                    <br />
                    Ambang komoditas ini: Waspada ≥ {persen(data.status.ambang_waspada_pct, { tanda: false })}, Lonjakan ≥{' '}
                    {persen(data.status.ambang_lonjakan_pct, { tanda: false })}
                  </p>
                </>
              ) : (
                <p className="catatan">Status belum tersedia (data untuk menentukan ambang belum cukup).</p>
              )}
            </div>
          </div>

          <div className="panel">
            <h2>Evaluasi model vs baseline naif</h2>
            <TabelEvaluasi evaluasi={data.evaluasi} />
            <p className="catatan">
              Walk-forward: model dilatih hanya dengan data yang sudah diketahui sebelum hari uji. Baseline naif = harga hari ini berlaku h hari lagi. MAE dan RMSE dalam rupiah.
              Model dianggap berguna bila MAE-nya lebih kecil dari baseline.
            </p>
            {evStatus && (
              <p className="catatan">
                Klasifikasi status komoditas ini (kelas berisiko = Waspada + Lonjakan), {evStatus.n_uji} hari uji gabungan semua deret, {evStatus.n_berisiko} kejadian berisiko:{' '}
                recall {evStatus.recall_berisiko == null ? 'tidak terhitung' : persen(evStatus.recall_berisiko * 100, { tanda: false, digit: 0 })}, presisi{' '}
                {evStatus.presisi_berisiko == null ? 'tidak terhitung' : persen(evStatus.presisi_berisiko * 100, { tanda: false, digit: 0 })}.
              </p>
            )}
          </div>
        </>
      )}
    </>
  )
}