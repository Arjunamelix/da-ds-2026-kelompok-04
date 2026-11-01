# Analisis dan Prediksi Harga Bahan Pokok Berdasarkan Waktu di Wilayah Kota Medan

Dashboard web dinamis untuk **Data Analitik** dan **Data Science**: memantau tren harga bahan pokok di Kota Medan,
membandingkan antar kecamatan, memprediksi harga 7 dan 14 hari ke depan, dan memberi status harga
(Normal / Waspada / Lonjakan). Saat data baru ditambahkan, grafik, prediksi, dan status ikut diperbarui otomatis.

- **Sumber data:** SIMPANG Pemko Medan (hasil scraping tim), 2 Januari 2024 sampai 15 Oktober 2026
- **Cakupan:** 21 kecamatan Kota Medan (13 punya data, 8 tampil "tidak ada data"), 5 komoditas

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
menjalankannya (Python hanya dibutuhkan untuk dua skrip data, lihat bagian 2). Satu perintah menyalakan empat layanan:

```
Peramban  →  frontend (React, nginx)  →  backend (Go)  →  db (PostgreSQL)
                                              ↓  setelah data berubah
                                         ml (Python FastAPI)  →  menulis prediksi, status, evaluasi ke db
```

| Layanan | Teknologi | Tugas | Alamat di laptop |
|---|---|---|---|
| `frontend` | React + Vite, disajikan nginx | Halaman dashboard | http://localhost:3000 |
| `backend` | Go (chi, pgx) | API, validasi, impor/ekspor CSV, memicu pelatihan ulang | http://localhost:8080/api |
| `ml` | Python (FastAPI, scikit-learn) | Melatih model dan menghitung prediksi dan status | hanya di dalam Docker |
| `db` | PostgreSQL 16 | Menyimpan data harga dan hasil model | `localhost:5432` |

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

Empat layanan (`db`, `backend`, `ml`, `frontend`) harus berstatus **Up**, dan `db` berstatus **healthy**. Lalu cek backend:

```bash
curl http://localhost:8080/api/health
```
(Di PowerShell: `Invoke-RestMethod http://localhost:8080/api/health`.) Hasilnya harus `{"status":"ok"}`.

### Langkah 5. Olah data mentah SIMPANG

Data mentah sudah ada di repo (`data/raw/simpang/data_harian_simpang_medan.csv`). Ubah ke format impor:

```bash
pip install pandas
python scripts/etl_simpang.py data/raw/simpang/data_harian_simpang_medan.csv
```

(Di macOS/Linux, pakai `python3`.) Angka yang **harus** muncul:

| Keterangan | Jumlah |
|---|---|
| Baris mentah | 106.995 |
| Dibuang (harga 0 = tidak ada data hari itu) | 47.463 |
| Ditolak (di luar batas wajar atau menyimpang ekstrem) | 210 |
| **Diimpor** | **59.322** |

Hasilnya ditulis ke `data/processed/harga_harian_simpang.csv`, dan baris yang ditolak ke `data/processed/simpang_ditolak.csv`.

### Langkah 6. Impor data ke database

```bash
python scripts/impor_csv.py data/processed/harga_harian_simpang.csv
```

Yang harus muncul: `baru disimpan 59322 | dilewati (sudah ada) 0 | tidak valid 0`.
Perintah ini **aman diulang**: pada percobaan kedua hasilnya `baru disimpan 0`, tanpa duplikat.

### Langkah 7. Tunggu model selesai dilatih

Begitu data masuk, model dilatih otomatis di belakang layar (sekitar 40 detik sampai 1 menit). Pantau:

```bash
curl http://localhost:8080/api/status-hitung
docker compose logs ml --tail 10
```

Tunggu `status_hitung` menjadi `idle`. Di log ML akan ada baris `selesai: 140 prediksi, 70 status, 0 dilewati`.

### Langkah 8. Buka dashboard

**http://localhost:3000**

Selesai.

> **Ringkasan cepat** (setelah `.env` dibuat dan Docker menyala):
> ```bash
> docker compose up --build -d
> pip install pandas
> python scripts/etl_simpang.py data/raw/simpang/data_harian_simpang_medan.csv
> python scripts/impor_csv.py data/processed/harga_harian_simpang.csv
> ```
> lalu buka http://localhost:3000.

---

## 4. Memakai dashboard

| Halaman | Alamat | Isi |
|---|---|---|
| **Dashboard** | `/` | Kartu per komoditas: harga terakhir, perubahan 7 hari, prediksi 7 hari, dan status. Pilih "KOTA MEDAN" atau satu kecamatan |
| **Tren** | `/tren` | Grafik garis harga. Pilih komoditas, sampai 3 kecamatan, dan rentang waktu |
| **Perbandingan** | `/perbandingan` | Harga 21 kecamatan untuk satu komoditas, terurut, beserta selisih terhadap harga Kota Medan |
| **Prediksi** | `/prediksi` | Prediksi 7 dan 14 hari dengan rentang 80%, status, dan evaluasi model dibanding baseline |
| **Kelola Data** | `/kelola` | Tambah, ubah, hapus data; impor dan ekspor CSV; melihat perubahan prediksi sebelum dan sesudah |

Cara kerja angka di dashboard:
- Harga **kecamatan** = rata-rata harga semua pasar di kecamatan itu pada hari itu.
- Harga **Kota Medan** = median harga semua pasar pada hari itu (minimal 3 pasar melapor).
- **8 kecamatan tampil "tidak ada data"** (Medan Amplas, Baru, Denai, Labuhan, Maimun, Polonia, Tembung, Timur). Itu benar: sumber SIMPANG tidak
  punya pasar di sana. Tidak ada angka yang ditebak.

Untuk mencoba sifat dinamisnya: buka **Kelola Data**, tambahkan satu data harga, lalu lihat kartu prediksi berubah setelah model dihitung ulang
(status "sedang menghitung ulang" tampil sebentar).

---

## 5. Tentang data

- **Sumber:** SIMPANG Pemko Medan, hasil scraping tim: 106.995 baris, 21 pasar di 13 kecamatan, 5 komoditas, harian sejak 1 Januari 2024.
- **Komoditas:** Beras Medium, Bawang Merah, Bawang Putih, Minyak Goreng Curah, Daging Sapi. (Jenis beras dan minyak goreng masih berupa asumsi yang perlu dikonfirmasi tim.)
- **Format impor** (6 kolom, boleh urutan bebas): `tanggal, kecamatan, nama_pasar, komoditas, harga, sumber`. Contoh ada di `data/template_import.csv`.
- **Aturan pembersihan** (`scripts/etl_simpang.py`): harga 0 dianggap tidak ada data dan dibuang; harga di luar batas wajar komoditas ditolak; harga yang menyimpang lebih dari 40% dari median pasar lain pada hari itu (bila minimal 5 pasar melapor) ditolak sebagai dugaan salah input.
- **Hanya data asli per pasar** yang disimpan di tabel `harga`. Rata-rata kecamatan dan median kota dihitung otomatis oleh view `harga_agregat`.
- **Batasan:** data SIMPANG hanya terisi sekitar 616 dari 1.018 hari kalender (ada lubang, terutama Mei sampai Juli 2024); 8 dari 21 kecamatan tidak punya data; ada kemungkinan anomali pada bawang merah 6 September 2024 yang masih diperiksa.
- **Model:** pada data ini model boosting belum mengalahkan baseline naif (harga hari ini dianggap berlaku 7 atau 14 hari lagi). Ini temuan yang dilaporkan jujur, bukan galat. Rinciannya di [`Project.md`](Project.md) bagian 11.5.

Data sintetis untuk uji (`python scripts/gen_data_dev.py`) hanya untuk menguji aplikasi dan **tidak boleh dipakai di laporan**.

---

## 6. Struktur proyek

```
Dasi_Dalis_04/
├── README.md                  dokumen ini
├── Project.md                 keputusan, status, dan rencana kerja proyek
├── docker-compose.yml         menjalankan db + backend + ml + frontend
├── .env.example               contoh pengaturan (salin menjadi .env)
├── Makefile                   pintasan perintah (macOS/Linux)
├── frontend/                  React + Vite (dashboard)
│   └── src/{pages,components,api,lib,__tests__}
├── backend/                   Go (chi, pgx, golang-migrate)
│   ├── cmd/server/main.go
│   ├── internal/{config,handler,service,repository,csvimport,model}
│   └── migrations/            skema PostgreSQL (tertanam di biner, berjalan otomatis)
├── ml/                        Python FastAPI
│   ├── app/{main,pipeline,fitur,model,evaluasi,status,kalender,db,config}.py
│   └── tests/
├── config/referensi.json      21 kecamatan, 21 pasar, 5 komoditas, batas harga (dibaca Go dan Python)
├── data/
│   ├── raw/simpang/           data mentah SIMPANG (hanya ditambah)
│   ├── processed/             hasil ETL (dibuat ulang lewat skrip)
│   ├── dev/                   data sintetis uji (diabaikan git)
│   └── template_import.csv
├── scripts/                   etl_simpang.py, impor_csv.py, gen_data_dev.py
└── docs/                      PANDUAN_SETUP.md, kontrak_api.md, alur_data_dev.md, hasil_cek_sumber.md, logbook.md, laporan/
```

---

## 7. Menjalankan tes

Tes **tidak** berjalan di Docker; ia butuh alat masing-masing di laptop (hanya bagi yang ingin mengembangkan kode).

| Bagian | Syarat | Perintah |
|---|---|---|
| Frontend | Node.js 20+ | `cd frontend && npm install && npm test` |
| ML | Python 3.10+ | `cd ml && python -m venv .venv`, aktifkan venv, `pip install -r requirements.txt`, `pytest` (harus **16 lulus**) |
| Backend | Go 1.25+ | `cd backend && go mod tidy && go vet ./... && go test ./...` |

Aktivasi venv: Windows `.\.venv\Scripts\Activate.ps1`; macOS/Linux `source .venv/bin/activate`.
