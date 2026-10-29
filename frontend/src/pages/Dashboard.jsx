import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client.js'
import { useApp } from '../AppContext.jsx'
import { Galat, KeteranganAcuan, Kosong, Memuat, PilihKecamatan, StatusBadge } from '../components/Umum.jsx'
import { persen, rupiah, tanggalID } from '../lib/format.js'

function Kartu({ k, kecamatan }) {
  const naik = k.perubahan_7h_pct > 0
  const turun = k.perubahan_7h_pct < 0
  return (
    <Link className="kartu" to={`/tren?komoditas=${k.komoditas}&kecamatan=${encodeURIComponent(kecamatan)}`}>
      <div className="kartu-kepala">
        <h3>{k.nama}</h3>
        <StatusBadge status={k.status} />
      </div>
      <div className="kartu-harga">
        {rupiah(k.harga_terakhir)}
        <small> / {k.satuan}</small>
      </div>
      <div className="kartu-baris">
        <span className="redup">Per {tanggalID(k.tanggal_terakhir)}</span>
      </div>
      <div className="kartu-baris">
        <span>Perubahan 7 hari</span>
        {k.perubahan_7h_pct == null ? (
          <span className="redup">-</span>
        ) : (
          <span className={naik ? 'naik' : turun ? 'turun' : ''}>
            {naik ? '▲' : turun ? '▼' : '■'} {rupiah(Math.abs(k.perubahan_7h_abs))} ({persen(k.perubahan_7h_pct)})
          </span>
        )}
      </div>
      <div className="kartu-baris">
        <span>Prediksi 7 hari</span>
        {k.prediksi_7h != null ? (
          <span>
            <strong>{rupiah(k.prediksi_7h)}</strong>
            <small className="redup">
              {' '}
              ({rupiah(k.prediksi_7h_bawah)} – {rupiah(k.prediksi_7h_atas)})
            </small>
          </span>
        ) : (
          <span className="redup">
            {k.keterangan === 'data_belum_cukup' ? 'data belum cukup' : 'model belum dilatih'}
          </span>
        )}
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const { ref, versiModel } = useApp()
  const [params, setParams] = useSearchParams()
  const kecamatan = params.get('kecamatan') || ref.kota.kecamatan
  const [data, setData] = useState(null)
  const [galat, setGalat] = useState(null)

  useEffect(() => {
    let batal = false
    setGalat(null)
    api
      .ringkasan(kecamatan)
      .then((d) => !batal && setData(d))
      .catch((e) => !batal && setGalat(e))
    return () => {
      batal = true
    }
  }, [kecamatan, versiModel])

  const ubah = (k) => setParams(k === ref.kota.kecamatan ? {} : { kecamatan: k })

  return (
    <>
      <div className="bar-judul">
        <h1>Ringkasan harga</h1>
        <PilihKecamatan nilai={kecamatan} onChange={ubah} referensi={ref} />
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
      {data && !data.tanpa_data && data.kartu.length === 0 && (
        <Kosong>
          Belum ada data harga untuk deret ini. Impor CSV lewat halaman <Link to="/kelola">Kelola Data</Link>.
        </Kosong>
      )}
      <div className="grid-kartu">{data?.kartu?.map((k) => <Kartu key={k.komoditas} k={k} kecamatan={kecamatan} />)}</div>
      <p className="catatan">
        Status memakai perubahan harga 7 hari ke depan yang diprediksi model, dibandingkan dengan ambang tiap komoditas.
        Klik kartu untuk melihat tren.
      </p>
    </>
  )
}