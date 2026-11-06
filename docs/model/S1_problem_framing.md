# S1 · Problem framing dan desain eksperimen

Bagian dari R3 (pemodelan ulang). Rincian perhitungan, kode, dan grafik ada di `notebooks/pemodelan.ipynb` bagian S1.
Semua angka di bawah dihitung dari data bersih `data/processed/` (133.218 baris, 2 Jan 2024 – 15 Okt 2026).
Status: **disetujui tim** (keputusan tambahan di bagian 9).

## 1. Pertanyaan keputusan dan pengguna

| Pengguna | Pertanyaan keputusan | Keluaran model |
|---|---|---|
| Konsumen | Berapa kira-kira harga minggu depan dan dua minggu lagi? Perlu beli sekarang? | Prediksi harga 7 dan 14 hari beserta rentangnya |
| Pedagang | Apakah harga akan naik tajam sehingga perlu menambah atau menahan stok? | Status Normal / Waspada / Lonjakan |
| Pemerintah (Dinas Perdagangan, TPID) | Komoditas dan wilayah mana yang perlu diwaspadai minggu depan? | Status per komoditas dan kecamatan, dengan alasannya |

## 2. Rumusan tugas

| Aspek | Keputusan |
|---|---|
| Jenis tugas | Regresi |
| Target | Perubahan harga log h hari ke depan, y = ln(P[t+h]) − ln(P[t]), h = 7 dan 14; dikonversi ke rupiah P[t]·exp(ŷ) |
| Deret | Level Kota Medan (median harga pasar, minimal 3 pasar) dan level kecamatan (rata-rata pasar), sama dengan view `harga_agregat` |
| Jumlah deret | 169 (12 kota, 157 kecamatan); 2 deret dilewati karena kurang dari 90 hari data (jagung Medan Area 51 hari, kedelai Medan Selayang 3 hari) |
| Jenis model | Satu model gabungan untuk semua deret per horizon, dengan fitur komoditas dan wilayah |
| Status | Turunan dari prediksi dan perubahan aktual (aturan kombinasi, bagian 6) |
| Deret berhenti melapor | Garam halus dan susu bubuk Medan Area (terakhir 19 Feb 2026), kedelai Medan Area (terakhir 22 Jul 2025): dipakai untuk latih, tidak diberi prediksi di aplikasi |

Alasan memprediksi perubahan, bukan harga: satu model bisa dipakai untuk komoditas dengan tingkat harga sangat berbeda
(gula sekitar Rp18 ribu sampai daging sapi sekitar Rp145 ribu), dan perbandingan dengan baseline "harga tetap" (perubahan = 0) menjadi adil.

## 3. Sifat target: harga bahan pokok "lengket"

Persentase pasangan hari (keduanya data asli, periode latih) yang harganya **sama persis** 7 hari kemudian:

| Kelompok | Komoditas (% tidak berubah) |
|---|---|
| **Bergejolak** | Cabai merah 11%, cabai rawit 16%, bawang merah 24%, daging ayam ras 27%, bawang putih 43% |
| **Stabil** | Telur ayam ras 85%, minyak goreng curah 86%, daging sapi 88%, beras medium 89%, gula pasir 90%, jagung 90%, kedelai 92%, susu bubuk 96%, garam halus 97% |

Akibatnya: pada komoditas stabil, tebakan "harga tetap" sudah benar di 85–97% kasus, sehingga model sulit (dan tidak perlu) mengalahkannya jauh.
Nilai tambah model ada di komoditas bergejolak. Evaluasi karena itu dilaporkan **per kelompok** dan **per komoditas**.

## 4. Pembagian data (kronologis, tanpa kebocoran)

Baris dibagi menurut hari asal t dan hari target t + h, sehingga ada jeda h hari di setiap batas.

| Bagian | Syarat | h = 7 | h = 14 | Fungsi |
|---|---|---|---|---|
| Latih | t + h ≤ 31 Mar 2026 | 63.772 | 63.052 | Melatih, memilih fitur |
| Validasi | t ≥ 1 Apr 2026 dan t + h ≤ 30 Jun 2026 | 7.190 | 6.715 | Tuning, memilih algoritma |
| Uji | t ≥ 1 Jul 2026 | 10.979 | 10.149 | Sekali saja, angka final; model final dilatih dengan latih + validasi |
| Jeda (tidak dipakai) | di batas antarbagian | 1.443 | 2.411 | Mencegah kebocoran target |

Hanya baris yang hari asal dan hari target-nya **data asli** yang dihitung (bukan hasil interpolasi).

Keterbatasan: periode uji (Juli–Oktober 2026) tidak memuat hari besar nasional, sedangkan Iduladha 2026 ada di periode validasi.
Pengaruh fitur hari besar dinilai di data validasi dan validasi silang (S2–S3). Periode uji juga memuat lonjakan cabai September–Oktober 2026.

## 5. Metrik dan baseline

| Metrik | Arti | Peran |
|---|---|---|
| **MAPE** | rata-rata meleset dalam persen harga | Metrik utama; memilih model di data validasi |
| **MAE** | rata-rata meleset dalam rupiah | Syarat "berguna": harus lebih kecil dari baseline naif |
| RMSE | menghukum kesalahan besar lebih berat | Pelengkap |
| R² perubahan | variasi perubahan harga yang dijelaskan model | Pelengkap; 0 = sama dengan menebak "tidak berubah" |

R² dihitung pada skala perubahan. Pada skala harga, tebakan "harga tetap" sudah mendapat R² sekitar 0,98, sehingga angka itu menyesatkan.

Baseline: (1) **naif** "harga tetap"; (2) **model lama** yang sekarang berjalan di aplikasi (`GradientBoostingRegressor` satu per deret,
hiperparameter tetap), dilatih dengan latih + validasi lalu diuji di data uji; (3) Linear Regression dikerjakan di S3.

### Patokan "sebelum" di data uji

| h | Kelompok | Model | MAE (Rp) | RMSE (Rp) | MAPE | R² perubahan |
|---|---|---|---|---|---|---|
| 7 | Bergejolak | naif | 3.567 | 5.934 | 7,77% | −0,010 |
| 7 | Bergejolak | model lama | 4.028 | 6.257 | 8,90% | −0,149 |
| 7 | Stabil | naif | 329 | 2.424 | 0,77% | −0,001 |
| 7 | Stabil | model lama | 576 | 2.434 | 1,58% | −0,349 |
| 7 | Semua | naif | 1.701 | 4.279 | 3,73% | −0,003 |
| 7 | Semua | model lama | 2.039 | 4.472 | 4,68% | −0,160 |
| 14 | Bergejolak | naif | 4.903 | 7.645 | 10,57% | −0,036 |
| 14 | Bergejolak | model lama | 5.506 | 8.108 | 12,05% | −0,164 |
| 14 | Stabil | naif | 514 | 2.996 | 1,24% | −0,001 |
| 14 | Stabil | model lama | 803 | 2.960 | 2,25% | −0,303 |
| 14 | Semua | naif | 2.375 | 5.473 | 5,20% | −0,012 |
| 14 | Semua | model lama | 2.797 | 5.738 | 6,41% | −0,154 |

Per komoditas (h = 7, MAPE naif → model lama): cabai merah 14,3% → 15,1%; cabai rawit 10,0% → 11,2%; bawang merah 5,6% → 7,1%;
daging ayam ras 4,8% → 5,7%; bawang putih 4,2% → 5,3%; garam halus 1,6% → 1,6%; jagung 1,4% → 2,8%; daging sapi 1,3% → 1,8%;
telur ayam ras 1,2% → 3,3%; gula pasir 0,4% → 0,7%; beras medium 0,4% → 1,0%; minyak goreng curah 0,3% → 0,8%; kedelai 0,3% → 0,5%.

**Model lama lebih buruk dari baseline naif di semua komoditas**, dan hanya lebih baik pada 11 dari 165 deret (h = 7) serta 19 dari 165 deret (h = 14).
Penyebab yang paling mungkin: satu model per deret hanya punya ratusan baris latih, sehingga model mempelajari gerakan acak, termasuk
pada komoditas yang harganya hampir tidak pernah berubah.

## 6. Status Normal / Waspada / Lonjakan

- Ambang per komoditas dari sebaran perubahan 7 hari **pada periode latih saja** (sebelumnya dari seluruh data, yang membocorkan
  informasi data uji ke evaluasi status): Waspada = persentil 80 (minimal 2%), Lonjakan = persentil 95. Hanya kenaikan yang berstatus.
- Status = yang paling tinggi dari kelas perubahan **aktual** 7 hari terakhir dan kelas perubahan 7 hari yang **diprediksi**; alasannya ditampilkan.
- Evaluasi kelas "berisiko" (Waspada + Lonjakan) terhadap perubahan aktual 7 hari ke depan: recall, presisi, F1. Recall diutamakan.

Ambang (dari periode latih): cabai merah 18,8% / 42,9%; cabai rawit 11,1% / 33,3%; bawang merah 8,6% / 22,1%; daging ayam ras 4,8% / 10,3%;
bawang putih 2,9% / 10,0%; komoditas stabil 2,0% / sekitar 3% (jagung 2,0% / 6,2%).

Patokan di data uji (10.979 hari uji, 1.231 kejadian berisiko):

| Aturan | Ditandai | Recall | Presisi | F1 |
|---|---|---|---|---|
| Persistensi (aktual 7 hari terakhir saja) | 1.185 | 0,202 | 0,210 | 0,206 |
| Model lama (prediksi saja) | 1.041 | 0,166 | 0,196 | 0,180 |
| Kombinasi: aktual atau model lama | 2.188 | 0,365 | 0,205 | 0,263 |

## 7. Kriteria sukses (dinilai di data uji pada S4)

| Kelompok | Minimum | Target |
|---|---|---|
| Bergejolak, h = 7 dan 14 | MAE model lebih kecil dari naif | MAE ≥ 5% lebih kecil dari naif |
| Stabil, h = 7 dan 14 | MAE model tidak lebih dari 5% lebih buruk dari naif | Sama atau lebih baik dari naif |
| Semua deret | Lebih baik dari model lama | |
| Status (kelas berisiko) | Recall dan F1 lebih tinggi dari persistensi | Recall ≥ 0,40 dengan presisi tidak turun |

Bila kriteria minimum tidak tercapai pada suatu kelompok, hal itu dilaporkan apa adanya, dan aplikasi memakai baseline naif untuk
kelompok itu (diputuskan di S5).

## 8. Perubahan terhadap kode aplikasi yang akan dikerjakan di S6

- Ambang status dihitung dari data latih saja (memperbaiki kebocoran).
- Model gabungan menggantikan model per deret.
- Penyebab rentang prediksi 80% janggal (`lo = min(..., pred)` dan `hi = max(..., pred)` di `pipeline.py`) diperbaiki di S4.
- Tanggal awal Ramadan 2024 di `ml/app/kalender.py` dikoreksi ke ketetapan pemerintah (bagian 9).

## 9. Keputusan tambahan yang disepakati

| Topik | Keputusan |
|---|---|
| Kelompok dan kriteria sukses | Disetujui seperti bagian 3 dan 7 |
| Potret data pemodelan | Notebook dan laporan memakai **data sampai 15 Oktober 2026** (dibekukan), supaya angka dapat direproduksi. Aplikasi tetap melatih ulang dengan seluruh data terbaru dari layanan scraper |
| Data sesudah 15 Oktober 2026 | Dipakai di S5 sebagai uji tambahan pada data yang belum pernah dilihat model |
| Deret berhenti melapor | Garam halus dan susu bubuk Medan Area, kedelai Medan Area: dipakai untuk latih, tidak diberi prediksi di aplikasi |
| Deret kurang dari 90 hari | Jagung Medan Area, kedelai Medan Selayang: dilewati |
| Lubang data (terutama Mei–Juli 2024) | Tidak diisi tebakan; hari tanpa data asli tidak dipakai sebagai hari asal maupun hari target |
| Harga janggal (jagung di sebagian pasar, bawang merah 6 Sep 2024) | Tidak dihapus manual; tetap mengikuti aturan ETL (tolak bila menyimpang > 40% dari median pasar lain). Dibahas sebagai contoh kasus di S5 |
| Kalender hari besar | Semua tanggal memakai ketetapan pemerintah (sidang isbat dan SKB). Awal Ramadan 2024 dikoreksi dari 11 Maret menjadi **12 Maret 2024**. Ramadan 2026 mulai 19 Februari dan Idulfitri 21 Maret 2026 sudah sesuai |

Patokan "model lama" di bagian 5 dan 6 sudah dihitung ulang dengan kalender yang dikoreksi. Perubahannya sangat kecil
(MAE berubah kurang dari Rp2), kecuali jumlah deret tempat model lama mengalahkan naif: 11 (sebelumnya 9) untuk h = 7
dan 19 (sebelumnya 23) untuk h = 14. Kesimpulannya tetap: model lama lebih buruk dari naif di semua komoditas.