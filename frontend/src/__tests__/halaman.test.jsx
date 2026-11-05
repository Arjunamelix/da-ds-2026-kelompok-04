// Tes asap: tiap halaman dirender dengan API tiruan yang bentuk JSON-nya mengikuti docs/kontrak_api.md.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App.jsx'

const REF = {
  data_sintetis: true,
  status_konfigurasi: 'draf-dev',
  app_env: 'dev',
  kota: { kecamatan: 'KOTA MEDAN', nama_pasar: 'SEMUA' },
  kecamatan: ['Medan Area', 'Medan Petisah'],
  komoditas: [
    { kode: 'beras_medium', nama: 'Beras Medium', satuan: 'kg', min: 8000, max: 30000, kelompok: 'inti' },
    { kode: 'cabai_merah_keriting', nama: 'Cabai Merah Keriting', satuan: 'kg', min: 10000, max: 150000, kelompok: 'inti' },
  ],
  pasar: [
    { nama: 'Pasar Bakti', kecamatan: 'Medan Area' },
    { nama: 'Pasar Sukaramai', kecamatan: 'Medan Area' },
    { nama: 'Pasar Petisah', kecamatan: 'Medan Petisah' },
  ],
  sumber: [
    { kode: 'PIHPS', nama: 'PIHPS' },
    { kode: 'DEV', nama: 'Data sintetis', dev_saja: true },
  ],
  pemetaan_kecamatan: {},
}

const titik = Array.from({ length: 40 }, (_, i) => ({
  tanggal: new Date(Date.UTC(2026, 8, 10 + i)).toISOString().slice(0, 10),
  harga: 14000 + i * 20,
}))

const RESP = {
  '/api/referensi': REF,
  '/api/status-hitung': { versi_data: 3, versi_model: 3, status_hitung: 'idle', pesan_hitung: '' },
  '/api/ringkasan': {
    kecamatan: 'KOTA MEDAN',
    pasar_acuan: 'SEMUA',
    sumber: 'DEV',
    pasar_sendiri: true,
    kartu: [
      {
        komoditas: 'beras_medium', nama: 'Beras Medium', satuan: 'kg', tanggal_terakhir: '2026-10-21', harga_terakhir: 14900,
        harga_7h_lalu: 14800, perubahan_7h_abs: 100, perubahan_7h_pct: 0.68, prediksi_7h: 14887, prediksi_7h_bawah: 14743,
        prediksi_7h_atas: 14947, status: 'Waspada', perubahan_prediksi_pct: -0.1, keterangan: '',
      },
      {
        komoditas: 'cabai_merah_keriting', nama: 'Cabai Merah Keriting', satuan: 'kg', tanggal_terakhir: '2026-10-21', harga_terakhir: 38800,
        harga_7h_lalu: null, perubahan_7h_abs: null, perubahan_7h_pct: null, prediksi_7h: null, prediksi_7h_bawah: null,
        prediksi_7h_atas: null, status: null, perubahan_prediksi_pct: null, keterangan: 'data_belum_cukup',
      },
    ],
  },
  '/api/tren': {
    komoditas: 'beras_medium', nama: 'Beras Medium', satuan: 'kg',
    seri: [{ kecamatan: 'KOTA MEDAN', pasar_acuan: 'SEMUA', sumber: 'DEV', pasar_sendiri: true, tanpa_data: false, titik }],
  },
  '/api/perbandingan': {
    komoditas: 'beras_medium', nama: 'Beras Medium', satuan: 'kg', rata_rata_kota: 14900, dasar_rata_rata: 'median harga pasar se-Kota Medan (SIMPANG)',
    kecamatan: [
      { kecamatan: 'Medan Petisah', pasar_acuan: 'SEMUA', sumber: 'SIMPANG', pasar_sendiri: true, jumlah_pasar: 1, tanggal_data: '2026-10-15', harga: 15100, selisih_pct_vs_kota: 1.3, tanpa_data: false, keterangan: 'rata-rata 1 pasar' },
      { kecamatan: 'Medan Area', pasar_acuan: 'SEMUA', sumber: 'SIMPANG', pasar_sendiri: true, jumlah_pasar: 2, tanggal_data: '2026-10-15', harga: 14700, selisih_pct_vs_kota: -1.3, tanpa_data: false, keterangan: 'rata-rata 2 pasar' },
      { kecamatan: 'Medan Belawan', pasar_acuan: '', sumber: '', pasar_sendiri: false, jumlah_pasar: 0, tanggal_data: '', harga: null, selisih_pct_vs_kota: null, tanpa_data: true, keterangan: 'tidak ada data pasar di sumber (SIMPANG)' },
    ],
  },
  '/api/prediksi': {
    kecamatan: 'KOTA MEDAN', komoditas: 'beras_medium', pasar_acuan: 'SEMUA', sumber: 'DEV', pasar_sendiri: true,
    prediksi: [
      { horizon: 7, tanggal_dasar: '2026-10-21', harga_dasar: 14900, harga_prediksi: 14887, batas_bawah: 14743, batas_atas: 14947 },
      { horizon: 14, tanggal_dasar: '2026-10-21', harga_dasar: 14900, harga_prediksi: 14905, batas_bawah: 14723, batas_atas: 14970 },
    ],
    status: { status: 'Normal', perubahan_prediksi_pct: -0.09, ambang_waspada_pct: 2, ambang_lonjakan_pct: 3, tanggal_dasar: '2026-10-21' },
    evaluasi: [
      { horizon: 7, n_uji: 64, mae_model: 69, rmse_model: 80, mape_model: 0.47, mae_baseline: 59, rmse_baseline: 70, mape_baseline: 0.4, mengalahkan_baseline: false },
      { horizon: 14, n_uji: 64, mae_model: 98, rmse_model: 110, mape_model: 0.66, mae_baseline: 97, rmse_baseline: 108, mape_baseline: 0.65, mengalahkan_baseline: false },
    ],
  },
  '/api/evaluasi': {
    deret: [],
    status: [{ komoditas: 'beras_medium', n_uji: 359, n_berisiko: 0, recall_berisiko: null, presisi_berisiko: null, ambang_waspada_pct: 2, ambang_lonjakan_pct: 3 }],
  },
  '/api/harga': { data: [], total: 0, page: 1, per_page: 25 },
  '/api/scraper/status': {
    sedang_berjalan: false, mulai: null, pemicu: null, aktif: true, sumber: ['simpang'], jadwal: ['10:00', '16:00'], zona: 'Asia/Jakarta',
    berikutnya: '2026-11-05T16:00+07:00',
    terakhir_sukses: null, // diisi di bawah
    riwayat: [],
  },
  '/api/scraper/jalankan': { status: 'running' },
}
const TARIKAN = {
  mulai: '2026-11-05T10:00:02+07:00', selesai: '2026-11-05T10:04:31+07:00', pemicu: 'jadwal', dry_run: false, status: 'sukses', baris_baru: 2964,
  sumber: {
    simpang: {
      status: 'sukses', ambil: { permintaan: 120, dari: '2026-10-27', sampai: '2026-11-05' },
      ditahan: [{ tanggal: '2026-11-04', pasar: 6 }], tanggal_berdata: ['2026-10-30', '2026-11-03'],
    },
  },
}
RESP['/api/scraper/status'] = { ...RESP['/api/scraper/status'], terakhir: TARIKAN, terakhir_sukses: TARIKAN, riwayat: [TARIKAN] }

let panggilan
beforeEach(() => {
  panggilan = []
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.fetch = vi.fn(async (url, opts = {}) => {
    const path = String(url).split('?')[0]
    panggilan.push({ path, method: opts.method || 'GET', body: opts.body })
    if (path === '/api/harga' && opts.method === 'POST') {
      return { ok: true, status: 201, json: async () => ({ harga: { id: 1 }, peringatan: ['harga berubah 60%'], versi_data: 4, prediksi_sebelum: [] }) }
    }
    if (!(path in RESP)) return { ok: false, status: 404, json: async () => ({ error: 'tidak ada ' + path }) }
    return { ok: true, status: 200, json: async () => RESP[path] }
  })
})
afterEach(cleanup)

const tampil = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )

describe('halaman', () => {
  it('Dashboard: kartu harga, perubahan, prediksi, status, dan pesan data belum cukup', async () => {
    tampil('/')
    expect(await screen.findByText('Beras Medium')).toBeTruthy()
    expect(screen.getByText(/Rp\s14\.900/)).toBeTruthy()
    expect(screen.getByText(/Waspada/)).toBeTruthy()
    expect(screen.getByText('data belum cukup')).toBeTruthy()
    expect(screen.getByText(/data sintetis/i)).toBeTruthy() // banner mode pengembangan
  })

  it('Tren: memanggil API dan menampilkan keterangan deret', async () => {
    tampil('/tren?komoditas=beras_medium')
    expect(await screen.findByText(/median harga semua pasar \(DEV\)/)).toBeTruthy()
    expect(panggilan.some((p) => p.path === '/api/tren')).toBe(true)
  })

  it('Perbandingan: termahal/termurah, rata-rata pasar per kecamatan, dan kecamatan tanpa data tidak disembunyikan', async () => {
    tampil('/perbandingan')
    expect(await screen.findByText('Rincian 21 kecamatan')).toBeTruthy()
    expect(screen.getByText('rata-rata 2 pasar')).toBeTruthy()
    expect(screen.getByText(/tidak ada data pasar di sumber/)).toBeTruthy()
    expect(screen.getByText('Medan Belawan')).toBeTruthy()
    expect(screen.getByText('termahal')).toBeTruthy()
    expect(screen.getByText('termurah')).toBeTruthy()
  })

  it('Prediksi: tabel prediksi 7/14 hari, status, dan evaluasi vs baseline', async () => {
    tampil('/prediksi')
    expect(await screen.findByText('Hasil prediksi')).toBeTruthy()
    expect(screen.getAllByText('7 hari').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('14 hari').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Evaluasi model vs baseline naif')).toBeTruthy()
    expect(screen.getAllByText('Tidak').length).toBe(2)
  })

  it('Kelola Data: menyimpan data dengan nama_pasar SEMUA untuk level kota dan menampilkan peringatan', async () => {
    tampil('/kelola')
    const harga = await screen.findByPlaceholderText('mis. 52000')
    fireEvent.change(harga, { target: { value: '52000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Simpan data' }))
    await waitFor(() => expect(panggilan.some((p) => p.method === 'POST' && p.path === '/api/harga')).toBe(true))
    const kirim = panggilan.find((p) => p.method === 'POST' && p.path === '/api/harga')
    const body = JSON.parse(kirim.body)
    expect(body).toMatchObject({ kecamatan: 'KOTA MEDAN', nama_pasar: 'SEMUA', komoditas: 'beras_medium', harga: 52000, sumber: 'PIHPS' })
    expect(await screen.findByText('Data tersimpan')).toBeTruthy()
    expect(screen.getByText(/harga berubah 60%/)).toBeTruthy()
  })

  it('Header: kapan data terakhir diambil dari SIMPANG', async () => {
    tampil('/')
    const chip = await screen.findByText('Diambil 5 Nov, 10.04')
    expect(chip.getAttribute('title')).toBe('Data SIMPANG terakhir diambil · data sampai 3 Nov 2026 · berikutnya 16.00 WIB')
    expect(chip.getAttribute('href')).toBe('/kelola?tab=otomatis')
  })

  it('Kelola Data: tab Pengambilan otomatis menampilkan riwayat dan tombol Ambil data sekarang', async () => {
    tampil('/kelola?tab=otomatis')
    expect(await screen.findByText('Riwayat pengambilan')).toBeTruthy()
    expect(screen.getByText('Terjadwal')).toBeTruthy()
    expect(screen.getByText('Sukses')).toBeTruthy()
    expect(screen.getByText('27 Okt 2026 – 5 Nov 2026')).toBeTruthy()
    expect(screen.getByText(/4 Nov 2026 ditahan \(baru 6 pasar melapor\)/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Ambil data sekarang' }))
    await waitFor(() => expect(panggilan.some((p) => p.method === 'POST' && p.path === '/api/scraper/jalankan')).toBe(true))
    expect(await screen.findByText(/Pengambilan data dimulai/)).toBeTruthy()
  })

  it('Scraper mati: halaman lain tetap jalan dan chip memberi tahu', async () => {
    const asli = RESP['/api/scraper/status']
    delete RESP['/api/scraper/status']
    try {
      tampil('/')
      expect(await screen.findByText('Beras Medium')).toBeTruthy()
      expect(await screen.findByText('Scraper tidak aktif')).toBeTruthy()
    } finally {
      RESP['/api/scraper/status'] = asli
    }
  })

  it('Kelola Data: harga bukan angka ditolak di sisi klien tanpa memanggil API', async () => {
    tampil('/kelola')
    const harga = await screen.findByPlaceholderText('mis. 52000')
    fireEvent.change(harga, { target: { value: '52.000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Simpan data' }))
    expect(await screen.findByText(/angka bulat tanpa titik/)).toBeTruthy()
    expect(panggilan.some((p) => p.method === 'POST')).toBe(false)
  })
})