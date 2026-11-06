# Analisis dan Prediksi Harga Bahan Pokok Berdasarkan Waktu di Wilayah Kota Medan

Dashboard web dinamis untuk **Data Analitik** dan **Data Science**: memantau tren harga bahan pokok di Kota Medan,
membandingkan antar kecamatan, memprediksi harga 7 dan 14 hari ke depan, dan memberi status harga
(Normal / Waspada / Lonjakan). Saat data baru ditambahkan, grafik, prediksi, dan status ikut diperbarui otomatis.

- **Sumber data:** SIMPANG Pemko Medan dan SP2KP Kemendag, mulai 2 Januari 2024. Data SIMPANG diperbarui otomatis setiap hari oleh layanan `scraper`
- **Cakupan:** 21 kecamatan Kota Medan (13 punya data, 8 tampil "tidak ada data"), 14 komoditas

---

## Daftar isi

1. [Gambaran singkat](#1-gambaran-singkat)
2. [Yang perlu dipasang](#2-yang-perlu-dipasang)
3. [Menjalankan proyek (langkah demi langkah)](#3-menjalankan-proyek-langkah-demi-langkah)
4. [Memakai dashboard](#4-memakai-dashboard)
5. [Tentang data](#5-tentang-data)
6. [Struktur proyek](#6-struktur-proyek)
7. [Menjalankan tes](#7-menjalankan-tes)

---

## 1. Gambaran singkat

Seluruh aplikasi berjalan di **Docker**, jadi kamu tidak perlu memasang PostgreSQL, Go, atau Node.js untuk
menjalankannya (Python hanya dibutuhkan untuk dua skrip data, lihat bagian 2). Satu perintah menyalakan lima layanan:

```
Peramban  →  frontend (React, nginx)  →  backend (Go)  →  db (PostgreSQL)
                                            ↑   ↓  setelah data berubah
                                            │  ml (Python FastAPI)  →  menulis prediksi, status, evaluasi ke db
                                            │
SIMPANG  →  scraper (Python FastAPI)  ──────┘  impor data baru, juga ditambah ke master CSV
```

| Layanan | Teknologi | Tugas | Alamat di laptop |
|---|---|---|---|
| `frontend` | React + Vite, disajikan nginx | Halaman dashboard | http://localhost:3000 |
| `backend` | Go (chi, pgx) | API, validasi, impor/ekspor CSV, memicu pelatihan ulang | http://localhost:8080/api |
| `ml` | Python (FastAPI, scikit-learn) | Melatih model dan menghitung prediksi dan status | hanya di dalam Docker |
| `scraper` | Python (FastAPI, requests, pandas) | Mengambil harga harian SIMPANG secara otomatis dan menambahkannya tanpa duplikat | hanya di dalam Docker (status lewat `/api/scraper/status`) |
| `db` | PostgreSQL 16 | Menyimpan data harga dan hasil model | `localhost:5432` (bisa diganti lewat `POSTGRES_HOST_PORT` di `.env`) |

Tabel di database dibuat otomatis oleh backend saat pertama kali menyala. Kamu tidak perlu membuat database sendiri.

---

## 2. Yang perlu dipasang

| Alat | Untuk apa | Cek versi |
|---|---|---|
| **Git** | Mengambil kode dari GitHub | `git --version` |
| **Docker Desktop** | Menjalankan seluruh aplikasi | `docker --version` dan `docker compose version` |
| **Python 3.10 atau lebih baru** | Hanya untuk dua skrip data (olah dan impor CSV) | `python --version` |

Catatan:
- **Windows:** Docker Desktop butuh WSL 2 (installer biasanya menawarkan otomatis). Buka Docker Desktop dulu dan tunggu status **"Engine running"** sebelum menjalankan perintah `docker`.
- **Python** hanya dipakai untuk skrip di folder `scripts/`. Untuk mengolah data mentah, pasang satu paket: `pip install pandas`.
- Kamu **tidak** perlu memasang Go, Node.js, atau PostgreSQL, kecuali ingin mengembangkan kode tanpa Docker.
- Repo ini privat. Minta pemilik repo menambahkan akun GitHub-mu sebagai kolaborator terlebih dahulu.

---

## 3. Menjalankan proyek (langkah demi langkah)

Semua perintah dijalankan di terminal (PowerShell di Windows, Terminal di macOS/Linux) dari **folder induk proyek**.

### Langkah 1. Ambil kode

```bash
git clone https://github.com/Arjunamelix/Dasi_Dalis_04.git
cd Dasi_Dalis_04
```

### Langkah 2. Buat berkas `.env`

Berkas `.env` berisi pengaturan database dan **tidak ikut di-commit** (tiap orang membuat sendiri).

Windows (PowerShell):
```powershell
Copy-Item .env.example .env
notepad .env
```

macOS / Linux:
```bash
cp .env.example .env
nano .env
```

Isi `POSTGRES_PASSWORD=` dengan password bebas. **Pakai huruf, angka, dan garis bawah saja.** Karakter seperti `@ : / # %` merusak alamat
koneksi database. Nilai lain boleh dibiarkan seperti bawaan.

Kalau saat langkah 3 muncul galat port 5432 sudah dipakai (sering di Windows), tambahkan `POSTGRES_HOST_PORT=5440` di `.env`.

Pengaturan scraper di `.env` (boleh dibiarkan bawaan):
- `SCRAPER_KONTAK=` isi email tim. Email ini dicantumkan di User-Agent sebagai identitas saat menghubungi SIMPANG.
- `SCRAPER_TULIS_MASTER=1` hanya untuk **satu** laptop di tim (yang meng-commit master CSV). Laptop lain memakai `0` supaya `data/raw/master_data_harian.csv` tidak bentrok saat `git pull`. Lihat bagian 5.

### Langkah 3. Nyalakan semua layanan

Pastikan Docker Desktop sudah berjalan, lalu:

```bash
docker compose up --build -d
```

Pertama kali butuh sekitar **5 sampai 10 menit** karena Docker mengunduh image dan memasang paket. Setelahnya jauh lebih cepat.

### Langkah 4. Pastikan semuanya hidup

```bash
docker compose ps
```

Lima layanan (`db`, `backend`, `ml`, `scraper`, `frontend`) harus berstatus **Up**, dan `db` berstatus **healthy**. Lalu cek backend:

```bash
curl http://localhost:8080/api/health
```
(Di PowerShell: `Invoke-RestMethod http://localhost:8080/api/health`.) Hasilnya harus `{"status":"ok"}`.

### Langkah 5. Olah data mentah

Data mentah gabungan SIMPANG dan SP2KP sudah ada di repo: `data/raw/master_data_harian.csv`. Ubah ke format impor:

```bash
pip install pandas
python scripts/etl_master.py
```

(Di macOS/Linux, pakai `python3`. Tanpa argumen, skrip otomatis membaca `data/raw/master_data_harian.csv`
dan menulis ke `data/processed/`. Bisa juga dijalankan dengan tombol **Run** di VS Code.)

Angka di bawah berasal dari master per **15 Oktober 2026**. Sejak scraper menambah data setiap hari, jumlah barisnya bertambah,
jadi angkamu akan sedikit lebih besar. Yang penting: tidak ada galat dan baris valid bertambah sesuai data baru.

| Keterangan | Jumlah |
|---|---|
| Baris mentah | 260.864 |
| Dibuang (harga 0 = tidak ada data hari itu) | 122.160 |
| Ditolak: telur dilaporkan per butir, bukan per kg | 3.763 |
| Ditolak: menyimpang > 40% dari median pasar lain hari itu | 1.600 |
| Ditolak: di luar batas wajar | 123 |
| **Baris valid** | **133.218** |

Hasilnya tiga berkas di `data/processed/`:
- `harga_harian_simpang.csv` (131.976 baris)
- `harga_harian_sp2kp.csv` (1.242 baris)
- `master_ditolak.csv` (baris yang dibuang beserta alasannya)

### Langkah 6. Impor data ke database

Impor kedua berkas (urutannya bebas):

```bash
python scripts/impor_csv.py data/processed/harga_harian_simpang.csv
python scripts/impor_csv.py data/processed/harga_harian_sp2kp.csv
```

Yang muncul pada database kosong (angka master per 15 Oktober 2026; sekarang lebih besar):
- SIMPANG: `baru disimpan 131976 | dilewati (sudah ada) 0 | tidak valid 0`
- SP2KP: `baru disimpan 1242 | dilewati (sudah ada) 0 | tidak valid 0`

Peringatan "baris berubah harga > 50% (tetap disimpan)" itu wajar: kebanyakan cabai dan bawang merah, yang harganya memang bergejolak.
Perintah ini **aman diulang**: pada percobaan kedua hasilnya `baru disimpan 0`, tanpa duplikat.

### Langkah 7. Tunggu model selesai dilatih

Begitu data masuk, model dilatih otomatis di belakang layar. Dengan 14 komoditas, prosesnya butuh **beberapa menit**. Pantau:

```bash
curl http://localhost:8080/api/status-hitung
docker compose logs ml --tail 10
```

(Di PowerShell: `Invoke-RestMethod http://localhost:8080/api/status-hitung`.)

Tunggu sampai `status_hitung` menjadi `idle` dan `versi_model` sama dengan `versi_data`. Beberapa deret memang dilewati
karena datanya kurang (misalnya jagung di Medan Area dan kedelai di Medan Selayang); itu tercatat di tabel `deret_dilewati`, bukan galat.
Kalau `status_hitung` bernilai `error`, baca isi `pesan_hitung` dan log ML, lalu picu ulang setelah diperbaiki:

```bash
curl -X POST http://localhost:8080/api/retrain
```

### Langkah 8. Buka dashboard

**http://localhost:3000**

Selesai. Mulai sekarang data baru masuk sendiri: layanan `scraper` mengambil harga SIMPANG saat menyala dan setiap hari pukul
10.00 dan 16.00 WIB (lihat bagian 5). Langkah 5 dan 6 hanya perlu dijalankan sekali, saat database masih kosong.

> **Ringkasan cepat** (setelah `.env` dibuat dan Docker menyala):
> ```bash
> docker compose up --build -d
> pip install pandas
> python scripts/etl_master.py
> python scripts/impor_csv.py data/processed/harga_harian_simpang.csv
> python scripts/impor_csv.py data/processed/harga_harian_sp2kp.csv
> ```
> lalu tunggu model selesai dan buka http://localhost:3000.

---

## 4. Memakai dashboard

| Halaman | Alamat | Isi |
|---|---|---|
| **Dashboard** | `/` | Kartu per komoditas: harga terakhir, perubahan 7 hari, prediksi 7 hari, dan status. Pilih "KOTA MEDAN" atau satu kecamatan |
| **Tren** | `/tren` | Grafik garis harga. Pilih komoditas, sampai 3 kecamatan, dan rentang waktu |
| **Perbandingan** | `/perbandingan` | Harga 21 kecamatan untuk satu komoditas, terurut, beserta selisih terhadap harga Kota Medan |
| **Analisis** | `/analisis` | Analisis mendalam dari data warehouse: KPI, peta panas, sebaran antarpasar, wilayah, deret beranotasi |
| **Cerita** | `/cerita` | Lima temuan utama dalam bentuk cerita data |
| **Prediksi** | `/prediksi` | Prediksi 7 dan 14 hari dengan rentang 80%, status, dan evaluasi model dibanding baseline |
| **Kelola Data** | `/kelola` | Tambah, ubah, hapus data; impor dan ekspor CSV; melihat perubahan prediksi sebelum dan sesudah; tab **Pengambilan otomatis** (status scraper, tombol "Ambil data sekarang", riwayat) |

Chip kecil di kanan atas menunjukkan kapan data terakhir diambil dari SIMPANG (mis. "Diambil 5 Nov, 14.43"); klik untuk membuka tab Pengambilan otomatis.

Cara kerja angka di dashboard:
- Harga **kecamatan** = rata-rata harga semua pasar di kecamatan itu pada hari itu.
- Harga **Kota Medan** = median harga semua pasar pada hari itu (minimal 3 pasar melapor).
- **8 kecamatan tampil "tidak ada data"** (Medan Amplas, Baru, Denai, Labuhan, Maimun, Polonia, Tembung, Timur). Itu benar: sumber data tidak
  punya pasar di sana. Tidak ada angka yang ditebak.
- **Garam halus dan susu bubuk** (SP2KP) hanya ada di 2 pasar, jadi tidak punya angka Kota Medan (butuh minimal 3 pasar).
  Pilih kecamatan **Medan Area** atau **Medan Kota** untuk melihatnya.

Untuk mencoba sifat dinamisnya: buka **Kelola Data**, tambahkan satu data harga, lalu lihat kartu prediksi berubah setelah model dihitung ulang
(status "sedang menghitung ulang" tampil sebentar).

---

## 5. Tentang data

- **Sumber:** digabung dalam satu berkas mentah `data/raw/master_data_harian.csv` (kolom `sumber` membedakan asalnya). Data sampai 15 Oktober 2026 hasil scraping tim (260.864 baris); sesudahnya ditambah otomatis oleh layanan `scraper`:
  - **SIMPANG Pemko Medan:** 21 pasar di 13 kecamatan, 12 komoditas, harian sejak 1 Januari 2024.
  - **SP2KP Kemendag:** Pasar Sukaramai dan Pusat Pasar, 2 komoditas.
- **Komoditas (14):**

  | Sumber | Komoditas |
  |---|---|
  | SIMPANG | Beras Medium, Bawang Merah, Bawang Putih, Cabai Merah, Cabai Rawit, Minyak Goreng Curah, Gula Pasir, Daging Sapi, Daging Ayam Ras, Telur Ayam Ras, Jagung, Kedelai |
  | SP2KP | Garam Halus, Susu Bubuk |

- **Satu deret tidak pernah dicampur dari dua sumber.** Kolom `sumber` ikut disimpan di setiap baris.
- **Format impor** (6 kolom, boleh urutan bebas): `tanggal, kecamatan, nama_pasar, komoditas, harga, sumber`. Contoh ada di `data/template_import.csv`.
- **Aturan pembersihan** (`scripts/etl_master.py`), berurutan:
  1. Nama komoditas, sumber, dan pasar dibakukan (mis. `pusat pasar` di SP2KP menjadi `Pusat Pasar`).
  2. Komoditas yang isinya salinan persis komoditas lain dibuang otomatis (pernah terjadi: telur hasil scraping lama identik dengan daging sapi).
  3. Harga 0 dianggap tidak ada data dan dibuang.
  4. Harga telur yang dilaporkan **per butir** (SIMPANG, Januari 2024 sampai Januari 2025) ditolak, tidak dikonversi; deret telur dimulai Februari 2025.
  5. Harga di luar batas wajar komoditas (`config/referensi.json`) ditolak.
  6. Harga yang menyimpang lebih dari 40% dari median pasar lain pada hari, komoditas, dan sumber yang sama (bila minimal 5 pasar melapor) ditolak sebagai dugaan salah input.
- **Hanya data asli per pasar** yang disimpan di tabel `harga`. Rata-rata kecamatan dan median kota dihitung otomatis oleh view `harga_agregat`.
- **Batasan:**
  - Ada lubang data, terutama Mei sampai Juli 2024.
  - 8 dari 21 kecamatan tidak punya data.
  - Sebagian pasar melaporkan harga jagung jauh di atas pasar lain (kemungkinan jenis jagung berbeda).
  - Beberapa deret berhenti melapor sebelum Oktober 2026 (garam dan susu di Pasar Sukaramai, kedelai di Medan Area).
  - Jenis beras (medium) dan satuan susu bubuk (kemasan 400 g) masih berupa asumsi yang perlu dikonfirmasi tim.
  - Ada kemungkinan anomali pada bawang merah 6 September 2024 yang masih diperiksa.
- **Model:** pada data 5 komoditas awal, model boosting belum mengalahkan baseline naif (harga hari ini dianggap berlaku 7 atau 14 hari lagi).
  Ini temuan yang dilaporkan jujur, bukan galat. Hasil pada 14 komoditas sedang dievaluasi; rinciannya di [`Project.md`](Project.md).

Data sintetis untuk uji (`python scripts/gen_data_dev.py`) hanya untuk menguji aplikasi dan **tidak boleh dipakai di laporan**.

### Data baru otomatis (layanan `scraper`)

- **Kapan:** saat layanan menyala (dilewati bila tarikan sukses terakhir kurang dari 3 jam lalu), lalu setiap hari pukul 10.00 dan 16.00 WIB (`SCRAPER_JADWAL`), dan kapan saja lewat tombol **Ambil data sekarang** di Kelola Data.
- **Apa yang diambil:** harga 12 komoditas di 21 pasar dari halaman peta harga SIMPANG (`?menu=peta`), satu permintaan per komoditas per tanggal. Rentangnya dari 7 hari sebelum tanggal terakhir di database sampai hari ini, supaya harga yang diunggah terlambat ikut terisi. SP2KP belum diambil otomatis (ID pasar SP2KP belum lengkap).
- **Alurnya:** ambil, simpan mentah ke `data/raw/otomatis/`, tambahkan ke `master_data_harian.csv`, bersihkan dengan aturan yang sama dengan `etl_master.py` (`scripts/aturan_bersih.py`), lalu impor lewat backend. Setelah itu model dilatih ulang otomatis.
- **Tanpa duplikat:** master dan database memakai kunci yang sama (`tanggal, kecamatan, nama_pasar, komoditas, sumber`). Menjalankan tarikan berkali-kali aman; yang bertambah hanya data yang benar-benar baru. Harga yang tadinya 0 lalu diunggah belakangan akan diisi.
- **Hari yang belum lengkap ditahan:** tanggal dengan kurang dari 15 pasar melapor tidak diimpor dulu; tarikan berikutnya mengimpornya setelah lengkap. Sabtu dan Minggu memang tidak berisi harga di SIMPANG.
- **Etika akses:** robots.txt SIMPANG mengizinkan akses (`Allow: /`). Scraper memakai User-Agent yang jujur (nama proyek dan `SCRAPER_KONTAK`), jeda 2 detik antarpermintaan, dan **berhenti** bila server menolak (HTTP 403/429/503) atau menampilkan halaman tantangan. Tidak ada upaya melewati proteksi.
- **Bekerja dalam tim:** database tiap laptop terpisah. Cukup satu orang (`SCRAPER_TULIS_MASTER=1`) yang meng-commit master CSV. Anggota lain memakai `SCRAPER_TULIS_MASTER=0`; database mereka tetap terisi oleh scraper, atau bisa disamakan dari master terbaru dengan langkah 5 dan 6 tanpa scraping.
- **Tanpa Docker** (mis. menguji satu tarikan dari terminal, dari folder induk):

  ```powershell
  pip install fastapi "uvicorn[standard]" requests tzdata pandas
  $env:PYTHONPATH="scraper"; $env:BACKEND_URL="http://localhost:8080"; $env:SCRIPTS_DIR="scripts"; $env:DATA_DIR="data"
  python -m app.cli --dry-run     # ambil dan bersihkan saja, tidak mengubah apa pun
  python -m app.cli               # tarikan penuh
  ```

---

## 6. Struktur proyek

Gambaran besar: lima layanan aplikasi (`frontend`, `backend`, `ml`, `scraper`, `db`) dijalankan oleh `docker-compose.yml`;
folder `config/`, `data/`, `scripts/`, `notebooks/`, dan `docs/` berisi referensi, data, skrip olah data, eksperimen model, dan dokumentasi.

| Folder | Isi | Dipakai oleh |
|---|---|---|
| `frontend/` | Dashboard web (React + Vite, disajikan nginx) | layanan `frontend` |
| `backend/` | API, validasi, impor/ekspor CSV, data warehouse, pemicu pelatihan ulang (Go) | layanan `backend` |
| `ml/` | Pelatihan model, prediksi, status harga (Python FastAPI) | layanan `ml` |
| `scraper/` | Pengambilan data harga otomatis dari SIMPANG (Python FastAPI) | layanan `scraper` |
| `config/` | Referensi kecamatan, pasar, komoditas, dan batas harga | `backend`, `ml`, `scripts` |
| `data/` | Data mentah, data bersih hasil ETL, data uji | `scripts`, `notebooks` |
| `scripts/` | Skrip olah data yang dijalankan manual dari terminal, dan aturan pembersihan bersama | pengguna, `scraper` |
| `notebooks/` | Notebook eksperimen pemodelan | pengguna (Jupyter / VS Code) |
| `docs/` | Dokumentasi data, aplikasi, model, laporan, logbook | pengguna, dosen |

### 6.1 Berkas di folder induk

```
Dasi_Dalis_04/
├── README.md               panduan menjalankan proyek (dokumen ini)
├── Project.md              keputusan, status, dan rencana kerja proyek
├── docker-compose.yml      menjalankan db + backend + ml + scraper + frontend
├── .env.example            contoh pengaturan; salin menjadi .env (tidak ikut di-commit)
├── .gitignore              daftar berkas yang tidak ikut di-commit (.env, node_modules, .venv, data/processed, data/dev, data/raw/otomatis)
├── .vscode/settings.json   pengaturan VS Code: folder scripts/ dikenali Pylance
└── Makefile                pintasan perintah (macOS/Linux)
```

### 6.2 `frontend/` (dashboard)

```
frontend/
├── Dockerfile              build React lalu sajikan dengan nginx
├── nginx.conf              pengaturan nginx (rute halaman dan penerusan /api ke backend)
├── .dockerignore           berkas yang tidak ikut ke image Docker (node_modules, dist)
├── index.html              halaman HTML dasar
├── package.json            daftar paket JavaScript dan perintah npm
├── vite.config.js          pengaturan Vite (build dan server pengembangan)
└── src/
    ├── main.jsx            titik awal aplikasi React
    ├── App.jsx             daftar rute halaman
    ├── AppContext.jsx      data bersama: referensi, status model, pemantauan pelatihan ulang dan scraper
    ├── styles.css          gaya tampilan umum
    ├── api/
    │   └── client.js       semua pemanggilan API backend
    ├── lib/
    │   ├── format.js       format rupiah, persen, tanggal, waktu
    │   ├── format.test.js  tes format.js
    │   └── scraper.js      pembantu tampilan status dan riwayat scraper
    ├── data/
    │   └── medan_kecamatan.json   batas wilayah 21 kecamatan (GeoJSON) untuk peta
    ├── components/
    │   ├── Layout.jsx      kerangka halaman: judul, menu, status model, status pengambilan data, kaki halaman
    │   ├── Umum.jsx        komponen kecil bersama (pilihan kecamatan/komoditas, badge status, pesan galat)
    │   ├── PetaMedan.jsx   peta choropleth harga per kecamatan (Google Maps)
    │   └── viz/            komponen visual analitik
    │       ├── util.js              warna, format angka dan tanggal, rentang waktu
    │       ├── useMuat.js           pemuat data dari API
    │       ├── viz.css              gaya visual analitik
    │       ├── Tooltip.jsx          tooltip mengikuti kursor
    │       ├── Heatmap.jsx          peta panas (pola musiman, korelasi)
    │       ├── BoxPlot.jsx          sebaran harga antarpasar per bulan
    │       ├── TreemapWilayah.jsx   treemap Kota Medan > kecamatan > pasar
    │       ├── SmallMultiples.jsx   tren mingguan per komoditas
    │       ├── DeretBeranotasi.jsx  harga harian dengan hari besar, celah data, lonjakan
    │       └── PanelKPI.jsx         4 kartu KPI dan grafik perubahan 7 hari
    ├── pages/
    │   ├── Dashboard.jsx      ringkasan harga, kartu KPI, kartu per komoditas
    │   ├── Tren.jsx           grafik tren sampai 3 kecamatan dan peta
    │   ├── Perbandingan.jsx   harga 21 kecamatan untuk satu komoditas
    │   ├── Analisis.jsx       analisis mendalam dengan filter global
    │   ├── Cerita.jsx         lima temuan utama (storytelling)
    │   ├── Prediksi.jsx       prediksi 7 dan 14 hari, status, evaluasi model
    │   └── KelolaData.jsx     tambah, ubah, hapus, impor, ekspor data, pengambilan otomatis
    └── __tests__/
        └── halaman.test.jsx   tes halaman
```

### 6.3 `backend/` (API Go)

```
backend/
├── Dockerfile              build biner Go
├── go.mod                  modul dan daftar dependensi Go
├── go.sum                  checksum dependensi
├── cmd/server/
│   └── main.go             titik awal server: baca pengaturan, jalankan migrasi, nyalakan API
├── internal/
│   ├── config/
│   │   ├── config.go       pengaturan dari variabel lingkungan dan referensi.json
│   │   └── config_test.go
│   ├── handler/
│   │   ├── handler.go      rute dan endpoint HTTP /api
│   │   ├── analitik_wh.go  endpoint /api/analitik/* (KPI, peta panas, sebaran, wilayah, deret, statistik)
│   │   ├── scraper.go      endpoint /api/scraper/status dan /api/scraper/jalankan (diteruskan ke layanan scraper)
│   │   └── scraper_test.go
│   ├── service/
│   │   ├── service.go      logika tulis data, validasi, versi data, pemicu pelatihan ulang
│   │   ├── analitik.go     ringkasan, tren, perbandingan, halaman prediksi
│   │   └── tx.go           pembantu transaksi database
│   ├── repository/
│   │   ├── repository.go   query tabel harga dan tabel hasil model
│   │   └── analitik_wh.go  query data warehouse (fakta dan dimensi)
│   ├── csvimport/
│   │   ├── csvimport.go    baca dan tulis CSV (impor/ekspor)
│   │   └── csvimport_test.go
│   └── model/
│       └── model.go        struktur data (struct) yang dipakai antarlapisan
└── migrations/             skema PostgreSQL, berjalan otomatis saat backend menyala
    ├── embed.go
    ├── 000001_init.up.sql            tabel harga, meta, dan tabel hasil model
    ├── 000001_init.down.sql
    ├── 000002_harga_agregat.up.sql   view harga_agregat (rata-rata kecamatan, median kota)
    ├── 000002_harga_agregat.down.sql
    ├── 000003_warehouse.up.sql       skema bintang: fakta_harga + 4 dimensi, ETL otomatis (trigger)
    └── 000003_warehouse.down.sql
```

### 6.4 `ml/` (layanan model)

```
ml/
├── Dockerfile              image Python untuk layanan ML
├── requirements.txt        paket Python
├── app/
│   ├── main.py             API FastAPI: /health, /retrain, pelatihan ulang di latar belakang
│   ├── pipeline.py         alur lengkap: baca data, fitur, latih, evaluasi, tulis hasil
│   ├── fitur.py            deret harian dan fitur model (model per deret yang sedang berjalan)
│   ├── fitur_global.py     fitur model gabungan hasil S2 (dipakai notebook, dan aplikasi mulai S6)
│   ├── model.py            baseline naif dan model boosting
│   ├── evaluasi.py         evaluasi walk-forward: MAE, RMSE, MAPE vs baseline
│   ├── status.py           status Normal / Waspada / Lonjakan dan evaluasinya
│   ├── kalender.py         daftar hari besar dan periode Ramadan (ketetapan pemerintah)
│   ├── db.py               baca tabel harga, tulis tabel hasil model
│   └── config.py           pengaturan dari variabel lingkungan (ML_*)
└── tests/
    ├── conftest.py               data uji sintetis
    ├── test_fitur.py
    ├── test_fitur_global.py      termasuk cek tanpa kebocoran data
    ├── test_evaluasi_status.py
    └── test_pipeline_api.py
```

### 6.5 `scraper/` (layanan pengambil data)

```
scraper/
├── Dockerfile              image Python untuk layanan scraper
├── .dockerignore           berkas yang tidak ikut ke image Docker (tests, cache)
├── requirements.txt        paket Python
├── app/
│   ├── main.py             API FastAPI: /health, /status, /jalankan; menyalakan penjadwal
│   ├── jadwal.py           penjadwal: tarikan saat menyala dan pada jam SCRAPER_JADWAL
│   ├── tarikan.py          alur satu tarikan: rentang, ambil, simpan mentah, perbarui master, bersihkan, impor
│   ├── sumber_simpang.py   pengambil halaman peta harga SIMPANG
│   ├── sumber_sp2kp.py     pengambil API SP2KP (belum aktif: menunggu ID pasar)
│   ├── backend.py          tanggal terakhir di database dan impor CSV lewat backend
│   ├── riwayat.py          riwayat tarikan (data/raw/otomatis/riwayat_tarikan.jsonl)
│   ├── cli.py              menjalankan satu tarikan dari terminal (python -m app.cli)
│   ├── config.py           pengaturan dari variabel lingkungan (SCRAPER_*)
│   └── __init__.py
└── tests/
    ├── conftest.py         halaman SIMPANG tiruan dan folder data sementara
    ├── test_sumber.py
    └── test_tarikan.py
```

### 6.6 `config/`, `data/`, `scripts/`, `notebooks/`

```
config/
└── referensi.json          21 kecamatan, 21 pasar, 14 komoditas, satuan, batas harga, sumber data

data/
├── template_import.csv     contoh format impor (6 kolom)
├── raw/                    data mentah, tidak pernah diedit
│   ├── master_data_harian.csv    gabungan SIMPANG + SP2KP (masukan etl_master.py), ditambah otomatis oleh scraper
│   ├── otomatis/                 hasil mentah tiap tarikan scraper dan riwayat_tarikan.jsonl (tidak ikut di-commit)
│   └── simpang/
│       └── data_harian_simpang_medan.csv   data SIMPANG awal, 5 komoditas (arsip)
├── processed/              hasil etl_master.py (tidak ikut di-commit, dibuat ulang)
│   ├── harga_harian_simpang.csv
│   ├── harga_harian_sp2kp.csv
│   └── master_ditolak.csv        baris yang dibuang beserta alasannya
└── dev/                    data sintetis untuk uji (tidak ikut di-commit, jangan dipakai di laporan)

scripts/
├── etl_master.py           ETL utama: master_data_harian.csv → data/processed/
├── aturan_bersih.py        aturan pembersihan dan penggabungan ke master, dipakai etl_master.py dan scraper
├── test_aturan_bersih.py   tes aturan_bersih.py
├── impor_csv.py            kirim CSV hasil ETL ke backend (POST /api/harga/import)
├── laporan_kualitas.py     buat docs/kualitas_data.md (kualitas data sebelum dan sesudah)
├── cek_akses_simpang.py    cek sekali apakah halaman SIMPANG dapat diakses
├── etl_simpang.py          ETL lama khusus data SIMPANG 5 komoditas (arsip)
└── gen_data_dev.py         pembuat data sintetis uji

notebooks/
└── pemodelan.ipynb         eksperimen pemodelan, disusun bertahap per komponen penilaian (S1 dan S2 sudah ada)
```

### 6.7 `docs/` (dokumentasi)

```
docs/
├── PANDUAN_SETUP.md        panduan setup langkah demi langkah
├── kontrak_api.md          daftar endpoint API dan formatnya
├── alur_data_dev.md        alur data dari mentah sampai database
├── hasil_cek_sumber.md     hasil pengecekan sumber data
├── kualitas_data.md        laporan kualitas data sebelum dan sesudah pembersihan (dibuat laporan_kualitas.py)
├── warehouse.md            skema bintang, ERD, contoh query
├── visualisasi.md          daftar visual dan interaktivitas dashboard
├── logbook.md              catatan kerja mingguan
├── model/
│   ├── S1_problem_framing.md       ringkasan problem framing (S1)
│   └── S2_feature_engineering.md   ringkasan preprocessing dan feature engineering (S2)
└── laporan/                laporan akhir dan bahan presentasi
```

## 7. Menjalankan tes

Tes **tidak** berjalan di Docker; ia butuh alat masing-masing di laptop (hanya bagi yang ingin mengembangkan kode).

| Bagian | Syarat | Perintah |
|---|---|---|
| Frontend | Node.js 20+ | `cd frontend && npm install && npm test` |
| ML | Python 3.10+ | `cd ml && python -m venv .venv`, aktifkan venv, `pip install -r requirements.txt`, `pytest` (harus **23 lulus**) |
| Backend | Go 1.25+ | `cd backend && go mod tidy && go vet ./... && go test ./...` |
| Scraper | Python 3.10+ | dari folder induk: `pip install -r scraper/requirements.txt`, lalu `python -m pytest scraper/tests -q` (harus **34 lulus**) |
| Aturan bersih | Python 3.10+ | dari folder induk: `python -m pytest scripts/test_aturan_bersih.py -q` (harus **9 lulus**) |

Aktivasi venv: Windows `.\.venv\Scripts\Activate.ps1`; macOS/Linux `source .venv/bin/activate`.

Notebook `notebooks/pemodelan.ipynb` memakai venv ML yang sama ditambah dua paket: `pip install matplotlib ipykernel`.
Buka di VS Code, pilih kernel `ml\.venv`, lalu **Run All** (sekitar 5–10 menit). Notebook hanya memakai data sampai 15 Oktober 2026.