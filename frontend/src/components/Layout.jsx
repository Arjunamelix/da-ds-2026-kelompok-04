import { NavLink, Outlet } from 'react-router-dom'
import { useState } from 'react'
import { useApp } from '../AppContext.jsx'
import { api } from '../api/client.js'

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
            <NavLink to="/prediksi">Prediksi</NavLink>
            <NavLink to="/kelola">Kelola Data</NavLink>
          </nav>
          <ChipHitung />
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
        Sumber data: PIHPS BI, SIMPANG Pemko Medan, Badan Pangan, SP2KP. Prediksi bersifat estimasi statistik, bukan jaminan harga.
      </footer>
    </div>
  )
}