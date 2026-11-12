# S2 · Preprocessing dan feature engineering

Bagian dari R3 (pemodelan ulang). Kode, tabel lengkap, dan grafik ada di `notebooks/pemodelan.ipynb` bagian S2.
Fungsi fitur ada di `app/ml/app/fitur_global.py` (dipakai juga oleh aplikasi di S6), dengan tes di `app/ml/tests/test_fitur_global.py`.
Semua angka hanya memakai data latih dan validasi (hari target sampai 30 Juni 2026). Data uji belum disentuh.

## 1. Alur preprocessing

| Langkah | Perlakuan |
|---|---|
| Potret data | Data bersih sampai 15 Oktober 2026 (keputusan S1) |
| Agregasi harian | Kecamatan = rata-rata pasar; Kota Medan = median pasar (minimal 3 pasar), sama dengan view `harga_agregat`. Jumlah pasar melapor dan sebaran harga antarpasar ikut dicatat |
| Deret harian | Hari tanpa data diisi interpolasi linear paling lama 14 hari, hanya untuk mengisi jendela bergulir |
| Baris model | Hari asal dan hari target harus data asli. Hasilnya sama persis dengan tabel S1 (83.384 baris untuk h = 7) |
| Target | y = ln P[t+h] − ln P[t], h = 7 dan 14 |
| Nilai kosong | Dibiarkan kosong untuk model pohon. Untuk model linear (S3): imputasi median dan standardisasi yang dihitung dari data latih saja |
| Kategori | Komoditas sebagai kode kategori (model pohon) atau one-hot (model linear) |

Cek kebocoran: fitur pada hari t dihitung ulang setelah semua data sesudah t dihapus, dan hasilnya sama persis
(80 baris acak dari data asli, ditambah tes otomatis pada data sintetis).

## 2. Fitur kandidat (25 fitur, 5 kelompok)

| Kelompok | Fitur |
|---|---|
| Identitas | `komoditas_kode`, `bergejolak`, `tingkat_kota` |
| Momentum | `ret_1`, `ret_3`, `ret_7`, `ret_14`, `ret_28`, `rasio_ma30`, `rasio_ma90`, `rasio_ma365` |
| Volatilitas dan kelengketan | `vol14`, `vol56`, `frac_berubah_28`, `hari_sejak_berubah` |
| Pasar dan wilayah | `n_pasar`, `dispersi`, `selisih_kota`, `ret_7_kota` |
| Kalender (tanggal target) | `hb_menjelang`, `hb_target`, `hari_ke_hb`, `ramadan_target`, `bulan_sin`, `bulan_cos` |

Rumus dan alasan tiap fitur ada di notebook S2.2. Kelompok pasar dan wilayah baru dimungkinkan oleh model gabungan,
karena model per deret yang lama tidak bisa melihat harga kota atau pasar lain.

## 3. Ablation

Model penguji tetap: `HistGradientBoostingRegressor`, `loss="absolute_error"`, hiperparameter tetap, tanpa tuning.
Validasi silang 4 lipatan waktu (expanding window): Jul–Sep 2025, Okt–Des 2025, Jan–Mar 2026 (Ramadan 2026), Apr–Jun 2026.
Ukuran: MAE (rupiah) dibanding baseline naif, dalam persen; negatif berarti lebih baik dari naif.

Rata-rata 4 lipatan:

| Konfigurasi | Bergejolak h = 7 | Stabil h = 7 | Bergejolak h = 14 | Stabil h = 14 |
|---|---|---|---|---|
| Identitas + momentum | +4,7% | +2,6% | +2,1% | +12,6% |
| + volatilitas | +3,9% | +0,2% | +0,8% | +2,9% |
| + pasar dan wilayah = **B** | −1,3% | +0,1% | −4,7% | +6,7% |
| B tanpa pasar dan wilayah | +3,9% | +0,2% | +0,8% | +2,9% |
| B + hari besar | +2,3% | +0,4% | +1,5% | +13,5% |
| B + Ramadan | +0,1% | +0,4% | −4,0% | +10,7% |
| B + bulan | +2,6% | −0,1% | +1,5% | +13,2% |
| **K (set final, 13 fitur)** | **−3,3%** | +0,5% | **−6,2%** | +3,0% |

Set K disusun dari permutation importance di lipatan 4: fitur yang kepentingannya nol atau negatif dikeluarkan
(`ret_1`, `ret_7`, `ret_28`, `rasio_ma90`, `vol14`, `vol56`). Perbaikannya juga terlihat di lipatan 1–3, yang tidak dipakai untuk memilih.

## 4. Keputusan

Fitur final (`fitur_global.FITUR_TERPILIH`, 13 fitur):

| Kelompok | Fitur |
|---|---|
| Identitas | `komoditas_kode`, `bergejolak`, `tingkat_kota` |
| Momentum | `ret_3`, `ret_14`, `rasio_ma30`, `rasio_ma365` |
| Kelengketan | `frac_berubah_28`, `hari_sejak_berubah` |
| Pasar dan wilayah | `n_pasar`, `dispersi`, `selisih_kota`, `ret_7_kota` |

- **Pasar dan wilayah** adalah kelompok fitur terpenting. `selisih_kota` dan `ret_7_kota` termasuk 4 fitur teratas di kedua horizon.
- **Kalender dikeluarkan**: tidak menurunkan galat di validasi silang. Dugaan: data latih hanya memuat dua siklus Ramadan dan Idulfitri,
  sehingga model menghafal kejadian di dua tahun itu. Fungsinya tetap ada dan diuji ulang sekali di S3 setelah tuning.

## 5. Catatan untuk S3–S5

1. Kelompok stabil masih sedikit di atas naif (+0,5% h = 7, +3,0% h = 14). Kriteria minimum S1 (tidak lebih dari 5% lebih buruk)
   terpenuhi secara rata-rata, tetapi S3 akan menguji model terpisah per kelompok atau penyusutan prediksi kecil ke nol.
2. Lipatan 1 (Jul–Sep 2025) jauh lebih buruk dari naif di semua set fitur; data latihnya paling sedikit. Dianalisis di S5.
3. Angka S2 adalah batas bawah karena model penguji belum di-tuning.