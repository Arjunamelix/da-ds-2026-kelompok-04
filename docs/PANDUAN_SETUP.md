# Panduan Setup Langkah demi Langkah

Ikuti dari atas ke bawah. Kode tiap file ada di empat dokumen per folder:
`1_frontend.md`, `2_backend.md`, `3_ml.md`, `4_root_config_scripts_docs.md`.
Cara kerjanya: buat file kosong di path yang tertulis, lalu tempel isi dari bagian berjudul path itu.

```
React (frontend)  →  Go API (backend)  →  PostgreSQL
                          ↓ POST /retrain
                      FastAPI (ml)  →  menulis prediksi ke PostgreSQL
```

---

## Tahap 0. Pasang alat yang dibutuhkan

| Alat | Versi | Cek |
|---|---|---|
| Git | bebas | `git --version` |
| Docker Desktop (Compose v2) | bebas | `docker compose version` |
| Go | **1.24 atau lebih baru** | `go version` |
| Node.js | 20 atau lebih baru (22 disarankan) | `node -v` |
| Python | 3.11 atau lebih baru | `python --version` (Windows) / `python3 --version` |

Windows: jalankan perintah di **Git Bash** (disarankan) atau PowerShell. Perintah yang beda ditulis dua versi.

---

## Tahap 1. Buat repo dan semua folder

**Git Bash / Linux / macOS**
```bash
mkdir harga-pangan-medan && cd harga-pangan-medan
git init
mkdir -p frontend/src/{pages,components,api,lib,__tests__} \
         backend/cmd/server backend/internal/{config,handler,service,repository,csvimport,model} backend/migrations \
         ml/app ml/tests config scripts docs/laporan \
         data/raw/{pihps,simpang,badanpangan,sp2kp} data/processed data/dev
touch data/raw/{pihps,simpang,badanpangan,sp2kp}/.gitkeep data/processed/.gitkeep data/dev/.gitkeep docs/laporan/.gitkeep
```

**PowerShell**
```powershell
mkdir harga-pangan-medan; cd harga-pangan-medan
git init
$dirs = "frontend/src/pages","frontend/src/components","frontend/src/api","frontend/src/lib","frontend/src/__tests__",
        "backend/cmd/server","backend/internal/config","backend/internal/handler","backend/internal/service",
        "backend/internal/repository","backend/internal/csvimport","backend/internal/model","backend/migrations",
        "ml/app","ml/tests","config","scripts","docs/laporan",
        "data/raw/pihps","data/raw/simpang","data/raw/badanpangan","data/raw/sp2kp","data/processed","data/dev"
$dirs | ForEach-Object { New-Item -ItemType Directory -Force $_ | Out-Null }
```

Hasilnya (kosong dulu, nanti terisi):
```
harga-pangan-medan/
├── frontend/src/{pages,components,api,lib,__tests__}
├── backend/{cmd/server, internal/{config,handler,service,repository,csvimport,model}, migrations}
├── ml/{app,tests}
├── config/   scripts/   docs/laporan/
└── data/{raw/{pihps,simpang,badanpangan,sp2kp}, processed, dev}
```

---

## Tahap 2. File di root, config, dan data (dari `4_root_config_scripts_docs.md`)

| # | File | Catatan |
|---|---|---|
| 1 | `.gitignore` | |
| 2 | `.env.example` | lalu salin jadi `.env` (lihat bawah) |
| 3 | `docker-compose.yml` | |
| 4 | `Makefile` | opsional di Windows (perintahnya bisa diketik manual) |
| 5 | `config/referensi.json` | 21 pasar SIMPANG, 5 komoditas, 21 kecamatan |
| 6 | `data/template_import.csv` | |
| 7 | `README.md` dan `Project.md` | `Project.md` pakai berkasmu sendiri |

```bash
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
```
Buka `.env`, **ganti `POSTGRES_PASSWORD`** (wajib; Compose menolak jalan bila kosong). Jangan commit `.env`.

---

## Tahap 3. Database: migrasi SQL (dari `2_backend.md`)

Buat empat berkas di `backend/migrations/` dan satu berkas Go:

| # | File |
|---|---|
| 1 | `000001_init.up.sql` |
| 2 | `000001_init.down.sql` |
| 3 | `000002_harga_agregat.up.sql` |
| 4 | `000002_harga_agregat.down.sql` |
| 5 | `embed.go` |

Tidak ada yang dijalankan manual: backend Go menerapkan migrasi otomatis saat start.
Isi: tabel `harga` (data asli per pasar), view `harga_agregat` (rata-rata kecamatan dan median kota, dihitung otomatis), dan tabel hasil model.

---

## Tahap 4. Backend Go (dari `2_backend.md`)

**Urutan menempel** (urutan ini menghindari file yang merujuk file yang belum ada):

| # | File |
|---|---|
| 1 | `backend/go.mod` (hanya 2 baris: `module ...` dan `go 1.24`) |
| 2 | `backend/internal/config/config.go` |
| 3 | `backend/internal/model/model.go` |
| 4 | `backend/internal/csvimport/csvimport.go` |
| 5 | `backend/internal/repository/repository.go` |
| 6 | `backend/internal/service/tx.go` |
| 7 | `backend/internal/service/service.go` |
| 8 | `backend/internal/service/analitik.go` |
| 9 | `backend/internal/handler/handler.go` |
| 10 | `backend/cmd/server/main.go` |
| 11 | `backend/internal/config/config_test.go`, `backend/internal/csvimport/csvimport_test.go` |
| 12 | `backend/Dockerfile` |

**Setup dan cek:**
```bash
cd backend
go mod tidy          # mengunduh chi, cors, pgx, golang-migrate dan membuat go.sum (butuh internet)
gofmt -l .           # kosong = rapi
go vet ./...
go build ./...
go test ./...
cd ..
```
Commit `go.mod` **dan** `go.sum`.

> Kode Go ini **belum pernah dikompilasi penuh** (tempat saya menulisnya tidak bisa mengunduh modul Go). Hanya paket `config` dan `csvimport` yang sudah lulus tes. Kalau `go build` menampilkan galat, kirim teks galatnya ke saya; biasanya perbaikan kecil.

---

## Tahap 5. Layanan ML Python (dari `3_ml.md`)

**Urutan menempel:**

| # | File |
|---|---|
| 1 | `ml/requirements.txt` |
| 2 | `ml/app/__init__.py` (**kosong**, buat file kosong saja) |
| 3 | `ml/app/config.py` |
| 4 | `ml/app/kalender.py` |
| 5 | `ml/app/fitur.py` |
| 6 | `ml/app/model.py` |
| 7 | `ml/app/evaluasi.py` |
| 8 | `ml/app/status.py` |
| 9 | `ml/app/pipeline.py` |
| 10 | `ml/app/db.py` |
| 11 | `ml/app/main.py` |
| 12 | `ml/tests/conftest.py`, `test_fitur.py`, `test_evaluasi_status.py`, `test_pipeline_api.py` |
| 13 | `ml/Dockerfile` |

**Setup dan cek:**
```bash
cd ml
python -m venv .venv                 # Linux/macOS: python3 -m venv .venv
source .venv/bin/activate            # Git Bash Windows: source .venv/Scripts/activate
                                     # PowerShell:       .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q                  # harus: 16 passed
cd ..
```
Folder `.venv/` sudah diabaikan git oleh `.gitignore`.

---

## Tahap 6. Frontend React (dari `1_frontend.md`)

Tidak perlu `npm create vite`: semua konfigurasi ada di `package.json` dan `vite.config.js`. Cukup tempel file lalu `npm install`.

**Urutan menempel:**

| # | File |
|---|---|
| 1 | `frontend/package.json` |
| 2 | `frontend/vite.config.js`, `frontend/index.html` |
| 3 | `frontend/src/main.jsx`, `App.jsx`, `AppContext.jsx` |
| 4 | `frontend/src/api/client.js` |
| 5 | `frontend/src/lib/format.js`, `format.test.js` |
| 6 | `frontend/src/components/Layout.jsx`, `Umum.jsx` |
| 7 | `frontend/src/pages/Dashboard.jsx`, `Tren.jsx`, `Perbandingan.jsx`, `Prediksi.jsx`, `KelolaData.jsx` |
| 8 | `frontend/src/styles.css` |
| 9 | `frontend/src/__tests__/halaman.test.jsx` |
| 10 | `frontend/Dockerfile`, `frontend/nginx.conf` |

**Setup dan cek:**
```bash
cd frontend
npm install          # membuat node_modules dan package-lock.json (commit lock file-nya)
npm test             # harus lulus (format.test.js dan 6 tes halaman)
npm run build        # harus berhasil
cd ..
```
Paket yang dipasang `package.json`: `react`, `react-dom`, `react-router-dom`, `recharts`; dev: `vite`, `@vitejs/plugin-react`, `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/dom`.
Kalau mau memasang manual tanpa `package.json` dari saya:
```bash
npm i react react-dom react-router-dom recharts
npm i -D vite @vitejs/plugin-react vitest jsdom @testing-library/react @testing-library/dom
```
(lalu tetap tempel `vite.config.js` dan atur skrip `test` di `package.json` seperti berkas saya).

---

## Tahap 7. Skrip data (dari `4_root_config_scripts_docs.md`)

| # | File | Fungsi |
|---|---|---|
| 1 | `scripts/etl_simpang.py` | mengubah CSV mentah SIMPANG menjadi format 6 kolom |
| 2 | `scripts/impor_csv.py` | mengirim CSV ke API impor (hanya pustaka standar Python) |
| 3 | `scripts/gen_data_dev.py` | opsional: data **sintetis** (sumber DEV), tidak diperlukan karena data asli sudah ada |

Dokumen di `docs/` (`kontrak_api.md`, `alur_data_dev.md`, `hasil_cek_sumber.md`, `logbook.md`, dan file ini) ditempel terakhir.

---

## Tahap 8. Jalankan sistem

### Opsi A: semuanya lewat Docker (paling mudah)
```bash
docker compose up --build -d       # pertama kali butuh beberapa menit
docker compose ps                  # db, backend, ml, frontend harus Up/healthy
docker compose logs -f backend     # cari "skema database siap" dan "API mendengarkan di :8080"
```
Web: **http://localhost:3000**

### Opsi B: mode pengembangan (kode berubah langsung terbaca)
Database lewat Docker, tiga lainnya jalan langsung di laptop. Buka 4 terminal.

```bash
# Terminal 1: database
docker compose up -d db

# Terminal 2: backend  (ganti PASSWORD dengan POSTGRES_PASSWORD di .env)
cd backend
export DATABASE_URL="postgres://pangan:PASSWORD@localhost:5432/harga_pangan?sslmode=disable"
export ML_URL="http://localhost:8000"
go run ./cmd/server
#   PowerShell: $env:DATABASE_URL="postgres://pangan:PASSWORD@localhost:5432/harga_pangan?sslmode=disable"; $env:ML_URL="http://localhost:8000"; go run ./cmd/server

# Terminal 3: layanan ML
cd ml && source .venv/bin/activate
export DATABASE_URL="postgres://pangan:PASSWORD@localhost:5432/harga_pangan?sslmode=disable"
uvicorn app.main:app --port 8000

# Terminal 4: frontend
cd frontend && npm run dev          # http://localhost:5173 (meneruskan /api ke backend :8080)
```

---

## Tahap 9. Muat dataset SIMPANG

1. Simpan CSV mentah dari SIMPANG **apa adanya** di `data/raw/simpang/data_harian_simpang_medan.csv`.
2. Ubah ke format 6 kolom (perlu `pandas`; paling mudah pakai venv `ml`):
   ```bash
   source ml/.venv/bin/activate          # jika belum aktif
   python scripts/etl_simpang.py data/raw/simpang/data_harian_simpang_medan.csv
   ```
   Hasil yang diharapkan pada berkas yang kamu kirim:
   ```
   mentah               :  106995
   dibuang (harga = 0)  :   47463  (44.4%)
   ditolak              :     210
   diimpor              :   59322
   ```
   Keluaran: `data/processed/harga_harian_simpang.csv` (impor) dan `data/processed/simpang_ditolak.csv` (baris yang ditolak beserta alasannya; periksa).
3. Impor lewat API (backend harus sudah jalan):
   ```bash
   python scripts/impor_csv.py data/processed/harga_harian_simpang.csv
   ```
   Harus melapor `baru disimpan 59322`. Jalankan **sekali lagi**: harus `baru disimpan 0` (impor idempoten, tidak membuat duplikat).
4. Tunggu sekitar 1 menit: status di web berubah "sedang menghitung ulang" lalu hasil muncul.

---

## Tahap 10. Cek bahwa semuanya benar

```bash
curl http://localhost:8080/api/health                       # {"status":"ok"}
curl http://localhost:8080/api/status-hitung                # versi_model sama dengan versi_data bila pelatihan selesai
curl "http://localhost:8080/api/ringkasan?kecamatan=KOTA%20MEDAN"
```
Di web:
- Dashboard menampilkan 5 kartu komoditas.
- Perbandingan menampilkan 21 kecamatan; **8 kecamatan tampil "tidak ada data"** (Amplas, Baru, Denai, Labuhan, Maimun, Polonia, Tembung, Timur). Itu benar, bukan galat.
- Kelola Data: tambah satu harga, lalu lihat status "menghitung ulang".

---

## Tahap 11. Commit pertama (repo privat)

```bash
git add .
git status                 # pastikan .env, node_modules, .venv, data/dev TIDAK ikut
git commit -m "chore: kerangka awal proyek harga pangan Medan"
git branch -M main
git remote add origin <URL-repo-privat-kamu>
git push -u origin main
```
`data/raw/` dan `data/processed/` ikut di-commit (ukuran beberapa MB; ketentuan Project.md 7.2).

---

## Masalah yang sering muncul

| Gejala | Penyebab dan solusi |
|---|---|
| `isi POSTGRES_PASSWORD di file .env` | `.env` belum dibuat atau `POSTGRES_PASSWORD` kosong |
| `go mod tidy` gagal mengunduh | tidak ada internet atau proxy kampus; coba jaringan lain |
| `go build` galat | kirim teks galat ke saya (kode Go belum dikompilasi penuh sebelumnya) |
| Port 5432 atau 3000 terpakai | ubah `POSTGRES_HOST_PORT` / `FRONTEND_HOST_PORT` di `.env` |
| Impor: `Backend tidak terjangkau` | backend belum jalan; cek `docker compose logs backend` |
| Impor: banyak baris `tidak valid` | jalankan ETL dulu; impor hanya menerima 6 kolom, harga bulat tanpa titik |
| Web kosong setelah impor | pelatihan belum selesai; cek `/api/status-hitung` dan `docker compose logs ml` |
| `make` tidak dikenal (Windows) | pakai Git Bash atau ketik perintah di Makefile manual |
| Status `error` di web | lihat `pesan_hitung` di `/api/status-hitung`, dan log layanan ml |

---

## Yang perlu kamu ketahui sebelum melapor ke dosen

**Sudah diuji:** tes ML (16), tes frontend (6) dan build, tes Go untuk `config` dan `csvimport`; migrasi SQL, view, dan semua kueri SQL dari kode Go dijalankan di PostgreSQL 16 sungguhan dengan data SIMPANG; jalur ML ke database (baca view, latih, tulis hasil) berhasil.

**Belum diuji:** kompilasi penuh backend Go, dan Docker Compose end-to-end (alur impor lewat Go, retrain otomatis, web berubah).

**Temuan data:**
- Model boosting **belum mengalahkan baseline naif** (harga hari ini berlaku 7/14 hari lagi) di data SIMPANG. Dicoba beberapa varian dan jendela uji; hasilnya konsisten. Harga bahan pokok cenderung datar berminggu-minggu. Ini perlu keputusan arah modelnya.
- Juni–Juli 2024 hampir kosong (4 dari 43 hari kerja ada data).
- Pada 6 Sep 2024 harga bawang merah anjlok serentak di banyak pasar lalu kembali normal; periksa apakah itu nyata atau masalah scraping.
- Jenis beras dan minyak goreng di SIMPANG tidak tertulis; diasumsikan `beras_medium` dan `minyak_goreng_curah`.
