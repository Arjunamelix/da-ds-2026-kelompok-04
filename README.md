# Analisis dan Prediksi Harga Bahan Pokok Berdasarkan Waktu di Wilayah Kota Medan

Dashboard web dinamis (Data Analitik + Data Science). Sumber kebenaran proyek: [`Project.md`](Project.md).

```
React (frontend)  →  Go API (backend)  →  PostgreSQL
                          ↓ POST /retrain (setelah data berubah, tanpa menunggu)
                      FastAPI (ml)  →  menulis prediksi, status, evaluasi ke PostgreSQL
```

## Menjalankan di laptop

Panduan lengkap langkah demi langkah: [`docs/PANDUAN_SETUP.md`](docs/PANDUAN_SETUP.md).

```bash
cp .env.example .env            # isi POSTGRES_PASSWORD
make up                         # atau: docker compose up --build -d
make etl                        # data mentah SIMPANG -> data/processed/harga_harian_simpang.csv
make import-data                # impor lewat API (aman diulang)
# buka http://localhost:3000
```

Pertama kali, jalankan sekali `cd backend && go mod tidy` lalu commit `go.mod` dan `go.sum`.

## Data

Sumber saat ini: **SIMPANG** (21 pasar di 13 kecamatan, 5 komoditas, harian sejak 1 Jan 2024). Hanya data asli per pasar yang
disimpan di tabel `harga`. Rata-rata kecamatan dan median kota dihitung otomatis oleh view `harga_agregat`.
Delapan kecamatan tidak punya pasar di SIMPANG dan ditampilkan sebagai "tidak ada data". Alur: [`docs/alur_data_dev.md`](docs/alur_data_dev.md).

## Struktur proyek

```
harga-pangan-medan/
├── README.md, Project.md, Makefile, docker-compose.yml, .env.example, .gitignore
├── frontend/             React + Vite (dashboard, tren, perbandingan, prediksi, kelola data)
│   └── src/{pages,components,api,lib,__tests__}
├── backend/              Go (chi, pgx, golang-migrate)
│   ├── cmd/server/main.go
│   ├── internal/{config,handler,service,repository,csvimport,model}
│   └── migrations/       skema PostgreSQL (tertanam di biner)
├── ml/                   Python FastAPI
│   ├── app/{main,pipeline,fitur,model,evaluasi,status,kalender,db,config}.py
│   └── tests/
├── config/referensi.json 21 kecamatan, komoditas, batas harga, pasar, pemetaan (dibaca Go dan Python)
├── data/{raw,processed,dev}, data/template_import.csv
├── scripts/              etl_simpang.py, impor_csv.py, gen_data_dev.py (sintetis, opsional)
└── docs/                 kontrak_api.md, alur_data_dev.md, hasil_cek_sumber.md, logbook.md, laporan/
```

## Pengujian

```bash
make test          # test-go, test-ml, test-front
```

## Aturan kerja bersama

Lihat Project.md bagian 7.2: branch `fitur/<nama>` atau `data/<nama>`, Pull Request ditinjau minimal satu
anggota, `data/raw/` hanya ditambah, jangan commit `.env`.
