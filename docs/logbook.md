# Logbook

| Tanggal | Progres | Oleh |
|---|---|---|
| 2026-10-21 | Keputusan: tim 5 orang, pengumpulan 3-5 minggu, 21 kecamatan via opsi B, komoditas dengan aturan 90%, impor CSV sebagai satu-satunya jalur data, data sintetis dev diizinkan, GitHub privat | - |
| 2026-10-21 | Kerangka repo: skema PostgreSQL, API Go (CRUD, impor/ekspor idempotent, validasi 5.4, pemicu retrain), layanan ML (baseline + boosting, walk-forward, status), frontend React 5 halaman, Docker Compose, data sintetis dev | Claude |
| 2026-10-22 | Perbaikan: prop `ref` React yang tidak terbaca di pemilih kecamatan/komoditas; validasi harga di formulir; dokumen README dan kontrak API | Claude |
| 2026-10-22 | Dataset SIMPANG diterima (106.995 baris, 21 pasar di 13 kecamatan, 5 komoditas, 1 Jan 2024 - 15 Okt 2026). ETL: 59.322 baris valid. Keputusan: kecamatan = rata-rata pasar, kota = median pasar, 8 kecamatan tanpa pasar tampil "tidak ada data", komoditas mengikuti CSV | Claude |
| 2026-10-22 | Temuan: model belum mengalahkan baseline naif di data SIMPANG (beberapa varian dan jendela uji dicoba); keputusan arah model menunggu tim | Claude |
| 2026-10-23 | View `harga_agregat` (migrasi 000002); referensi.json versi SIMPANG; migrasi dan kueri SQL diuji di PostgreSQL 16; panduan setup | Claude |
| 2026-10-23 | Struktur folder dibuat di laptop (`Dasi_Dalis_04`: backend, frontend, ml), nama folder diseragamkan huruf kecil, repo Git lokal dibuat dan terhubung ke GitHub privat; commit pertama menunggu file pertama (folder kosong tidak bisa di-commit) | Pengguna |
| 2026-10-23 | `Project.md` diperbarui (status pengerjaan, rundown sisa pekerjaan, keputusan terbuka); fokus berikutnya dashboard visualisasi | Claude |
