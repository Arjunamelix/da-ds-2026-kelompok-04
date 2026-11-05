import { Link, NavLink, Outlet } from 'react-router-dom'
import { useState } from 'react'
import { useApp } from '../AppContext.jsx'
import { api } from '../api/client.js'
import { jamID, tanggalID, waktuSingkat } from '../lib/format.js'
import { dataSampai, pesanSumber } from '../lib/scraper.js'

function ChipHitung() {
  const { hitung, menghitung, picuPolling } = useApp()
  const [galat, setGalat] = useState('')
  if (!hitung) return <span className="chip chip-abu">status model…</span>

  const latih = async () => {
    setGalat('')
    try {
      await api.latihUlang()
      picuPolling()
    } catch (e) {
      setGalat(e.message)
    }
  }

  if (hitung.status_hitung === 'error') {
    return (
      <span className="chip chip-merah" title={hitung.pesan_hitung}>
        Pelatihan gagal
        <button className="tombol-kecil" onClick={latih}>
          Coba lagi
        </button>
        {galat && <em>{galat}</em>}
      </span>
    )
  }
  if (menghitung) {
    return (
      <span className="chip chip-oranye" aria-live="polite">
        <span className="spinner" aria-hidden="true" /> Sedang menghitung ulang…
      </span>
    )
  }
  return (
    <span className="chip chip-aqua" title={`Data v${hitung.versi_data} · model v${hitung.versi_model}`}>
      Model terbaru
    </span>
  )
}

// Kapan data terakhir diambil dari SIMPANG; klik untuk membuka Kelola Data > Pengambilan otomatis.
function ChipScraper() {
  const { scraper, galatScraper } = useApp()
  const ke = '/kelola?tab=otomatis'
  if (galatScraper) {
    return (
      <Link className="chip chip-abu" to={ke} title={galatScraper.message}>
        Scraper tidak aktif
      </Link>
    )
  }
  if (!scraper) return null
  if (scraper.sedang_berjalan) {
    return (
      <Link className="chip chip-oranye" to={ke} aria-live="polite">
        <span className="spinner" aria-hidden="true" /> Mengambil data…
      </Link>
    )
  }
  if (scraper.terakhir?.status === 'galat') {
    return (
      <Link className="chip chip-merah" to={ke} title={pesanSumber(scraper.terakhir).join('\n')}>
        Ambil data gagal
      </Link>
    )
  }
  const sukses = scraper.terakhir_sukses
  const sampai = dataSampai(sukses)
  const info = [
    sukses && 'Data SIMPANG terakhir diambil',
    sampai && `data sampai ${tanggalID(sampai)}`,
    scraper.berikutnya && `berikutnya ${jamID(scraper.berikutnya)} WIB`,
  ]
  return (
    <Link className="chip chip-abu" to={ke} title={info.filter(Boolean).join(' · ')}>
      {sukses ? `Diambil ${waktuSingkat(sukses.selesai)}` : 'Belum ada pengambilan data'}
    </Link>
  )
}

export default function Layout() {
  const { ref, galatRef } = useApp()
  return (
    <div className="app">
      <header className="atas">
        <div className="atas-isi">
          <div className="judul">
            <strong>Harga Bahan Pokok Kota Medan</strong>
            <span>Analisis dan prediksi berdasarkan waktu</span>
          </div>
          <nav aria-label="Navigasi utama">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/tren">Tren</NavLink>
            <NavLink to="/perbandingan">Perbandingan</NavLink>
            <NavLink to="/analisis">Analisis</NavLink>
            <NavLink to="/cerita">Cerita</NavLink>
            <NavLink to="/prediksi">Prediksi</NavLink>
            <NavLink to="/kelola">Kelola Data</NavLink>
          </nav>
          <div className="chip-baris">
            <ChipScraper />
            <ChipHitung />
          </div>
        </div>
        {ref?.data_sintetis && (
          <div className="banner-dev" role="status">
            Mode pengembangan: seluruh angka berasal dari data sintetis (sumber DEV), bukan data asli. Jangan dipakai di laporan.
          </div>
        )}
      </header>
      <main className="isi">
        {galatRef ? (
          <div className="kotak kotak-galat" role="alert">
            <strong>Tidak bisa memuat referensi dari backend.</strong>
            <p>{galatRef}</p>
          </div>
        ) : !ref ? (
          <div className="memuat">Memuat…</div>
        ) : (
          <Outlet />
        )}
      </main>
      <footer className="kaki">
        Sumber data: SIMPANG Pemko Medan dan SP2KP Kemendag (hasil scraping tim). Prediksi bersifat estimasi statistik, bukan jaminan harga.
      </footer>
    </div>
  )
}