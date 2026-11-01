# Kontrak API (Go, prefix `/api`)

Format galat: `{"error": "...", "detail": ["..."]}`. Status: 400 permintaan salah, 404 tidak ditemukan,
409 duplikat kunci unik, 422 validasi gagal (detail memuat tiap aturan yang dilanggar), 500 galat server.
Kunci unik: `tanggal + kecamatan + nama_pasar + komoditas + sumber`. Harga level kota:
`kecamatan = "KOTA MEDAN"` dan `nama_pasar = "SEMUA"` (keduanya harus berpasangan).

| Metode | Jalur | Fungsi |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` |
| GET | `/referensi` | Daftar kecamatan, komoditas (satuan, batas harga), pasar, sumber, pemetaan opsi B |
| GET | `/harga` | Daftar berhalaman. Query: `kecamatan, pasar, komoditas, sumber, dari, sampai, page, per_page` |
| POST | `/harga` | Tambah satu data (JSON 6 kolom). 201 + `{harga, peringatan[], versi_data, prediksi_sebelum[]}` |
| PUT | `/harga/{id}` | Ubah satu data |
| DELETE | `/harga/{id}` | Hapus satu data |
| POST | `/harga/import` | Impor CSV (multipart, field `file`, header 6 kolom, urutan bebas). Idempotent |
| GET | `/harga/export` | Ekspor CSV (filter sama dengan `/harga`) |
| GET | `/harga/template` | Contoh CSV impor |
| GET | `/ringkasan?kecamatan=` | Kartu per komoditas: harga terakhir, perubahan 7 hari, prediksi 7 hari, status |
| GET | `/tren?komoditas=&kecamatan=&dari=&sampai=` | Deret harga; `kecamatan` boleh berulang, maksimal 3 |
| GET | `/perbandingan?komoditas=&tanggal=` | 21 kecamatan, selisih % terhadap rata-rata Kota Medan; yang tanpa data tetap tampil |
| GET | `/prediksi?komoditas=&kecamatan=` | Prediksi 7 dan 14 hari + rentang, status, evaluasi vs baseline |
| POST | `/prediksi/sesudah` | Body: daftar `{kecamatan,nama_pasar,komoditas,sumber}`; balasan prediksi 7 hari terkini (tampilan sebelum → sesudah) |
| GET | `/status?kecamatan=` | Status Normal/Waspada/Lonjakan per komoditas |
| GET | `/evaluasi?komoditas=` | Metrik walk-forward per deret + recall/presisi kelas berisiko |
| GET | `/versi-data` | `{versi_data, versi_model}` |
| GET | `/status-hitung` | `{versi_data, versi_model, status_hitung (idle/running/error), pesan_hitung, ...}` |
| POST | `/retrain` | Picu pelatihan ulang manual (202) |

## Impor CSV

Respons: `total_baris, disisipkan, dilewati_sudah_ada, tidak_valid, galat[{baris,pesan}]` (maks 100),
`peringatan[]` (harga berubah > 50%, tetap disimpan), `versi_data`, `prediksi_sebelum[]`.
`versi_data` hanya naik bila ada baris baru.

## Layanan ML (internal, dipanggil Go)

`POST /retrain` (202, asinkron) dan `GET /health`. Hasil ditulis ke tabel `prediksi`, `status_harga`,
`evaluasi_model`, `evaluasi_status`, `deret_dilewati`; `meta.versi_model` diperbarui saat selesai.
