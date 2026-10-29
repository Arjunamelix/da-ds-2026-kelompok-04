import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { useApp } from '../AppContext.jsx'
import { Galat, Kosong, Memuat } from '../components/Umum.jsx'
import { angka, rupiah, tanggalID } from '../lib/format.js'

function hariIni() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const kunciStr = (k) => [k.kecamatan, k.nama_pasar, k.komoditas, k.sumber].join('|')

function HasilTulis({ hasil, kunci, judul }) {
  const { hitung, ref } = useApp()
  const [sesudah, setSesudah] = useState(null)
  const [galat, setGalat] = useState('')

  const selesai = hitung && hitung.versi_model >= hasil.versi_data && hitung.status_hitung === 'idle'

  useEffect(() => {
    if (!selesai || !kunci.length) return
    let batal = false
    api
      .prediksiSesudah(kunci)
      .then((r) => !batal && setSesudah(r.prediksi))
      .catch((e) => !batal && setGalat(e.message))
    return () => {
      batal = true
    }
  }, [selesai, kunci])

  const sebelumMap = Object.fromEntries((hasil.prediksi_sebelum || []).map((p) => [kunciStr(p), p.prediksi_7h]))
  const sesudahMap = Object.fromEntries((sesudah || []).map((p) => [kunciStr(p), p.prediksi_7h]))
  const namaKom = (kode) => ref.komoditas.find((k) => k.kode === kode)?.nama ?? kode

  return (
    <div className="kotak kotak-ok" role="status">
      <strong>{judul}</strong>
      <span className="redup"> · versi data {hasil.versi_data}</span>
      {hasil.peringatan?.length > 0 && (
        <ul className="peringatan">
          {hasil.peringatan.map((p, i) => (
            <li key={i}>⚠ {p}</li>
          ))}
        </ul>
      )}
      {kunci.length > 0 && (
        <div className="sebelum-sesudah">
          <h4>Perubahan prediksi 7 hari</h4>
          {!selesai && hitung?.status_hitung !== 'error' && (
            <p className="catatan">
              <span className="spinner" aria-hidden="true" /> Sedang menghitung ulang… hasilnya muncul di sini setelah selesai.
            </p>
          )}
          {hitung?.status_hitung === 'error' && <p className="catatan">Pelatihan ulang gagal: {hitung.pesan_hitung}</p>}
          {galat && <p className="catatan">{galat}</p>}
          {selesai && sesudah && (
            <div className="tabel-gulir">
              <table>
                <thead>
                  <tr>
                    <th>Komoditas</th>
                    <th>Deret</th>
                    <th className="kanan">Sebelum</th>
                    <th className="kanan">Sesudah</th>
                    <th className="kanan">Selisih</th>
                  </tr>
                </thead>
                <tbody>
                  {kunci.map((k) => {
                    const a = sebelumMap[kunciStr(k)]
                    const b = sesudahMap[kunciStr(k)]
                    const d = a != null && b != null ? b - a : null
                    return (
                      <tr key={kunciStr(k)}>
                        <td>{namaKom(k.komoditas)}</td>
                        <td>{k.kecamatan === ref.kota.kecamatan ? 'Kota Medan' : k.nama_pasar}</td>
                        <td className="kanan">{a != null ? rupiah(a) : <em>belum ada</em>}</td>
                        <td className="kanan">{b != null ? rupiah(b) : <em>belum ada</em>}</td>
                        <td className={'kanan ' + (d > 0 ? 'naik' : d < 0 ? 'turun' : '')}>{d == null ? '-' : (d > 0 ? '+' : d < 0 ? '-' : '') + rupiah(Math.abs(d))}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function FormHarga({ awal, onSubmit, label, onBatal }) {
  const { ref } = useApp()
  const kota = ref.kota
  const [f, setF] = useState(
    awal || {
      tanggal: hariIni(),
      kecamatan: kota.kecamatan,
      nama_pasar: kota.nama_pasar,
      komoditas: ref.komoditas[0].kode,
      harga: '',
      sumber: ref.sumber.find((s) => s.kode === 'PIHPS') ? 'PIHPS' : ref.sumber[0].kode,
    },
  )
  const [galat, setGalat] = useState(null)
  const [kirim, setKirim] = useState(false)

  const pasarOpsi = f.kecamatan === kota.kecamatan ? [kota.nama_pasar] : ref.pasar.filter((p) => p.kecamatan === f.kecamatan).map((p) => p.nama)
  const kom = ref.komoditas.find((k) => k.kode === f.komoditas)

  const ubahKec = (kecamatan) => {
    const opsi = kecamatan === kota.kecamatan ? [kota.nama_pasar] : ref.pasar.filter((p) => p.kecamatan === kecamatan).map((p) => p.nama)
    setF({ ...f, kecamatan, nama_pasar: opsi[0] || '' })
  }

  const submit = async (e) => {
    e.preventDefault()
    setGalat(null)
    if (!/^\d+$/.test(String(f.harga))) {
      setGalat({ message: 'Harga harus angka bulat tanpa titik, koma, atau "Rp".', detail: [] })
      return
    }
    setKirim(true)
    try {
      await onSubmit({ ...f, harga: Number(f.harga) })
    } catch (err) {
      setGalat(err)
    } finally {
      setKirim(false)
    }
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <div className="form-grid">
        <label className="field">
          <span>Tanggal</span>
          <input type="date" value={f.tanggal} onChange={(e) => setF({ ...f, tanggal: e.target.value })} required />
        </label>
        <label className="field">
          <span>Kecamatan</span>
          <select value={f.kecamatan} onChange={(e) => ubahKec(e.target.value)}>
            <option value={kota.kecamatan}>{kota.kecamatan} (harga level kota)</option>
            {ref.kecamatan.map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Nama pasar</span>
          <select value={f.nama_pasar} onChange={(e) => setF({ ...f, nama_pasar: e.target.value })} disabled={pasarOpsi.length <= 1} required>
            {pasarOpsi.length === 0 && <option value="">(belum ada pasar terdaftar)</option>}
            {pasarOpsi.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
          {pasarOpsi.length === 0 && <small className="galat-kecil">Kecamatan ini belum punya pasar di config/referensi.json.</small>}
        </label>
        <label className="field">
          <span>Komoditas</span>
          <select value={f.komoditas} onChange={(e) => setF({ ...f, komoditas: e.target.value })}>
            {ref.komoditas.map((k) => (
              <option key={k.kode} value={k.kode}>
                {k.nama}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Harga (Rp per {kom?.satuan})</span>
          <input
            inputMode="numeric"
            pattern="[0-9]*"
            value={f.harga}
            onChange={(e) => setF({ ...f, harga: e.target.value.trim() })}
            placeholder="mis. 52000"
            required
          />
          {kom && (
            <small className="redup">
              Batas wajar {angka(kom.min)} – {angka(kom.max)}
            </small>
          )}
        </label>
        <label className="field">
          <span>Sumber</span>
          <select value={f.sumber} onChange={(e) => setF({ ...f, sumber: e.target.value })}>
            {ref.sumber.map((s) => (
              <option key={s.kode} value={s.kode}>
                {s.kode}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Galat pesan={galat?.message} detail={galat?.detail} />
      <div className="aksi">
        <button className="tombol tombol-utama" type="submit" disabled={kirim || pasarOpsi.length === 0}>
          {kirim ? 'Menyimpan…' : label}
        </button>
        {onBatal && (
          <button className="tombol" type="button" onClick={onBatal}>
            Batal
          </button>
        )}
      </div>
    </form>
  )
}

const kunciDariInput = (d) => ({ kecamatan: d.kecamatan, nama_pasar: d.nama_pasar, komoditas: d.komoditas, sumber: d.sumber })

function TabTambah() {
  const { picuPolling } = useApp()
  const [hasil, setHasil] = useState(null)
  const simpan = async (d) => {
    const r = await api.tambahHarga(d)
    setHasil({ r, kunci: [kunciDariInput(d)], judul: 'Data tersimpan' })
    picuPolling()
  }
  return (
    <>
      <FormHarga onSubmit={simpan} label="Simpan data" key={hasil ? hasil.r.versi_data : 0} />
      {hasil && <HasilTulis hasil={hasil.r} kunci={hasil.kunci} judul={hasil.judul} />}
    </>
  )
}


function TabDaftar() {
  const { ref, picuPolling } = useApp()
  const [filter, setFilter] = useState({ komoditas: '', kecamatan: '', sumber: '', dari: '', sampai: '' })
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [galat, setGalat] = useState(null)
  const [edit, setEdit] = useState(null)
  const [hasil, setHasil] = useState(null)
  const perHalaman = 25

  const muat = useCallback(() => {
    setGalat(null)
    api
      .listHarga({ ...filter, page, per_page: perHalaman })
      .then(setData)
      .catch(setGalat)
  }, [filter, page])

  useEffect(muat, [muat])

  const ubahFilter = (k, v) => {
    setPage(1)
    setFilter({ ...filter, [k]: v })
  }

  const simpanEdit = async (d) => {
    const r = await api.ubahHarga(edit.id, d)
    setHasil({ r, kunci: [kunciDariInput(d), kunciDariInput(edit)].filter((k, i, a) => a.findIndex((x) => kunciStr(x) === kunciStr(k)) === i), judul: 'Data diubah' })
    setEdit(null)
    picuPolling()
    muat()
  }

  const hapus = async (row) => {
    if (!window.confirm(`Hapus data ${row.komoditas} ${row.nama_pasar} ${tanggalID(row.tanggal)} (${rupiah(row.harga)})?`)) return
    try {
      const r = await api.hapusHarga(row.id)
      setHasil({ r, kunci: [kunciDariInput(row)], judul: 'Data dihapus' })
      picuPolling()
      muat()
    } catch (e) {
      setGalat(e)
    }
  }

  const total = data?.total ?? 0
  const halamanMaks = Math.max(1, Math.ceil(total / perHalaman))

  return (
    <>
      {edit && (
        <div className="panel panel-edit">
          <h3>Ubah data #{edit.id}</h3>
          <FormHarga
            awal={{ tanggal: edit.tanggal, kecamatan: edit.kecamatan, nama_pasar: edit.nama_pasar, komoditas: edit.komoditas, harga: String(edit.harga), sumber: edit.sumber }}
            onSubmit={simpanEdit}
            label="Simpan perubahan"
            onBatal={() => setEdit(null)}
          />
        </div>
      )}
      {hasil && <HasilTulis hasil={hasil.r} kunci={hasil.kunci} judul={hasil.judul} />}

      <div className="filter">
        <label className="field">
          <span>Komoditas</span>
          <select value={filter.komoditas} onChange={(e) => ubahFilter('komoditas', e.target.value)}>
            <option value="">Semua</option>
            {ref.komoditas.map((k) => (
              <option key={k.kode} value={k.kode}>
                {k.nama}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Kecamatan</span>
          <select value={filter.kecamatan} onChange={(e) => ubahFilter('kecamatan', e.target.value)}>
            <option value="">Semua</option>
            <option value={ref.kota.kecamatan}>{ref.kota.kecamatan}</option>
            {ref.kecamatan.map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Sumber</span>
          <select value={filter.sumber} onChange={(e) => ubahFilter('sumber', e.target.value)}>
            <option value="">Semua</option>
            {ref.sumber.map((s) => (
              <option key={s.kode}>{s.kode}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Dari</span>
          <input type="date" value={filter.dari} onChange={(e) => ubahFilter('dari', e.target.value)} />
        </label>
        <label className="field">
          <span>Sampai</span>
          <input type="date" value={filter.sampai} onChange={(e) => ubahFilter('sampai', e.target.value)} />
        </label>
      </div>

      <Galat pesan={galat?.message} detail={galat?.detail} />
      {!data && !galat && <Memuat />}
      {data && data.data.length === 0 && <Kosong>Tidak ada data yang cocok dengan filter.</Kosong>}
      {data && data.data.length > 0 && (
        <>
          <div className="tabel-gulir">
            <table>
              <thead>
                <tr>
                  <th>Tanggal</th>
                  <th>Kecamatan</th>
                  <th>Pasar</th>
                  <th>Komoditas</th>
                  <th className="kanan">Harga</th>
                  <th>Sumber</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.data.map((r) => (
                  <tr key={r.id}>
                    <td>{tanggalID(r.tanggal)}</td>
                    <td>{r.kecamatan}</td>
                    <td>{r.nama_pasar}</td>
                    <td>{r.komoditas}</td>
                    <td className="kanan">
                      {rupiah(r.harga)}
                      <small className="redup"> /{r.satuan}</small>
                    </td>
                    <td>
                      {r.sumber}
                      {r.interpolasi === 1 && <span className="tag tag-abu">interpolasi</span>}
                    </td>
                    <td className="aksi-baris">
                      <button className="tombol-kecil" onClick={() => setEdit(r)}>
                        Ubah
                      </button>
                      <button className="tombol-kecil tombol-bahaya" onClick={() => hapus(r)}>
                        Hapus
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="halaman">
            <button className="tombol" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              ‹ Sebelumnya
            </button>
            <span>
              Halaman {page} dari {halamanMaks} · {angka(total)} baris
            </span>
            <button className="tombol" disabled={page >= halamanMaks} onClick={() => setPage(page + 1)}>
              Berikutnya ›
            </button>
          </div>
        </>
      )}
    </>
  )
}

function TabImporEkspor() {
  const { ref, picuPolling } = useApp()
  const [file, setFile] = useState(null)
  const [kirim, setKirim] = useState(false)
  const [hasil, setHasil] = useState(null)
  const [galat, setGalat] = useState(null)
  const [fe, setFe] = useState({ komoditas: '', kecamatan: '', sumber: '', dari: '', sampai: '' })

  const impor = async () => {
    if (!file) return
    setKirim(true)
    setGalat(null)
    setHasil(null)
    try {
      const r = await api.imporHarga(file)
      setHasil(r)
      if (r.disisipkan > 0) picuPolling()
    } catch (e) {
      setGalat(e)
    } finally {
      setKirim(false)
    }
  }

  return (
    <>
      <div className="dua-kolom">
        <div className="panel">
          <h2>Impor CSV</h2>
          <p className="catatan">
            Format 6 kolom: <code>tanggal,kecamatan,nama_pasar,komoditas,harga,sumber</code>. Baris yang sudah ada dilewati, jadi mengunggah file yang sama dua kali tidak membuat duplikat.
            Baris tidak valid dilaporkan dengan nomor barisnya; baris valid tetap masuk.
          </p>
          <p>
            <a href={api.urlTemplate()}>Unduh template CSV</a>
          </p>
          <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <div className="aksi">
            <button className="tombol tombol-utama" onClick={impor} disabled={!file || kirim}>
              {kirim ? 'Mengunggah…' : 'Impor'}
            </button>
          </div>
        </div>

        <div className="panel">
          <h2>Ekspor CSV</h2>
          <p className="catatan">Untuk cadangan atau analisis di luar aplikasi. Kosongkan filter untuk mengekspor semua data.</p>
          <div className="form-grid kecil">
            <label className="field">
              <span>Komoditas</span>
              <select value={fe.komoditas} onChange={(e) => setFe({ ...fe, komoditas: e.target.value })}>
                <option value="">Semua</option>
                {ref.komoditas.map((k) => (
                  <option key={k.kode} value={k.kode}>
                    {k.nama}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Sumber</span>
              <select value={fe.sumber} onChange={(e) => setFe({ ...fe, sumber: e.target.value })}>
                <option value="">Semua</option>
                {ref.sumber.map((s) => (
                  <option key={s.kode}>{s.kode}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Dari</span>
              <input type="date" value={fe.dari} onChange={(e) => setFe({ ...fe, dari: e.target.value })} />
            </label>
            <label className="field">
              <span>Sampai</span>
              <input type="date" value={fe.sampai} onChange={(e) => setFe({ ...fe, sampai: e.target.value })} />
            </label>
          </div>
          <div className="aksi">
            <a className="tombol tombol-utama" href={api.urlEkspor(fe)} download>
              Unduh CSV
            </a>
          </div>
        </div>
      </div>

      <Galat pesan={galat?.message} detail={galat?.detail} />
      {hasil && (
        <div className="kotak kotak-ok">
          <strong>Impor selesai</strong>
          <div className="ringkas">
            <div className="ringkas-item">
              <span>Baris dibaca</span>
              <strong>{angka(hasil.total_baris)}</strong>
            </div>
            <div className="ringkas-item">
              <span>Baru disimpan</span>
              <strong>{angka(hasil.disisipkan)}</strong>
            </div>
            <div className="ringkas-item">
              <span>Dilewati (sudah ada)</span>
              <strong>{angka(hasil.dilewati_sudah_ada)}</strong>
            </div>
            <div className="ringkas-item">
              <span>Tidak valid</span>
              <strong className={hasil.tidak_valid ? 'naik' : ''}>{angka(hasil.tidak_valid)}</strong>
            </div>
          </div>
          {hasil.disisipkan > 0 && (
            <p className="catatan">
              Data berubah (versi {hasil.versi_data}); model dilatih ulang otomatis. Lihat status di pojok kanan atas.
            </p>
          )}
          {hasil.galat?.length > 0 && (
            <>
              <h4>
                Baris tidak valid{hasil.galat_dipotong ? ` (menampilkan ${hasil.galat.length} pertama)` : ''}
              </h4>
              <div className="tabel-gulir tinggi-maks">
                <table>
                  <thead>
                    <tr>
                      <th>Baris</th>
                      <th>Masalah</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hasil.galat.map((g, i) => (
                      <tr key={i}>
                        <td>{g.baris}</td>
                        <td>{g.pesan}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {hasil.peringatan_total > 0 && (
            <>
              <h4>
                Peringatan: harga berubah lebih dari 50% ({hasil.peringatan_total} baris, tetap disimpan)
              </h4>
              <ul className="peringatan">
                {hasil.peringatan.slice(0, 10).map((p, i) => (
                  <li key={i}>
                    ⚠ {tanggalID(p.tanggal)} · {p.nama_pasar} · {p.komoditas}: {rupiah(p.harga_sebelumnya)} → {rupiah(p.harga)}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </>
  )
}

export default function KelolaData() {
  const [tab, setTab] = useState('tambah')
  return (
    <>
      <div className="bar-judul">
        <h1>Kelola data</h1>
      </div>
      <div className="tab" role="tablist">
        {[
          ['tambah', 'Tambah data'],
          ['daftar', 'Daftar dan ubah'],
          ['impor', 'Impor / ekspor CSV'],
        ].map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'aktif' : ''} onClick={() => setTab(k)}>
            {l}
          </button>
        ))}
      </div>
      {tab === 'tambah' && <TabTambah />}
      {tab === 'daftar' && <TabDaftar />}
      {tab === 'impor' && <TabImporEkspor />}
    </>
  )
}