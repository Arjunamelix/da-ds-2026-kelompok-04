# Laporan kualitas data

Dibuat otomatis oleh `etl/laporan_kualitas.py` dari `data/raw/master_data_harian.csv` dan hasil `etl/etl_master.py`. Jangan diedit manual; jalankan ulang skripnya bila data berubah.

## Ringkasan sebelum dan sesudah

| Dimensi | Ukuran | Sebelum (mentah) | Sesudah (bersih) |
|---|---|---|---|
| Jumlah baris | baris | 260.864 | 133.218 |
| **Completeness** | baris dengan harga terisi (bukan 0) | 138.704 dari 260.864 (53,2%) | 133.218 dari 133.218 (100%) |
| **Validity** | baris terisi yang lolos semua aturan validasi | 133.218 dari 138.704 (96,0%) | 100% |
| **Consistency** | ejaan nama pasar | 23 ejaan, 12.228 baris berspasi di tepi, ejaan SP2KP berbeda dari SIMPANG | 21 nama baku |
| | nama komoditas dan sumber | nama bebas (`gula pasir`, `simpang_medan`) | kode baku (`gula_pasir`, `SIMPANG`) |
| | komoditas salinan komoditas lain | 0 baris | 0 |
| | satuan telur (per butir dan per kg bercampur) | 3.763 baris per butir | hanya per kg |
| **Uniqueness** | duplikat kunci (tanggal, kecamatan, pasar, komoditas, sumber) | 0 | 0 (dijaga constraint `harga_kunci_unik`) |

## Baris yang dibuang dan alasannya

| Alasan | Baris |
|---|---|
| Harga 0 (tidak ada laporan pada hari itu) | 122.160 |
| satuan per butir, bukan per kg | 3.763 |
| menyimpang > 40% dari median pasar | 1.600 |
| di luar batas wajar | 123 |
| **Total dibuang** | **127.646** |

Rincian per baris ada di `data/processed/master_ditolak.csv`.

## Per sumber dan komoditas

| Sumber | Komoditas | Baris mentah | Terisi | Baris bersih | Hari berdata | Pasar | Periode | Median (Rp) |
|---|---|---|---|---|---|---|---|---|
| SIMPANG | bawang_merah | 21.399 | 12.615 | 12.485 | 618 | 21 | 2024-01-02 s.d. 2026-10-15 | 35.000 |
| SIMPANG | bawang_putih | 21.399 | 12.565 | 12.549 | 612 | 21 | 2024-01-02 s.d. 2026-10-15 | 38.000 |
| SIMPANG | beras_medium | 21.399 | 12.028 | 12.022 | 612 | 21 | 2024-01-02 s.d. 2026-10-15 | 15.500 |
| SIMPANG | cabai_merah | 21.399 | 12.711 | 12.534 | 619 | 21 | 2024-01-02 s.d. 2026-10-15 | 36.000 |
| SIMPANG | cabai_rawit | 21.399 | 12.552 | 12.375 | 618 | 21 | 2024-01-02 s.d. 2026-10-15 | 40.000 |
| SIMPANG | daging_ayam_ras | 21.399 | 10.131 | 10.109 | 521 | 21 | 2024-07-22 s.d. 2026-10-15 | 35.000 |
| SIMPANG | daging_sapi | 21.399 | 11.115 | 11.081 | 611 | 20 | 2024-01-02 s.d. 2026-10-15 | 130.000 |
| SIMPANG | gula_pasir | 21.399 | 12.025 | 12.009 | 613 | 20 | 2024-01-02 s.d. 2026-10-15 | 18.000 |
| SIMPANG | jagung | 21.399 | 9.586 | 8.496 | 607 | 20 | 2024-01-02 s.d. 2026-10-15 | 8.000 |
| SIMPANG | kedelai | 21.399 | 9.166 | 9.153 | 605 | 20 | 2024-01-02 s.d. 2026-10-15 | 16.000 |
| SIMPANG | minyak_goreng_curah | 21.399 | 11.209 | 11.185 | 613 | 21 | 2024-01-02 s.d. 2026-10-15 | 18.500 |
| SIMPANG | telur_ayam_ras | 21.399 | 11.759 | 7.978 | 415 | 20 | 2025-01-16 s.d. 2026-10-15 | 29.250 |
| SP2KP | garam_halus | 2.038 | 630 | 630 | 630 | 2 | 2024-02-02 s.d. 2026-10-15 | 8.000 |
| SP2KP | susu_bubuk | 2.038 | 612 | 612 | 612 | 2 | 2024-02-02 s.d. 2026-10-05 | 55.000 |

## Catatan

- Hari tanpa laporan **tidak diisi** di database; celah diinterpolasi (maksimal 14 hari) hanya di memori layanan ML saat membuat fitur.
- Telur per butir ditolak, tidak dikonversi, karena faktor butir per kg tidak tersedia dari sumber.
- Kejadian serentak di banyak pasar (mis. bawang merah 6 September 2024) tidak tertangkap aturan penyimpangan karena median hari itu ikut berubah; perlu pemeriksaan manual.
