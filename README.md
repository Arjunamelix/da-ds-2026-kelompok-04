# Analisis dan Prediksi Harga Bahan Pokok Berdasarkan Waktu di Wilayah Kota Medan

Dashboard web dinamis untuk mata kuliah **Data Analitik** dan **Data Science** (Kelompok 4, Institut Teknologi Del). Aplikasi ini:
- memantau tren harga bahan pokok di Kota Medan;
- membandingkan harga antarkecamatan dan antarpasar;
- memprediksi harga 7 dan 14 hari ke depan;
- memberi status harga (Normal / Waspada / Lonjakan).

Saat data baru masuk (otomatis dari scraper atau manual dari halaman Kelola Data), grafik, KPI, prediksi, dan status ikut diperbarui.

- **Sumber data:** SIMPANG Pemko Medan dan SP2KP Kemendag, mulai 2 Januari 2024. Data SIMPANG diperbarui otomatis setiap hari oleh layanan `scraper`.
- **Cakupan:** 21 kecamatan Kota Medan (13 punya data, 8 tampil "tidak ada data"), 21 pasar, 14 komoditas.
- **Keadaan dokumen ini:** progres per **11 November 2026**. Pemodelan sudah sampai **S4**; tahap berikutnya **S5**. Rincian ada di bagian 2 dan 12.

---

## Daftar isi

1. [Gambaran singkat](#1-gambaran-singkat)
2. [Status progres](#2-status-progres)
3. [Yang perlu dipasang](#3-yang-perlu-dipasang)
4. [Menjalankan proyek (langkah demi langkah)](#4-menjalankan-proyek-langkah-demi-langkah)
5. [Memakai dashboard](#5-memakai-dashboard)
6. [Tentang data](#6-tentang-data)
7. [Pemodelan (Data Science)](#7-pemodelan-data-science)
8. [Database, data warehouse, dan kerja tim](#8-database-data-warehouse-dan-kerja-tim)
9. [Struktur proyek](#9-struktur-proyek)
10. [Menjalankan tes](#10-menjalankan-tes)
11. [Masalah umum dan solusinya](#11-masalah-umum-dan-solusinya)
12. [Rencana kerja berikutnya](#12-rencana-kerja-berikutnya)
13. [Catatan untuk melanjutkan pekerjaan](#13-catatan-untuk-melanjutkan-pekerjaan)

---

## 1. Gambaran singkat

Seluruh aplikasi berjalan di **Docker**, jadi PostgreSQL, Go, dan Node.js tidak perlu dipasang. Python hanya dibutuhkan untuk dua skrip data (bagian 3). Satu perintah menyalakan lima layanan:

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
| `backend` | Go (chi, pgx) | API, validasi, impor/ekspor CSV, query data warehouse, memicu pelatihan ulang | http://localhost:8080/api (port bisa diganti lewat `BACKEND_HOST_PORT`) |
| `ml` | Python (FastAPI, scikit-learn) | Melatih model, menghitung prediksi dan status | hanya di dalam Docker |
| `scraper` | Python (FastAPI, requests, pandas) | Mengambil harga harian SIMPANG secara otomatis tanpa duplikat | hanya di dalam Docker (status lewat `/api/scraper/status`) |
| `db` | PostgreSQL 16 | Menyimpan data harga, data warehouse, dan hasil model | `localhost:5432` (bisa diganti lewat `POSTGRES_HOST_PORT`) |

Tabel di database dibuat otomatis oleh backend (migrasi) saat pertama kali menyala.

### Perjalanan satu data baru

1. **Ambil.** Scraper membaca halaman peta harga SIMPANG.
2. **Arsip.** Data mentah disimpan ke `data/raw/otomatis/`, dan baris baru ditambahkan ke `master_data_harian.csv`. Master menyimpan **termasuk harga 0**.
3. **Bersihkan.** Aturan di `etl/aturan_bersih.py` dipakai. Harga 0 dibuang.
4. **Tahan.** Tanggal yang dilaporkan kurang dari 15 pasar belum diimpor.
5. **Impor.** Data dikirim lewat `POST /api/harga/import`.
6. **Simpan.** Data masuk tabel `harga`. Kunci unik mencegah duplikat.
7. **Warehouse.** Trigger `muat_warehouse()` memperbarui `fakta_harga` dan dimensinya.
8. **Versi.** `versi_data` naik, lalu backend memanggil `ml /retrain`.
9. **Latih ulang.** Layanan ML melatih ulang dan menulis tabel `prediksi`, `status_harga`, dan `evaluasi_model`.
10. **Tampil.** Frontend memantau `/api/status-hitung` dan memuat ulang halaman saat model selesai.

Data yang ditambah lewat halaman Kelola Data masuk mulai langkah 5.

---

## 2. Status progres

Status mengikuti komponen penilaian di panduan dosen (*Deskripsi Proyek Data Analitik & Data Science*).

### 2.1 Luaran utama

| Luaran | Keadaan | Status |
|---|---|---|
| Aplikasi di-deploy dan dapat diakses publik | Berjalan lengkap lewat Docker di laptop; **belum ada URL publik**. Panduan: aplikasi yang hanya berjalan di laptop tidak memenuhi syarat | Belum (R5) |
| Dua modul terhubung (Data Analitik dan Data Science) | Dashboard dan modul model membaca database yang sama | Selesai |

### 2.2 Data Analitik

| Komponen | Isi | Status |
|---|---|---|
| A1 Proposal | Pertanyaan analitik, 3 kelompok pengguna, KPI | Selesai |
| A2 Data dan kualitas | Master CSV 2 sumber, `etl_master.py`, `docs/kualitas_data.md` | Selesai |
| A3 Data warehouse dan ETL | Skema bintang (`fakta_harga` + 4 dimensi), ETL otomatis lewat trigger, `docs/warehouse.md` | Selesai |
| A4 Visualisasi dan dashboard | 7 halaman, 17 visual (6 jenis lanjutan), 4 KPI dengan pembanding, filter global, drill-down, cross-filter, `docs/visualisasi.md` | Selesai |
| A5 Storytelling | Halaman Cerita, 5 temuan dengan judul dinamis | Selesai |

### 2.3 Data Science

| Komponen | Isi | Status |
|---|---|---|
| S1 Problem framing | `docs/model/S1_problem_framing.md` | Selesai |
| S2 Preprocessing dan fitur | `docs/model/S2_feature_engineering.md`, `app/ml/app/fitur_global.py` | Selesai |
| S3 Pemodelan dan tuning | `docs/model/S3_pemodelan.md`, `s3_tuning.csv`, `s3_terpilih.json` | Selesai |
| S4 Evaluasi dan validasi | `docs/model/S4_evaluasi.md`, `s4_hasil_uji.csv`, `s4_keputusan.json` | Selesai |
| S5 Error analysis | Daftar kasus sudah ada (bagian 12) | **Berikutnya** |
| S6 Deployment model | Aplikasi **masih memakai model lama**; model S4 belum dipasang | Belum |
| S7 Reproducibility dan model card | README, tes, notebook dengan seed sudah ada; model card belum | Sebagian |

### 2.4 Pekerjaan lain yang sudah selesai

- **Scraper otomatis (P3–P6):**
  - layanan `scraper` dengan jadwal 10.00 dan 16.00 WIB;
  - proxy di backend (`/api/scraper/status`, `/api/scraper/jalankan`);
  - chip status di pojok kanan atas dan tab **Pengambilan otomatis** di Kelola Data;
  - layanan scraper di `docker-compose.yml`.
- **Data otomatis berjalan:** data sesudah 15 Oktober 2026 sudah masuk dari scraper.
- **Restrukturisasi berkas tanpa mengubah fungsi** (bagian 9.8): handler backend dipecah per fitur, header JSDoc di setiap halaman, dokumen redundan dihapus, `BACKEND_HOST_PORT`.
- `notebooks/pemodelan_lama.ipynb` sudah dihapus. Notebook yang dipakai hanya `notebooks/pemodelan.ipynb`.

### 2.5 Riwayat progres (urut waktu)

| Waktu (2026) | Tahap | Hasil |
|---|---|---|
| 21 Okt | Penetapan cakupan | Kota Medan, 21 kecamatan; stack React + Go + Python FastAPI + PostgreSQL lewat Docker Compose |
| 22 Okt | Data awal | Data SIMPANG (5 komoditas) masuk sebagai sumber |
| 2 Nov | Data gabungan | `master_data_harian.csv` gabungan SIMPANG 12 komoditas + SP2KP 2 komoditas; `etl_master.py`, `aturan_bersih.py` |
| s.d. 2 Nov | Aplikasi inti | 5 layanan Docker, warehouse skema bintang, 7 halaman dashboard, 17 visual, model lama per deret |
| awal Nov | P3 Scraper | Layanan `app/scraper/` (jadwal, rentang, tahan < 15 pasar, tanpa duplikat, riwayat), 34 tes lulus |
| awal Nov | P4 Backend | Proxy `/api/scraper/status` dan `/api/scraper/jalankan` (`app/backend/internal/handler/scraper.go`), `SCRAPER_URL` |
| awal Nov | P5 Frontend | Chip pengambilan data di header, tab Pengambilan otomatis di Kelola Data |
| awal Nov | P6 Compose | Layanan scraper di `docker-compose.yml`, `.env.example`, README; data otomatis masuk sampai 3 Nov |
| awal Nov | S1 | Problem framing dikunci (`docs/model/S1_problem_framing.md`) |
| awal Nov | S2 | `app/ml/app/fitur_global.py` + tes, 13 fitur terpilih |
| awal Nov | S3 | `app/ml/app/model_global.py`, `validasi_global.py`, tuning Optuna, LightGBM per kelompok terpilih; 31 tes ML lulus |
| s.d. 9 Nov | S4 | Evaluasi di data uji, `s4_hasil_uji.csv`, `s4_keputusan.json`; 32 tes ML lulus; `pemodelan_lama.ipynb` dihapus |
| 10 Nov | Cek database | Hasil scraping terbukti masuk PostgreSQL tanpa duplikat; rencana database bersama (Neon) dibahas, belum diputuskan |
| 11 Nov | Restrukturisasi | Handler backend dipecah per fitur, header JSDoc halaman, `BACKEND_HOST_PORT` (bagian 9.8); README diperbarui |

---

## 3. Yang perlu dipasang

| Alat | Untuk apa | Cek versi |
|---|---|---|
| **Git** | Mengambil kode dari GitHub | `git --version` |
| **Docker Desktop** | Menjalankan seluruh aplikasi | `docker --version` dan `docker compose version` |
| **Python 3.10 atau lebih baru** | Skrip data, tes, dan notebook | `python --version` |

Catatan:
- **Windows:** Docker Desktop butuh WSL 2. Buka Docker Desktop dulu dan tunggu status **"Engine running"** sebelum menjalankan perintah `docker`.
- Python hanya dipakai untuk skrip di `etl/`, tes, dan notebook. Untuk mengolah data mentah cukup `pip install pandas`.
- Go, Node.js, dan PostgreSQL **tidak** perlu dipasang, kecuali ingin mengembangkan kode tanpa Docker.
- Repo ini privat. Minta pemilik repo (Arjunamelix) menambahkan akun GitHub-mu sebagai kolaborator.

---

## 4. Menjalankan proyek (langkah demi langkah)

Semua perintah dijalankan di terminal (PowerShell di Windows, Terminal di macOS/Linux) dari **folder induk proyek**.

### Langkah 1. Ambil kode

```bash
git clone https://github.com/Arjunamelix/Dasi_Dalis_04.git
cd Dasi_Dalis_04
```

Kalau repo sudah ada di laptop, cukup `git pull`.

### Langkah 2. Buat berkas `.env`

Berkas `.env` berisi pengaturan dan **tidak ikut di-commit**. Setiap orang membuat sendiri.

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

Yang perlu diisi atau diperhatikan:

| Variabel | Isi |
|---|---|
| `POSTGRES_PASSWORD` | Password bebas. **Pakai huruf, angka, dan garis bawah saja.** Karakter `@ : / # %` merusak alamat koneksi database |
| `POSTGRES_HOST_PORT` | Isi `5440` kalau muncul galat port 5432 sudah dipakai |
| `BACKEND_HOST_PORT` | Ganti kalau port 8080 di laptop sudah dipakai program lain |
| `SCRAPER_KONTAK` | Email **tim** untuk User-Agent scraper (identitas saat menghubungi SIMPANG) |
| `SCRAPER_TULIS_MASTER` | `1` hanya untuk **satu** laptop yang meng-commit master CSV (saat ini laptop Arjuna). Laptop lain `0` |
| `SCRAPER_AKTIF` | `1` = jadwal otomatis menyala; `0` = mati (tombol "Ambil data sekarang" tetap bisa dipakai) |
| `SCRAPER_JADWAL` | Jam tarikan, bawaan `10:00,16:00` |
| `ML_MIN_HARI` | Minimal hari data asli per deret agar dimodelkan |

### Langkah 3. Nyalakan semua layanan

Pastikan Docker Desktop berjalan, lalu:

```bash
docker compose up --build -d
```

Pertama kali butuh sekitar **5–10 menit**. Setelahnya jauh lebih cepat.

### Langkah 4. Pastikan semuanya hidup

```bash
docker compose ps
```

Lima layanan (`db`, `backend`, `ml`, `scraper`, `frontend`) harus berstatus **Up**, dan `db` berstatus **healthy**. Lalu cek backend:

```bash
curl http://localhost:8080/api/health
```

Di PowerShell: `Invoke-RestMethod http://localhost:8080/api/health`. Hasilnya harus `{"status":"ok"}`.

### Langkah 5. Olah data mentah

Data mentah gabungan SIMPANG dan SP2KP ada di `data/raw/master_data_harian.csv`. Ubah ke format impor:

```bash
pip install pandas
python etl/etl_master.py
```

Di macOS/Linux pakai `python3`. Tanpa argumen, skrip membaca `data/raw/master_data_harian.csv` dan menulis ke `data/processed/`.

Angka di bawah dari master per **15 Oktober 2026**. Karena scraper menambah data setiap hari, angkamu akan sedikit lebih besar. Yang penting tidak ada galat.

| Keterangan | Jumlah |
|---|---|
| Baris mentah | 260.864 |
| Dibuang (harga 0 = tidak ada laporan hari itu) | 122.160 |
| Ditolak: telur dilaporkan per butir, bukan per kg | 3.763 |
| Ditolak: menyimpang > 40% dari median pasar lain hari itu | 1.600 |
| Ditolak: di luar batas wajar | 123 |
| **Baris valid** | **133.218** |

Hasilnya tiga berkas di `data/processed/`:
- `harga_harian_simpang.csv` (131.976 baris)
- `harga_harian_sp2kp.csv` (1.242 baris)
- `master_ditolak.csv` (baris yang dibuang beserta alasannya)

### Langkah 6. Impor data ke database

```bash
python etl/impor_csv.py data/processed/harga_harian_simpang.csv
python etl/impor_csv.py data/processed/harga_harian_sp2kp.csv
```

Hasil pada database kosong (master per 15 Oktober 2026):
- SIMPANG: `baru disimpan 131976 | dilewati (sudah ada) 0 | tidak valid 0`
- SP2KP: `baru disimpan 1242 | dilewati (sudah ada) 0 | tidak valid 0`

Perintah ini **aman diulang**: percobaan kedua menghasilkan `baru disimpan 0`, tanpa duplikat.

Peringatan "baris berubah harga > 50% (tetap disimpan)" itu wajar, kebanyakan dari cabai dan bawang merah.

### Langkah 7. Tunggu model selesai dilatih

Begitu data masuk, model dilatih otomatis di belakang layar, butuh **beberapa menit**. Pantau dengan:

```bash
curl http://localhost:8080/api/status-hitung
docker compose logs ml --tail 10
```

Tunggu sampai `status_hitung` menjadi `idle` dan `versi_model` sama dengan `versi_data`.

Beberapa deret memang dilewati karena datanya kurang (tercatat di tabel `deret_dilewati`). Itu bukan galat.

Kalau `status_hitung` bernilai `error`, baca `pesan_hitung` dan log ML, lalu picu ulang:

```bash
curl -X POST http://localhost:8080/api/retrain
```

### Langkah 8. Buka dashboard

**http://localhost:3000**

Mulai sekarang data baru masuk sendiri lewat layanan `scraper`. Langkah 5 dan 6 hanya perlu dijalankan sekali, saat database masih kosong.

> **Ringkasan cepat** (setelah `.env` dibuat dan Docker menyala):
> ```bash
> docker compose up --build -d
> pip install pandas
> python etl/etl_master.py
> python etl/impor_csv.py data/processed/harga_harian_simpang.csv
> python etl/impor_csv.py data/processed/harga_harian_sp2kp.csv
> ```
> Lalu tunggu model selesai dan buka http://localhost:3000.

---

## 5. Memakai dashboard

### 5.1 Halaman

| Halaman | Alamat | Isi |
|---|---|---|
| **Dashboard** | `/` | 4 kartu KPI dengan pembanding, kartu per komoditas (harga terakhir, perubahan 7 hari, prediksi 7 hari, status), grafik batang perubahan 7 hari. Pilih "KOTA MEDAN" atau satu kecamatan |
| **Tren** | `/tren` | Grafik garis harga (pilih komoditas, sampai 3 kecamatan, rentang waktu) dan peta choropleth 21 kecamatan |
| **Perbandingan** | `/perbandingan` | Harga 21 kecamatan untuk satu komoditas, terurut, dengan garis acuan harga Kota Medan dan tabel rincian |
| **Analisis** | `/analisis` | Analisis dari data warehouse dengan filter global: heatmap musiman, deret beranotasi, box plot, treemap (drill-down), small multiples, heatmap korelasi |
| **Cerita** | `/cerita` | Lima temuan utama dengan judul yang dihitung otomatis dari data |
| **Prediksi** | `/prediksi` | Prediksi 7 dan 14 hari dengan rentang 80%, status, evaluasi model dibanding baseline (masih model lama, lihat bagian 7.1) |
| **Kelola Data** | `/kelola` | Tab Tambah data (dengan prediksi sebelum dan sesudah), Daftar dan ubah, Impor/ekspor CSV, Pengambilan otomatis |

Elemen yang ada di semua halaman:
- **Chip pengambilan data** di kanan atas, misalnya "Diambil 10 Nov, 13.27". Klik untuk membuka tab Pengambilan otomatis.
- **Status model:** "Model terbaru" atau "Sedang menghitung ulang".
- **Pilihan filter tersimpan di alamat halaman**, misalnya `/tren?komoditas=cabai_merah`, sehingga tampilan bisa dibagikan.

### 5.2 Cara angka dihitung

- Harga **kecamatan** = rata-rata harga semua pasar di kecamatan itu pada hari itu.
- Harga **Kota Medan** = **median** harga semua pasar pada hari itu, minimal 3 pasar melapor.
- **8 kecamatan tampil "tidak ada data"** (Medan Amplas, Baru, Denai, Labuhan, Maimun, Polonia, Tembung, Timur), karena sumber data tidak punya pasar di sana. Tidak ada angka yang ditebak.
- **Garam halus dan susu bubuk** (SP2KP) hanya ada di 2 pasar, jadi tidak punya angka Kota Medan. Pilih kecamatan **Medan Area** atau **Medan Kota** untuk melihatnya.

### 5.3 Empat KPI di Dashboard

Dihitung dari data warehouse, fungsi `anKPI` di `app/backend/internal/handler/analitik_wh.go`.

| KPI | Cara hitung | Pembanding |
|---|---|---|
| Rata-rata perubahan harga 7 hari | Harga median kota terakhir vs sekitar 7 hari sebelumnya, dirata-rata semua komoditas | Minggu sebelumnya |
| Komoditas naik > 5% | Jumlah komoditas dengan perubahan 7 hari > 5% | Minggu sebelumnya |
| Selisih harga antarpasar | (termahal − termurah) / median per hari per komoditas (minimal 3 pasar), rata-rata 7 hari terakhir | Rata-rata 30 hari sebelumnya |
| Pasar melapor | Jumlah pasar berbeda pada tanggal terakhir | Rata-rata 30 hari laporan sebelumnya, target 21 |

### 5.4 Daftar 17 visual

| No | Halaman | Visual | Jenis |
|---|---|---|---|
| 1 | Dashboard | 4 kartu KPI dengan pembanding | kartu KPI |
| 2 | Dashboard | Perubahan harga 7 hari per komoditas | batang divergen |
| 3 | Tren | Tren harga sampai 3 kecamatan | garis |
| 4 | Tren | Peta harga 21 kecamatan | **peta choropleth** |
| 5 | Perbandingan | Harga 21 kecamatan dengan garis acuan kota | batang |
| 6 | Prediksi | Harga aktual, prediksi 7/14 hari, rentang 80% | garis + area |
| 7 | Analisis | Pola musiman komoditas × bulan | **heatmap** |
| 8 | Analisis | Harga harian dengan hari besar, celah, lonjakan | **deret waktu beranotasi** |
| 9 | Analisis | Sebaran harga antarpasar per bulan | **box plot** |
| 10 | Analisis | Kelengkapan laporan dan harga per wilayah | **treemap** (drill-down) |
| 11 | Analisis | Tren mingguan semua komoditas | **small multiples** |
| 12 | Analisis | Korelasi perubahan harga antarkomoditas | heatmap |
| 13 | Cerita | Menjelang hari besar vs hari biasa | batang berkelompok |
| 14 | Cerita | Volatilitas mingguan per komoditas | batang |
| 15 | Cerita | Selisih termahal–termurah antarpasar | batang |
| 16 | Cerita | Selisih tiap pasar terhadap median kota | batang divergen |
| 17 | Cerita | Akurasi model vs baseline per komoditas | batang berkelompok |

Aturan warna di semua grafik:
- **oranye** = naik atau lebih mahal;
- **biru** = turun, lebih murah, atau satu seri biasa;
- **abu** = pembanding atau data yang punya catatan kualitas.

Pengecualian: di grafik Tren, warna hanya membedakan wilayah. Rincian dan interaksi ada di `docs/visualisasi.md`.

### 5.5 Mencoba sifat dinamis

- Buka **Kelola Data**, tambahkan satu data harga, lalu lihat kartu prediksi berubah setelah model dihitung ulang.
- Atau buka tab **Pengambilan otomatis** dan tekan **Ambil data sekarang**.

---

## 6. Tentang data

### 6.1 Sumber dan isi

Semua data digabung dalam satu berkas mentah `data/raw/master_data_harian.csv`. Kolom `sumber` membedakan asalnya.

- Data sampai **15 Oktober 2026** adalah hasil scraping tim (260.864 baris).
- Sesudahnya, data **ditambah otomatis** oleh layanan `scraper`.

| Sumber | Pasar | Komoditas |
|---|---|---|
| **SIMPANG Pemko Medan** | 21 pasar di 13 kecamatan, harian sejak 1 Januari 2024 | Beras Medium, Bawang Merah, Bawang Putih, Cabai Merah, Cabai Rawit, Minyak Goreng Curah, Gula Pasir, Daging Sapi, Daging Ayam Ras, Telur Ayam Ras, Jagung, Kedelai |
| **SP2KP Kemendag** | Pasar Sukaramai dan Pusat Pasar | Garam Halus, Susu Bubuk |

- **Satu deret tidak pernah dicampur dari dua sumber.** Kolom `sumber` ikut disimpan di setiap baris.
- **Format impor** (6 kolom, urutan bebas): `tanggal, kecamatan, nama_pasar, komoditas, harga, sumber`. Contohnya di `data/template_import.csv`.
- **Master CSV menyimpan baris berharga 0** (pasar belum atau tidak melapor). Database hanya menerima harga > 0. Karena itu master bisa bertambah sementara database mencatat "baris baru 0". Itu normal.

### 6.2 Aturan pembersihan

Aturannya di `etl/aturan_bersih.py`, dipakai oleh `etl_master.py` dan scraper, dan dijalankan berurutan:

1. Nama komoditas, sumber, dan pasar dibakukan (mis. `pusat pasar` di SP2KP menjadi `Pusat Pasar`).
2. Komoditas yang isinya salinan persis komoditas lain dibuang otomatis (pernah terjadi: telur hasil scraping lama identik dengan daging sapi).
3. Harga 0 dianggap tidak ada data dan dibuang.
4. Harga telur yang dilaporkan **per butir** (SIMPANG, Januari 2024–Januari 2025) ditolak, tidak dikonversi. Deret telur dimulai Februari 2025.
5. Harga di luar batas wajar komoditas (`config/referensi.json`) ditolak.
6. Harga yang menyimpang lebih dari 40% dari median pasar lain pada hari, komoditas, dan sumber yang sama (bila minimal 5 pasar melapor) ditolak sebagai dugaan salah input.

Laporan kualitas sebelum dan sesudah pembersihan ada di `docs/kualitas_data.md` (dibuat oleh `etl/laporan_kualitas.py`). Contohnya, kelengkapan naik dari 53,2% menjadi 100%, dan ejaan nama pasar dari 23 menjadi 21 nama baku.

### 6.3 Batasan data

- Ada lubang data, terutama Mei sampai Juli 2024. Sabtu dan Minggu tidak berisi harga di SIMPANG.
- 8 dari 21 kecamatan tidak punya data.
- Sebagian pasar melaporkan harga jagung jauh di atas pasar lain (kemungkinan jenisnya berbeda). Kedelai juga konsisten berbeda per pasar. Keduanya ditandai abu di halaman Cerita.
- Beberapa deret berhenti melapor sebelum Oktober 2026 (garam dan susu di Pasar Sukaramai, kedelai di Medan Area).
- Jenis beras (medium) dan satuan susu bubuk (kemasan 400 g) masih asumsi yang perlu dikonfirmasi.
- Kemungkinan anomali bawang merah 6 September 2024 (kejadian serentak di banyak pasar), diperiksa di S5.

Data sintetis (`python etl/gen_data_dev.py`) hanya untuk menguji aplikasi dan **tidak boleh dipakai di laporan**.

### 6.4 Data baru otomatis (layanan `scraper`)

- **Kapan:**
  - saat layanan menyala (dilewati bila tarikan sukses terakhir kurang dari 3 jam lalu);
  - setiap hari pukul 10.00 dan 16.00 WIB (`SCRAPER_JADWAL`);
  - kapan saja lewat tombol **Ambil data sekarang** di Kelola Data.
- **Apa yang diambil:** 12 komoditas di 21 pasar dari halaman peta harga SIMPANG (`?menu=peta`), satu permintaan per komoditas per tanggal.
  - Rentangnya dari 7 hari sebelum tanggal terakhir di database sampai hari ini, supaya harga yang diunggah terlambat ikut terisi.
  - SP2KP belum diambil otomatis karena ID pasar SP2KP belum lengkap.
- **Alur:** ambil → simpan mentah ke `data/raw/otomatis/` → tambahkan ke `master_data_harian.csv` → bersihkan dengan `etl/aturan_bersih.py` → impor lewat backend → model dilatih ulang otomatis.
- **Tanpa duplikat:** master dan database memakai kunci yang sama (`tanggal, kecamatan, nama_pasar, komoditas, sumber`). Harga yang tadinya 0 lalu diunggah belakangan akan diisi (`diisi_dari_0`).
- **Hari belum lengkap ditahan:** tanggal dengan kurang dari 15 pasar melapor tidak diimpor dulu, dan diimpor di tarikan berikutnya.
- **Etika akses:**
  - robots.txt SIMPANG mengizinkan akses (`Allow: /`);
  - User-Agent jujur (nama proyek dan `SCRAPER_KONTAK`);
  - jeda 2 detik antarpermintaan;
  - **berhenti** bila server menolak (HTTP 403/429/503) atau menampilkan halaman tantangan;
  - tidak ada upaya melewati proteksi apa pun.
- **Riwayat tarikan:** `data/raw/otomatis/riwayat_tarikan.jsonl`, ditampilkan di tab Pengambilan otomatis. Rincian tarikan terakhir bisa dilihat dengan:

  ```powershell
  $s = Invoke-RestMethod http://localhost:8080/api/scraper/status
  $s.terakhir.sumber.simpang | Select-Object master, bersih, impor, ditahan, tanggal_berdata | ConvertTo-Json -Depth 4
  ```

  Arti angkanya:
  - `master.ditambahkan` = baris baru di master (termasuk harga 0);
  - `bersih.harga_0` = baris harga 0 yang dibuang;
  - `impor.disisipkan` = baris yang benar-benar baru masuk database;
  - `impor.dilewati_sudah_ada` = baris yang sudah ada.

- **Tanpa Docker** (menguji satu tarikan dari terminal, dari folder induk):

  ```powershell
  pip install fastapi "uvicorn[standard]" requests tzdata pandas
  $env:PYTHONPATH="app/scraper"; $env:BACKEND_URL="http://localhost:8080"; $env:SCRIPTS_DIR="scripts"; $env:DATA_DIR="data"
  python -m app.cli --dry-run     # ambil dan bersihkan saja, tidak mengubah apa pun
  python -m app.cli               # tarikan penuh
  ```

---

## 7. Pemodelan (Data Science)

Ada dua hal yang perlu dibedakan:
- **7.1** model yang **sedang berjalan di aplikasi** (model lama);
- **7.2** model hasil **pemodelan ulang S1–S4** di notebook, yang akan dipasang ke aplikasi di S6.

### 7.1 Model yang berjalan di aplikasi sekarang (model lama)

| Bagian | Cara kerja | Berkas |
|---|---|---|
| Deret | Satu deret = satu komoditas di satu wilayah (Kota Medan atau kecamatan) dari satu sumber. Sekitar 171 deret; deret dengan data asli kurang dari `ML_MIN_HARI` dilewati | `app/ml/app/pipeline.py` |
| Fitur | Perubahan harga 1, 3, 7, 14, 28 hari; rasio terhadap rata-rata 30 dan 90 hari; volatilitas 14 hari; hari besar dan bulan tanggal target | `app/ml/app/fitur.py`, `kalender.py` |
| Target | y = ln(harga h hari lagi) − ln(harga hari ini), h = 7 dan 14; dikembalikan ke rupiah | `fitur.py` |
| Model | `GradientBoostingRegressor` **satu per deret** (120 pohon, kedalaman 3); baseline naif = harga hari ini | `app/ml/app/model.py` |
| Evaluasi | Walk-forward pada hari uji terakhir; MAE, RMSE, MAPE dibanding baseline | `app/ml/app/evaluasi.py` |
| Rentang 80% | Persentil 10 dan 90 galat uji walk-forward | `pipeline.py` |
| Status | Ambang per komoditas dari kenaikan 7 hari historis: Waspada = persentil 80 (minimal 2%), Lonjakan = persentil 95. Hanya dari kenaikan yang **diprediksi** | `app/ml/app/status.py` |

Hasilnya lemah. Model lama hanya mengalahkan baseline naif di **7 dari 171 deret** (temuan 5 halaman Cerita), dan di data uji S4 secara keseluruhan **19,8% lebih buruk** dari naif. Karena itu pemodelan diulang.

### 7.2 Pemodelan ulang S1–S4

Kode dan grafik ada di `notebooks/pemodelan.ipynb`, ringkasan per tahap di `docs/model/`. Notebook hanya memakai data sampai **15 Oktober 2026**.

**S1 Problem framing** (`S1_problem_framing.md`)
- Regresi perubahan log harga 7 dan 14 hari, dengan **satu model gabungan** untuk semua deret.
- Komoditas dibagi dua kelompok:
  - **bergejolak:** cabai merah, cabai rawit, bawang merah, daging ayam ras, bawang putih;
  - **stabil:** sisanya.
- Pembagian data menurut waktu:
  - latih: target ≤ 31 Maret 2026;
  - validasi: April–Juni 2026;
  - uji: hari asal 1 Juli–15 Oktober 2026.
- Baseline: naif "harga tetap". Baseline wajib panduan: Linear Regression.
- Kriteria sukses, aturan status S1.7 (status = yang lebih tinggi dari kelas perubahan aktual 7 hari terakhir dan kelas prediksi), dan **aturan cadangan** ("bila kriteria minimum tidak tercapai pada satu kelompok, aplikasi memakai baseline naif untuk kelompok itu") ditetapkan **sebelum** data uji dibuka.

**S2 Preprocessing dan fitur** (`S2_feature_engineering.md`, `app/ml/app/fitur_global.py`)
- 25 fitur kandidat dalam 5 kelompok.
- Ablation dan permutation importance menyisakan **13 fitur** (`FITUR_TERPILIH`): `komoditas_kode, bergejolak, tingkat_kota, ret_3, ret_14, rasio_ma30, rasio_ma365, frac_berubah_28, hari_sejak_berubah, n_pasar, dispersi, selisih_kota, ret_7_kota`.
- Fitur pasar dan wilayah paling penting. Fitur kalender dikeluarkan karena tidak membantu.
- Tes kebocoran lulus.

**S3 Pemodelan dan tuning** (`S3_pemodelan.md`, `app/ml/app/model_global.py`, `validasi_global.py`)
- Algoritma: Linear Regression, Ridge, Random Forest, HistGradientBoosting, LightGBM.
- Tuning: Optuna (TPE, seed 42), 210 percobaan, validasi silang 4 lipatan waktu (Jul–Sep 2025, Okt–Des 2025, Jan–Mar 2026, Apr–Jun 2026). Semua percobaan di `s3_tuning.csv`.
- Strategi untuk komoditas stabil yang diuji: per kelompok, penyusutan prediksi kecil ke 0, naif untuk stabil.
- Terpilih: **LightGBM loss L1, model terpisah per kelompok** (`s3_terpilih.json`):
  - h7: learning_rate 0,0109; n_estimators 450; num_leaves 18; min_child_samples 23; subsample 0,72; colsample 0,98; reg_lambda 0,019;
  - h14: learning_rate 0,0118; n_estimators 250; num_leaves 8; min_child_samples 181; subsample 0,83; colsample 0,94; reg_lambda 0,0011.

**S4 Evaluasi di data uji** (`S4_evaluasi.md`, `s4_hasil_uji.csv`). Data uji dipakai satu kali. Angka di bawah adalah selisih MAE terhadap naif (negatif = lebih baik):

| Model | h7 bergejolak | h7 stabil | h7 semua | h14 semua |
|---|---|---|---|---|
| Model lama | +12,9% | +74,8% | +19,8% | +17,8% |
| Linear Regression | +2,5% | +85,9% | +11,8% | +11,6% |
| Ridge | +2,3% | +84,5% | +11,5% | +11,2% |
| Random Forest + penyusutan | −0,1% | −3,6% | −0,5% | +5,4% |
| HistGradientBoosting + penyusutan | −0,7% | 0,0% | −0,6% | +1,5% |
| LightGBM gabungan | −0,4% | −0,1% | −0,4% | +2,4% |
| **LightGBM per kelompok (terpilih)** | **+2,7%** | **−9,1%** | +1,4% | +2,4% |
| **Aplikasi (keputusan S4)** | 0,0% | −9,1% | **−1,0%** | **0,0%** |

Hasil pendukung:
- **Interval kepercayaan 90%** (bootstrap per deret, 1.000 kali):
  - bergejolak h7 +0,1 s.d. +5,6;
  - stabil h7 −13,5 s.d. −2,8.
- **Per deret:** model terpilih menang di 73 dari 165 deret (h7); model lama hanya 11.
- **Status (h7):** recall 0,270, presisi 0,243, F1 0,256, di atas aturan persistensi (0,202 / 0,206).
- **Cakupan rentang 80%:** bergejolak 81–84%, stabil 77%.

**Keputusan untuk aplikasi** (`s4_keputusan.json`, dipakai S6):
- **Stabil:** prediksi LightGBM kelompok stabil.
- **Bergejolak:** prediksi titik naif (harga tetap) dengan rentang dari sebaran perubahan historis (h7: −12,5% s.d. +16,7%).
- **Status:** aturan S1.7 (perubahan aktual ATAU prediksi model terpilih).
- Model **tidak dipilih ulang** berdasarkan data uji.
- Validasi silang terbukti optimistis untuk bergejolak (−3,1% menjadi +2,7%).

---

## 8. Database, data warehouse, dan kerja tim

### 8.1 Lapisan operasional (migrasi 000001 dan 000002)

| Tabel / view | Isi | Ditulis oleh |
|---|---|---|
| `harga` | Data harga asli per pasar; kunci unik `(tanggal, kecamatan, nama_pasar, komoditas, sumber)`; `CHECK (harga > 0)` | backend |
| `harga_agregat` (view) | Rata-rata kecamatan dan median kota (minimal 3 pasar) per hari | otomatis |
| `meta` | `versi_data`, `versi_model`, status pelatihan | backend, ml |
| `prediksi`, `status_harga`, `evaluasi_model`, `evaluasi_status`, `deret_dilewati` | Hasil model | ml |

### 8.2 Data warehouse skema bintang (migrasi 000003)

- **Fakta:** `fakta_harga`. Grain: satu harga satu komoditas di satu pasar pada satu tanggal dari satu sumber. Ukurannya: harga, perubahan harian dan 7 hari, rata-rata bergerak 7 dan 30 hari, median kota, selisih terhadap median kota, jumlah pasar melapor.
- **Dimensi:** `dim_waktu`, `dim_wilayah` (kota → kecamatan → pasar), `dim_komoditas`, `dim_sumber`.
- **ETL otomatis:** empat trigger pada tabel `harga` (tambah, ubah, hapus, kosongkan) memanggil `muat_warehouse()` untuk komoditas yang berubah.
- **Tampilan datar** `v_dataset_harga` (30 kolom) untuk EDA, ekspor, atau Tableau.
- Rincian dan contoh query ada di `docs/warehouse.md`.

### 8.3 Memeriksa isi database

Ganti `pangan` / `harga_pangan` bila `.env` berbeda.

```powershell
docker compose exec db psql -U pangan -d harga_pangan -c "SELECT sumber, count(*), min(tanggal), max(tanggal) FROM harga GROUP BY sumber;"
docker compose exec db psql -U pangan -d harga_pangan -c "SELECT dibuat_pada::date AS masuk, count(*) FROM harga GROUP BY 1 ORDER BY 1 DESC LIMIT 5;"
docker compose exec db psql -U pangan -d harga_pangan -c "SELECT (SELECT count(*) FROM harga) AS harga, (SELECT count(*) FROM fakta_harga) AS fakta;"
docker compose exec db psql -U pangan -d harga_pangan -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS ukuran;"
```

### 8.4 Kerja tim dan berbagi data

- **Keadaan sekarang:** setiap laptop punya PostgreSQL sendiri (volume Docker `pgdata`). Data dibagikan lewat `master_data_harian.csv` di GitHub.
- **Hanya satu laptop** yang memakai `SCRAPER_TULIS_MASTER=1` dan meng-commit master. Saat ini laptop Arjuna.
- **Laptop lain:** `git pull`, lalu jalankan langkah 5 dan 6 untuk menyamakan database tanpa scraping.
- **Rencana yang dibahas (belum diputuskan): satu database bersama di PostgreSQL online Neon** (gratis 1 GB). Hanya laptop penulis (scraper + ml) yang menulis; laptop lain cukup menjalankan `backend` dan `frontend`. Langkahnya:
  - **N1:** cek ukuran database;
  - **N2:** buat project Neon region Singapore, pakai alamat koneksi **non-pooled**;
  - **N3:** `DATABASE_URL` di `docker-compose.yml` bisa diisi dari `.env`, dengan database lokal sebagai cadangan;
  - **N4:** pindahkan isi database dengan `pg_dump` / `pg_restore`;
  - **N5:** rekan menyambung dan mengecek dashboard sama.

  Database bersama ini dipakai juga saat deploy (R5).

---

## 9. Struktur proyek

Lima layanan aplikasi (`frontend`, `backend`, `ml`, `scraper`, `db`) dijalankan oleh `docker-compose.yml`. Folder `config/`, `data/`, `etl/`, `notebooks/`, dan `docs/` berisi referensi, data, skrip olah data, eksperimen model, dan dokumentasi.

| Folder | Isi | Dipakai oleh |
|---|---|---|
| `app/frontend/` | Dashboard web (React + Vite, disajikan nginx) | layanan `frontend` |
| `app/backend/` | API, validasi, impor/ekspor CSV, data warehouse, pemicu pelatihan ulang (Go) | layanan `backend` |
| `app/ml/` | Pelatihan model, prediksi, status harga (Python FastAPI) | layanan `ml` |
| `app/scraper/` | Pengambilan data harga otomatis dari SIMPANG (Python FastAPI) | layanan `scraper` |
| `config/` | Referensi kecamatan, pasar, komoditas, dan batas harga | `backend`, `ml`, `scripts` |
| `data/` | Data mentah, data bersih hasil ETL, data uji | `scripts`, `notebooks` |
| `etl/` | Skrip olah data yang dijalankan manual, dan aturan pembersihan bersama | pengguna, `scraper` |
| `notebooks/` | Notebook pemodelan | pengguna (Jupyter / VS Code) |
| `docs/` | Dokumentasi data, aplikasi, model, laporan, logbook | pengguna, dosen |

Padanan dengan struktur yang diminta panduan (bagian 6), tanpa mengubah folder:

| Diminta panduan | Padanan di repo |
|---|---|
| `data/` | `data/` |
| `etl/` | `etl/` (`etl_master.py`, `aturan_bersih.py`, `impor_csv.py`) dan `app/backend/migrations/000003_warehouse.up.sql` |
| `notebooks/` | `notebooks/pemodelan.ipynb` |
| `app/` | `app/frontend/`, `app/backend/`, `app/ml/`, `app/scraper/` |
| `models/` | **Belum ada**; dibuat di S6 untuk berkas model joblib |

### 9.1 Berkas di folder induk

```
Dasi_Dalis_04/
├── README.md               panduan menjalankan proyek (dokumen ini)
├── Project.md              keputusan, status, dan rencana kerja proyek
├── docker-compose.yml      menjalankan db + backend + ml + scraper + frontend
├── .env.example            contoh pengaturan; salin menjadi .env (tidak ikut di-commit)
├── .gitignore              daftar berkas yang tidak ikut di-commit (.env, node_modules, .venv, data/processed, data/dev, data/raw/otomatis)
├── .vscode/settings.json   pengaturan VS Code: folder etl/ dikenali Pylance
└── Makefile                pintasan perintah (macOS/Linux)
```

### 9.2 `app/frontend/` (dashboard)

```
app/frontend/
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

### 9.3 `app/backend/` (API Go)

```
app/backend/
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
│   │   ├── handler.go      perakitan router dan middleware HTTP /api
│   │   ├── harga.go        CRUD data harga, impor, ekspor, dan template CSV
│   │   ├── ringkasan.go    ringkasan kartu metrik dashboard utama
│   │   ├── tren.go         deret waktu harga untuk grafik halaman tren
│   │   ├── perbandingan.go perbandingan harga komoditas antar-kecamatan
│   │   ├── prediksi.go     prediksi harga, status, evaluasi, dan picu retrain ML
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

### 9.4 `app/ml/` (layanan model)

```
app/ml/
├── Dockerfile              image Python untuk layanan ML
├── requirements.txt        paket Python
├── app/
│   ├── main.py             API FastAPI: /health, /retrain, pelatihan ulang di latar belakang
│   ├── pipeline.py         alur lengkap: baca data, fitur, latih, evaluasi, tulis hasil
│   ├── fitur.py            deret harian dan fitur model (model per deret yang sedang berjalan)
│   ├── fitur_global.py     fitur model gabungan hasil S2 (dipakai notebook, dan aplikasi mulai S6)
│   ├── model.py            baseline naif dan model boosting (model per deret yang sedang berjalan)
│   ├── model_global.py     pembangun model gabungan S3–S4: Linear Regression, Ridge, Random Forest, HistGradientBoosting, LightGBM
│   ├── validasi_global.py  validasi silang 4 lipatan waktu untuk model gabungan
│   ├── evaluasi.py         evaluasi walk-forward: MAE, RMSE, MAPE vs baseline
│   ├── status.py           status Normal / Waspada / Lonjakan dan evaluasinya
│   ├── kalender.py         daftar hari besar dan periode Ramadan (ketetapan pemerintah)
│   ├── db.py               baca tabel harga, tulis tabel hasil model
│   └── config.py           pengaturan dari variabel lingkungan (ML_*)
└── tests/
    ├── conftest.py               data uji sintetis
    ├── test_fitur.py
    ├── test_fitur_global.py      termasuk cek tanpa kebocoran data
    ├── test_model_global.py
    ├── test_evaluasi_status.py
    └── test_pipeline_api.py
```

### 9.5 `app/scraper/` (layanan pengambil data)

```
app/scraper/
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

### 9.6 `config/`, `data/`, `etl/`, `notebooks/`

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

etl/
├── etl_master.py           ETL utama: master_data_harian.csv → data/processed/
├── aturan_bersih.py        aturan pembersihan dan penggabungan ke master, dipakai etl_master.py dan scraper
├── test_aturan_bersih.py   tes aturan_bersih.py
├── impor_csv.py            kirim CSV hasil ETL ke backend (POST /api/harga/import)
├── laporan_kualitas.py     buat docs/kualitas_data.md (kualitas data sebelum dan sesudah)
├── cek_akses_simpang.py    cek sekali apakah halaman SIMPANG dapat diakses
├── etl_simpang.py          ETL lama khusus data SIMPANG 5 komoditas (arsip)
└── gen_data_dev.py         pembuat data sintetis uji

notebooks/
└── pemodelan.ipynb         eksperimen pemodelan, disusun bertahap per komponen penilaian (S1 sampai S4 sudah ada)
```

### 9.7 `docs/` (dokumentasi)

```
docs/
├── kontrak_api.md          daftar endpoint API dan formatnya
├── kualitas_data.md        laporan kualitas data sebelum dan sesudah pembersihan (dibuat laporan_kualitas.py)
├── warehouse.md            skema bintang, ERD, contoh query
├── visualisasi.md          daftar visual dan interaktivitas dashboard
├── logbook.md              catatan kerja mingguan
├── model/
│   ├── S1_problem_framing.md       ringkasan problem framing (S1)
│   ├── S2_feature_engineering.md   ringkasan preprocessing dan feature engineering (S2)
│   ├── S3_pemodelan.md             ringkasan pemodelan, tuning, dan pemilihan model (S3)
│   ├── s3_tuning.csv               semua percobaan tuning Optuna (S3)
│   ├── s3_terpilih.json            konfigurasi model terpilih (dipakai S4 dan S6)
│   ├── S4_evaluasi.md              ringkasan evaluasi di data uji (S4)
│   ├── s4_hasil_uji.csv            metrik semua model di data uji
│   └── s4_keputusan.json           keputusan untuk aplikasi: model per kelompok, status, rentang 80% (dipakai S6)
└── laporan/                laporan akhir dan bahan presentasi
```

### 9.8 Catatan Pembaruan Struktur (Before vs After)

Untuk meningkatkan kemudahan navigasi, kejelasan kode, dan keterbacaan proyek bagi seluruh anggota tim, telah dilakukan restrukturisasi berkas tanpa mengubah satupun fungsi, kontrak API, maupun logika komputasi yang ada:

| Komponen | Sebelum Pembaruan (Before) | Sesudah Pembaruan (After) | Alasan & Manfaat |
|---|---|---|---|
| **Backend Handler** | Semua rute dan handler API (`/harga`, `/ringkasan`, `/tren`, `/perbandingan`, `/prediksi`, `/status`, `/retrain`) menumpuk di **satu file tunggal** `handler.go` (404 baris). | Dipecah menjadi berkas modular per fitur: `harga.go`, `ringkasan.go`, `tren.go`, `perbandingan.go`, `prediksi.go`, dan `handler.go` (khusus routing). | Saat ingin mengubah logika fitur tertentu (misal: tren), anggota tim langsung menuju `tren.go` tanpa perlu scroll file panjang. Semuanya tetap di `package handler` sehingga bebas error import. |
| **Dokumentasi Frontend** | File halaman di `app/frontend/src/pages/` langsung dimulai dengan kode tanpa keterangan tujuan halaman. | Setiap file halaman (`Dashboard.jsx`, `Tren.jsx`, `Perbandingan.jsx`, `Prediksi.jsx`, `KelolaData.jsx`, `Analisis.jsx`, `Cerita.jsx`) dilengkapi header JSDoc standar. | Anggota tim langsung paham fungsi halaman, komponen UI yang dipakai, dan endpoint API backend yang dihubungi saat membuka file. |
| **Dokumentasi Redundan** | Ada file `docs/PANDUAN_SETUP.md` (isinya duplikat `README.md`), serta `docs/alur_data_dev.md` & `docs/hasil_cek_sumber.md` (catatan hari pertama yang sudah usang). | File redundan dihapus; seluruh panduan setup dipusatkan di `README.md`, dan kualitas data dipusatkan di `docs/kualitas_data.md`. | Mengurangi kebingungan panduan mana yang harus diikuti (*single source of truth*). |
| **Kebersihan Git & Cache** | Folder build `app/frontend/dist/` dan cache `app/ml/.pytest_cache/` sempat tertinggal di lokal. | Dibersihkan dari disk lokal dan ditambahkan ke `.gitignore`. | Menghindari commit berkas sampah build yang bisa memperberat ukuran repositori. |
| **Fleksibilitas Port Backend** | Port backend di `docker-compose.yml` terkunci di `127.0.0.1:8080:8080`. | Menggunakan `127.0.0.1:${BACKEND_HOST_PORT:-8080}:8080`. | Anggota tim bawaan tetap memakai port `8080`, namun bagi anggota tim yang memiliki konflik port lokal (misalnya servis bawaan laptop di 8080) dapat mengatur `BACKEND_HOST_PORT` di `.env` tanpa mengubah git. |

---

## 10. Menjalankan tes

Tes **tidak** berjalan di Docker; butuh alat masing-masing di laptop.

| Bagian | Syarat | Perintah | Hasil yang benar |
|---|---|---|---|
| Frontend | Node.js 20+ | `cd app/frontend && npm install && npm test` | semua lulus |
| ML | Python 3.10+ | `cd app/ml`, buat dan aktifkan venv, `pip install -r requirements.txt`, `pytest` | **32 lulus** (tes LightGBM dilewati bila paket `lightgbm` belum dipasang) |
| Backend | Go 1.25+ | `cd app/backend && go mod tidy && go vet ./... && go test ./...` | semua lulus |
| Scraper | Python 3.10+ | dari folder induk: `pip install -r app/scraper/requirements.txt`, lalu `python -m pytest app/scraper/tests -q` | **34 lulus** |
| Aturan bersih | Python 3.10+ | dari folder induk: `python -m pytest etl/test_aturan_bersih.py -q` | **9 lulus** |

Aktivasi venv: Windows `.\.venv\Scripts\Activate.ps1`; macOS/Linux `source .venv/bin/activate`.

**Notebook** `notebooks/pemodelan.ipynb`:
- memakai venv ML yang sama ditambah `pip install matplotlib ipykernel lightgbm optuna`;
- buka di VS Code, pilih kernel `app\ml\.venv`, lalu **Run All** (sekitar 10–15 menit);
- tuning S3 tidak dijalankan ulang (hasilnya dibaca dari `docs/model/s3_tuning.csv`) kecuali `JALANKAN_TUNING = True`, yang menambah sekitar 30–40 menit.

---

## 11. Masalah umum dan solusinya

| Gejala | Penyebab | Solusi |
|---|---|---|
| Galat port 5432 atau 8080 sudah dipakai | Program lain di laptop | `POSTGRES_HOST_PORT=5440` atau `BACKEND_HOST_PORT=...` di `.env` |
| `docker` galat / tidak terhubung | Docker Desktop belum menyala | Buka Docker Desktop, tunggu "Engine running" |
| Scraper dry-run: backend tidak terjangkau (localhost:8080) | Layanan Docker belum menyala | `docker compose up -d` |
| Chip scraper menampilkan galat 503 | Layanan scraper mati | `docker compose logs scraper --tail 30`, lalu `docker compose up -d scraper` |
| 409 saat menekan Ambil data sekarang | Tarikan lain sedang berjalan | Tunggu sampai selesai |
| Master CSV bertambah, database "baris baru 0" | Baris harga 0 (pasar belum mengunggah) | Normal; tarikan berikutnya mengisinya |
| Peringatan git "LF will be replaced by CRLF" pada master CSV | Scraper (Linux) menulis LF, git di Windows memakai CRLF | Tidak merusak data. Tambahkan `.gitattributes` berisi `*.csv text eol=lf` |
| `git pull` bentrok di master CSV | Lebih dari satu laptop menulis master | Hanya satu laptop `SCRAPER_TULIS_MASTER=1` |
| Pylance: import `aturan_bersih` atau `app` tidak dikenali | VS Code tidak tahu folder `etl/` dan `app/ml/` | `.vscode/settings.json` berisi `"python.analysis.extraPaths": ["scripts", "ml"]`, lalu Reload Window |
| pytest: `import file mismatch` | Sisa cache dari berkas yang dipindah | Hapus `__pycache__` dan `.pytest_cache` |
| Jumlah tes lulus kurang / tes tidak ditemukan | Berkas tes tersimpan di folder salah (mis. di `app/ml/app`) | Pindahkan ke `app/ml/tests/` |
| `status_hitung` = `error` | Galat saat melatih | Baca `pesan_hitung` dan `docker compose logs ml`, lalu `POST /api/retrain` |
| Peta Tren tidak tampil | API key Google Maps atau koneksi ke Google | Cek koneksi; key ada di `app/frontend/src/components/PetaMedan.jsx` (lihat bagian 12) |
| Berkas `.ipynb` / `.jsx` gagal dipratinjau saat dikirim lewat chat | Batasan pratinjau | Unduh berkasnya, atau minta salinan `.txt` |

---

## 12. Rencana kerja berikutnya

Urutan yang disarankan (paling berpengaruh ke nilai lebih dulu). Penanda R1–R7 adalah urutan kerja tim; S1–S7 komponen penilaian Data Science.

### 12.1 S5: Error analysis (berikutnya)
- Kenapa cabai rawit paling memburuk (+10% vs naif) dan beras +13% (walau MAPE tetap 0,42%).
- Periode Agustus–September 2026: bergejolak +7% vs naif; Oktober −11%.
- Lipatan Juli–September 2025 juga lebih buruk dari naif: apakah Juli–September memang sulit diprediksi?
- Jagung (harga janggal di sebagian pasar) dan bawang merah 6 September 2024 (kejadian serentak).
- Uji tambahan dengan data **sesudah 15 Oktober 2026** dari scraper, untuk melihat apakah hasil S4 konsisten.
- Hasil S5 bisa menjadi temuan ke-6 di halaman Cerita (kontribusi sisi Data Analitik).

### 12.2 S6: Pasang model baru ke aplikasi
- Layanan `ml` memakai `fitur_global.py` + `model_global.py` sesuai `s4_keputusan.json`:
  - stabil = LightGBM;
  - bergejolak = naif + rentang historis;
  - status = aturan S1.7;
  - rentang 80%.
- Simpan model dengan **joblib** di folder `models/` (syarat panduan).
- Tambah `lightgbm` ke `app/ml/requirements.txt`, dan pasang `libgomp1` di `app/ml/Dockerfile`.
- Halaman Prediksi menampilkan **perbandingan beberapa model**, grafik **aktual vs prediksi**, dan **residual** (syarat modul modelling di panduan bagian 2).
- **Perbaiki panel sebelum–sesudah** di Kelola Data. Sekarang panel mencari prediksi deret **pasar**, padahal model hanya untuk kecamatan dan Kota Medan, sehingga selalu tampil "belum ada". Panel seharusnya menampilkan deret kecamatan pasar itu dan Kota Medan (`app/backend/internal/service/service.go`, fungsi `Tambah` dan `kunciInput`).
- Perbarui temuan 5 di halaman Cerita dan evaluasi di halaman Prediksi agar memakai model baru.
- Pertimbangkan rentang 80% komoditas stabil: hasilnya sangat sempit (mis. jagung Rp8.974–Rp8.976) karena sebagian besar galat nol.

### 12.3 S7: Reproducibility dan model card
- Model card 1–2 halaman: tujuan, data, metrik, batasan, bias.
- Cek ulang notebook bisa dijalankan dari awal oleh anggota lain.

### 12.4 Perbaikan kecil sebelum demo
- `Perbandingan.jsx`: label "Rata-rata Kota Medan" diganti "Harga Kota Medan (median)" (kartu dan `ReferenceLine`), dan tambahkan `interval={0}` pada `<YAxis>` supaya semua nama kecamatan tampil.
- Pindahkan API key Google Maps dari `PetaMedan.jsx` ke `VITE_GOOGLE_MAPS_API_KEY` di `.env` dan batasi ke domain aplikasi sebelum deploy.
- Tambahkan `.gitattributes` (`*.csv text eol=lf`).
- SP2KP otomatis: menunggu ID pasar Sukaramai dan Pusat Pasar.

### 12.5 R5–R6
- **R5 Deploy publik:** server atau layanan hosting, database bersama (Neon), HTTPS, `CORS_ORIGIN`, API key Maps dibatasi.
- **R6 Uji kegunaan** dengan 3–5 calon pengguna.

---

## 13. Catatan untuk melanjutkan pekerjaan

Bagian ini untuk siapa pun yang melanjutkan, termasuk sesi percakapan berikutnya dengan asisten AI.

### 13.1 Keputusan yang sudah dikunci (jangan diubah tanpa diskusi)
- Cakupan: Kota Medan, 21 kecamatan, 14 komoditas, data mulai 2 Januari 2024.
- Harga kota = median pasar (minimal 3), kecamatan = rata-rata pasar.
- Pemodelan memakai potret data sampai **15 Oktober 2026**. `CELAH_MAKS = 14` dikunci di notebook.
- Data uji S4 **sudah dipakai sekali**. Jangan memilih ulang model berdasarkan data uji.
- Keputusan aplikasi di `docs/model/s4_keputusan.json`: stabil = LightGBM, bergejolak = naif + rentang, status = aturan S1.7.
- Struktur folder repo tidak dipindah atau dirombak (padanan dengan panduan ada di bagian 9).

### 13.2 Aturan kerja
- `.env` **tidak pernah di-commit**.
- Scraper **tidak boleh** dibuat melewati proteksi anti-bot (Cloudflare/Turnstile dan sejenisnya). Bila sumber menolak, scraper berhenti.
- User-Agent memakai `SCRAPER_KONTAK` (email tim); jangan menulis email pribadi langsung di kode.
- `data/raw/otomatis/` dan `data/processed/` tidak di-commit.
- Hanya satu laptop yang meng-commit master CSV.
- Berkas scraper atau skrip pihak lain di luar repo (mis. `scraper_simpang.py`, `pipeline_update_data.py`, `setup_task_scheduler.ps1`, `scraper_output.csv`) tidak di-commit.
- README dan dokumen tanpa emoji. Bahasa Indonesia.