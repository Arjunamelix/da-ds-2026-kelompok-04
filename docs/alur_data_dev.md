# Alur data

Prinsip Project.md: **tidak ada angka buatan di dataset.** Tabel `harga` hanya berisi data asli per pasar.

## Data SIMPANG (sumber saat ini)
1. Simpan CSV mentah apa adanya di `data/raw/simpang/data_harian_simpang_medan.csv`.
2. `make etl` (`scripts/etl_simpang.py`):
   - harga 0 = tidak ada data pada hari itu, dibuang (bukan harga nol);
   - nama dirapikan (spasi di tepi), nama komoditas dipetakan ke kode baku;
   - harga di luar batas wajar (`config/referensi.json`) ditolak;
   - harga yang menyimpang > 40% dari median pasar lain hari itu (bila >= 5 pasar melapor) ditolak sebagai dugaan salah input;
   - `Rata_Rata_Kecamatan` tidak diimpor (turunan; dihitung ulang oleh view).
   Baris yang ditolak ditulis ke `data/processed/simpang_ditolak.csv` beserta alasannya.
3. `make import-data` mengirim `data/processed/harga_harian_simpang.csv` ke `/api/harga/import` (idempoten).
4. Layanan ML melatih ulang otomatis setelah `versi_data` naik.

## Deret agregat (view `harga_agregat`)
| Tingkat | Cara hitung |
|---|---|
| pasar | data asli apa adanya |
| kecamatan | rata-rata harga pasar di kecamatan itu pada hari itu |
| kota (`KOTA MEDAN`) | median harga semua pasar pada hari itu (minimal 3 pasar melapor) |

Dashboard dan model memakai tingkat kecamatan dan kota. Kecamatan tanpa pasar di sumber ditampilkan "tidak ada data" (tanpa tebakan).

## Menambah sumber lain (mis. PIHPS)
Tambahkan pasar dan komoditas baru di `config/referensi.json`, buat skrip ETL baru di `scripts/`, lalu impor lewat jalur yang sama.
Satu deret tidak boleh dicampur dari dua sumber (kolom `sumber`).

## Data sintetis (opsional, hanya untuk uji)
`python scripts/gen_data_dev.py` membuat CSV sumber `DEV` di `data/dev/` (diabaikan git). Tidak boleh dipakai di laporan.
