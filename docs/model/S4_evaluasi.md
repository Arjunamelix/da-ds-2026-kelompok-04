# S4 · Evaluasi dan validasi model

Bagian dari R3 (pemodelan ulang). Kode, tabel lengkap, dan grafik ada di `notebooks/pemodelan.ipynb` bagian S4.
Angka lengkap: `docs/model/s4_hasil_uji.csv`. Keputusan untuk aplikasi: `docs/model/s4_keputusan.json`.

## 1. Rancangan

- Model, parameter, dan aturan dikunci di S3 (`s3_terpilih.json`) **sebelum** data uji dibuka. Data uji (hari asal 1 Juli – 15 Oktober 2026)
  dipakai satu kali.
- Semua model dilatih ulang dengan seluruh baris yang hari targetnya sampai 30 Juni 2026, dengan parameter hasil tuning S3.
- Pembanding: naif, model lama, Linear Regression murni, Ridge, Random Forest, HistGradientBoosting, LightGBM gabungan, dan model terpilih.
  Semua dinilai pada baris uji yang sama (10.919 baris untuk h = 7, 10.094 untuk h = 14).
- Ketidakpastian: bootstrap per deret (1.000 kali, 169 deret diambil ulang).

## 2. Hasil di data uji (MAE dibanding naif; negatif = lebih baik)

| Model | h7 bergejolak | h7 stabil | h7 semua | h14 bergejolak | h14 stabil | h14 semua |
|---|---|---|---|---|---|---|
| Model lama | +12,9% | +74,8% | +19,8% | +12,3% | +56,4% | +17,8% |
| Linear Regression | +2,5% | +85,9% | +11,8% | +3,8% | +67,0% | +11,6% |
| Ridge | +2,3% | +84,5% | +11,5% | +3,6% | +65,0% | +11,2% |
| Random Forest · penyusutan | −0,1% | −3,6% | −0,5% | +6,6% | −3,0% | +5,4% |
| HistGradientBoosting · penyusutan | −0,7% | 0,0% | −0,6% | +1,7% | 0,0% | +1,5% |
| LightGBM gabungan | −0,4% | −0,1% | −0,4% | +2,7% | +0,5% | +2,4% |
| **LightGBM per kelompok (terpilih)** | **+2,7%** | **−9,1%** | +1,4% | **+2,7%** | 0,0% | +2,4% |

MAPE naif: h7 bergejolak 7,77%, stabil 0,76%; h14 bergejolak 10,56%, stabil 1,24%.

Interval kepercayaan 90% (bootstrap) untuk model terpilih:
- bergejolak h7 +0,1% s.d. +5,6%, h14 +0,5% s.d. +5,0% (lebih buruk dari naif, bermakna)
- stabil h7 −13,5% s.d. −2,8% (lebih baik dari naif, bermakna), h14 −0,0% s.d. +0,1% (setara)

Per deret: model terpilih lebih baik dari naif di 73 dari 165 deret (h7) dan 63 dari 165 (h14); model lama 11 dan 19.
Per komoditas (h7): terbaik pada daging sapi (−15%) dan daging ayam ras (−7%); terburuk pada cabai rawit (+10%) dan beras (+13%, tetapi MAPE tetap 0,42%).
Per bulan: komoditas bergejolak memburuk pada Agustus dan September 2026 (+7%), membaik pada Oktober (−11%).

## 3. Status dan rentang prediksi

| Aturan status (h = 7) | Recall | Presisi | F1 |
|---|---|---|---|
| Persistensi (aktual 7 hari terakhir) | 0,202 | 0,210 | 0,206 |
| Kombinasi: aktual ATAU model lama | 0,365 | 0,205 | 0,263 |
| **Kombinasi: aktual ATAU model terpilih** | **0,270** | **0,243** | **0,256** |

Rentang 80% (persentil 10 dan 90 galat out-of-fold): cakupan bergejolak 82% (h7) dan 81% (h14); stabil 77%.

## 4. Kriteria sukses S1

| Kelompok | Minimum | Target |
|---|---|---|
| Bergejolak h7 dan h14 | **tidak tercapai** (+2,7%) | tidak |
| Stabil h7 | tercapai (−9,1%) | tercapai |
| Stabil h14 | tercapai (0,0%) | tidak (setara naif) |
| Status | tercapai (recall dan F1 di atas persistensi) | tidak (recall 0,270 < 0,40) |

Validasi silang S3 terlalu optimistis untuk komoditas bergejolak (−3,1% menjadi +2,7%). Lipatan Juli–September 2025 juga lebih buruk
dari naif; periode Juli–September tampaknya sulit diprediksi. Ini dianalisis di S5.

## 5. Keputusan untuk aplikasi (S6)

Mengikuti aturan cadangan S1 ("bila kriteria minimum tidak tercapai pada satu kelompok, aplikasi memakai baseline naif untuk kelompok itu"):

- **Stabil:** prediksi dari LightGBM kelompok stabil.
- **Bergejolak:** prediksi titik naif (harga tetap), dengan rentang dari sebaran perubahan historis (h7 −12,5% s.d. +16,7%, cakupan di data uji 83%).
- **Status:** aturan S1.7 tetap (perubahan aktual ATAU prediksi model terpilih), karena aturan ini ditetapkan sebelum data uji dan memenuhi kriteria minimum.

Kinerja aplikasi dengan aturan ini di data uji: 1,0% lebih baik dari naif (h7) dan setara (h14), dibanding model lama yang 19,8% dan 17,8% lebih buruk.
