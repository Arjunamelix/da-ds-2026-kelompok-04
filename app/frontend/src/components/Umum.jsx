/**
 * ==============================================================================
 * KOMPONEN BERSAMA / REUSABLE UI (Umum.jsx)
 * ==============================================================================
 * Berisi komponen-komponen antarmuka yang dipakai berulang di berbagai halaman:
 * - StatusBadge     : Lencana status (Normal, Waspada, Lonjakan) beserta ikon
 * - Galat           : Kotak notifikasi pesan error/gagal
 * - Memuat          : Indikator loading spinner / teks memuat data
 * - Kosong          : Tampilan fallback saat data tidak tersedia
 * - PilihKecamatan  : Komponen dropdown pemilihan kecamatan
 * - PilihKomoditas  : Komponen dropdown pemilihan bahan pokok
 * - KeteranganAcuan : Catatan kaki penjelasan batas acuan dan validasi
 * ==============================================================================
 */

import { STATUS_IKON } from '../lib/format.js'

export function StatusBadge({ status }) {
  if (!status) return null
  return (
    <span className={`badge badge-${status.toLowerCase()}`}>
      <span aria-hidden="true">{STATUS_IKON[status]}</span> {status}
    </span>
  )
}

export function Galat({ pesan, detail }) {
  if (!pesan) return null
  return (
    <div className="kotak kotak-galat" role="alert">
      <strong>{pesan}</strong>
      {detail && detail.length > 0 && (
        <ul>
          {detail.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function Memuat({ teks = 'Memuat data…' }) {
  return <div className="memuat">{teks}</div>
}

export function Kosong({ children }) {
  return <div className="kosong">{children}</div>
}

// Pilihan kecamatan: KOTA MEDAN lalu 21 kecamatan.
export function PilihKecamatan({ nilai, onChange, referensi, label = 'Kecamatan', id = 'kec' }) {
  return (
    <label className="field" htmlFor={id}>
      <span>{label}</span>
      <select id={id} value={nilai} onChange={(e) => onChange(e.target.value)}>
        <option value={referensi.kota.kecamatan}>{referensi.kota.kecamatan} (level kota)</option>
        {referensi.kecamatan.map((k) => (
          <option key={k} value={k}>
            {k}
          </option>
        ))}
      </select>
    </label>
  )
}

export function PilihKomoditas({ nilai, onChange, referensi, label = 'Komoditas', id = 'kom', kosong }) {
  return (
    <label className="field" htmlFor={id}>
      <span>{label}</span>
      <select id={id} value={nilai} onChange={(e) => onChange(e.target.value)}>
        {kosong && <option value="">{kosong}</option>}
        {referensi.komoditas.map((k) => (
          <option key={k.kode} value={k.kode}>
            {k.nama}
          </option>
        ))}
      </select>
    </label>
  )
}

// Keterangan deret yang dipakai: median pasar (kota), rata-rata pasar (kecamatan), atau satu pasar.
export function KeteranganAcuan({ kecamatan, pasarAcuan, sumber, pasarSendiri, kotaNama, jumlahPasar }) {
  if (!pasarAcuan) return null
  if (kecamatan === kotaNama) {
    return <p className="catatan">Median harga semua pasar se-Kota Medan · sumber {sumber}</p>
  }
  if (pasarAcuan === 'SEMUA') {
    return (
      <p className="catatan">
        Rata-rata harga {jumlahPasar > 0 ? `${jumlahPasar} pasar` : 'pasar'} di kecamatan ini · sumber {sumber}
      </p>
    )
  }
  return (
    <p className="catatan">
      {pasarSendiri ? `Pasar terpantau: ${pasarAcuan}` : `Mengacu pada ${pasarAcuan}`} · sumber {sumber}
    </p>
  )
}