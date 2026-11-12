# S3 · Pemodelan: ≥ 3 algoritma dan tuning

Bagian dari R3 (pemodelan ulang). Kode, tabel lengkap, dan grafik ada di `notebooks/pemodelan.ipynb` bagian S3.
Pembangun model ada di `app/ml/app/model_global.py` dan validasi silang di `app/ml/app/validasi_global.py` (tes: `app/ml/tests/test_model_global.py`).
Semua angka berasal dari validasi silang 4 lipatan waktu (Jul 2025 – Jun 2026) dengan fitur final S2 (13 fitur). Data uji belum disentuh.

## 1. Algoritma

| Algoritma | Peran | Loss | Praproses (di-fit pada data latih saja) |
|---|---|---|---|
| Ridge | Baseline linear wajib | kuadrat | imputasi median + penanda kosong, standardisasi, one-hot komoditas |
| Random Forest | Ansambel bagging | kuadrat | imputasi median + penanda kosong, one-hot komoditas |
| HistGradientBoosting | Model penguji S2 | absolut | tidak perlu |
| LightGBM | Model lanjutan boosting | dipilih saat tuning | tidak perlu |

## 2. Tuning

- Optuna, sampler TPE (`seed = 42`), satu studi per algoritma per horizon. Percobaan ke-0 selalu parameter bawaan.
- Jumlah percobaan: Ridge 20, Random Forest 15, HistGradientBoosting 30, LightGBM 40 (total 210 percobaan, masing-masing 4 lipatan).
- Skor: rata-rata rasio MAE terhadap naif atas 4 lipatan × 2 kelompok (1,0 = sama dengan naif).
- Semua percobaan: `docs/model/s3_tuning.csv`.

| Algoritma | Skor bawaan h7 → terbaik | Skor bawaan h14 → terbaik |
|---|---|---|
| Ridge | 1,835 → 1,795 | 1,807 → 1,731 |
| Random Forest | 1,177 → 1,112 | 1,196 → 1,193 |
| HistGradientBoosting | 0,986 → 0,983 | 0,984 → 0,965 |
| LightGBM | 1,001 → 0,992 | 1,006 → 0,986 |

LightGBM terbaik memakai loss L1 (absolut) di kedua horizon. Model berloss kuadrat (Ridge, Random Forest) sangat buruk pada komoditas
stabil (+24% sampai +160% dibanding naif) karena terus menebak gerak kecil pada harga yang hampir tidak pernah berubah.

## 3. Strategi untuk komoditas stabil

| Strategi | Cara |
|---|---|
| Gabungan | Satu model untuk semua komoditas |
| (a) Per kelompok | Model terpisah untuk bergejolak dan stabil |
| (b) Penyusutan | Prediksi kecil disusutkan ke nol dengan ambang τ per kelompok (dipilih di validasi silang, jadi sedikit optimistis) |
| (c) Naif untuk stabil | Model hanya untuk bergejolak |

Skor terbaik tiap algoritma (MAE dibanding naif, rata-rata 4 lipatan; negatif = lebih baik):

| Algoritma · strategi | h7 bergejolak | h7 stabil | h14 bergejolak | h14 stabil | Rata 2 horizon |
|---|---|---|---|---|---|
| **LightGBM · (a) per kelompok** | **−3,1%** | **−3,9%** | −6,7% | +0,1% | **−3,4%** |
| Random Forest · (b) penyusutan | −3,2% | −0,1% | −8,7% | −0,5% | −3,1% |
| HistGradientBoosting · (b) penyusutan | −3,2% | −0,1% | −6,8% | −0,6% | −2,7% |
| HistGradientBoosting · gabungan | −3,2% | −0,1% | −6,5% | −0,6% | −2,6% |
| Ridge · (b) penyusutan | −2,7% | +0,1% | −6,3% | 0,0% | −2,2% |

## 4. Uji ulang kalender

Pada LightGBM per kelompok, menambah fitur kalender tetap tidak membantu. Pada h = 7, komoditas bergejolak memburuk
(+0,7% dengan hari besar, +3,3% dengan bulan, dibanding −3,1% tanpa kalender). Pada h = 14 hanya Ramadan yang hampir sama
(−3,4% dibanding −3,3%). Kalender tidak dipakai.

## 5. Model terpilih

**LightGBM, loss L1, satu model untuk komoditas bergejolak dan satu untuk komoditas stabil, per horizon (4 model).**
Konfigurasi lengkap: `docs/model/s3_terpilih.json`.

Alasan:
1. Skor rata-rata kedua horizon terbaik (−3,4%), dan satu-satunya kandidat yang lebih baik dari naif di kedua kelompok pada h = 7.
2. Tidak bergantung pada ambang yang dipilih di validasi silang, sehingga angkanya tidak optimistis.
3. Cepat dilatih (sekitar 2 detik per lipatan untuk dua model), penting karena aplikasi melatih ulang setiap kali data berubah.
4. Random Forest penyusutan unggul pada h = 14, tetapi jauh lebih lemah pada h = 7 dan stabilnya bergantung penuh pada ambang besar.

Posisi sementara terhadap kriteria sukses S1 (validasi silang): bergejolak h7 −3,1% dan h14 −6,7% (minimum terpenuhi, target 5% terpenuhi
untuk h14); stabil h7 −3,9% dan h14 +0,1% (minimum terpenuhi). Angka resmi dari data uji ada di S4.

## 6. Catatan untuk S4–S5

- S4: model terpilih dilatih dengan data latih + validasi (hari target sampai 30 Juni 2026), lalu dinilai sekali di data uji,
  dibanding naif dan model lama, termasuk status.
- Lipatan 1 (Jul–Sep 2025) tetap lebih buruk dari naif untuk komoditas bergejolak di semua algoritma; dianalisis di S5.