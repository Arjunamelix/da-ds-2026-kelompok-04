# Visualisasi dan interaktivitas dashboard

Pemetaan visual di aplikasi terhadap syarat panduan proyek (4.2 Visualisasi Advance). Visual baru membaca
data warehouse (`docs/warehouse.md`) lewat endpoint `/api/analitik/*` (`backend/internal/handler/analitik_wh.go`).

## Daftar visual (16; syarat minimal 10)

| No | Halaman | Visual | Jenis | Lanjutan? | Interaksi |
|---|---|---|---|---|---|
| 1 | Dashboard | 4 kartu KPI dengan pembanding | kartu KPI | - | - |
| 2 | Dashboard | Perubahan harga 7 hari per komoditas | batang divergen | - | tooltip |
| 3 | Tren | Tren harga sampai 3 kecamatan | garis | - | filter, tooltip |
| 4 | Tren | Peta sebaran harga 21 kecamatan | **peta choropleth** | ya | klik kecamatan = filter grafik tren, tooltip |
| 5 | Perbandingan | Harga 21 kecamatan, terurut, garis acuan kota | batang | - | tooltip |
| 6 | Prediksi | Harga aktual, prediksi 7/14 hari, rentang 80% | garis + area | - | tooltip |
| 7 | Analisis | Pola musiman komoditas x bulan (indeks / perubahan bulanan) | **heatmap** | ya | klik sel = filter silang komoditas + bulan, tooltip |
| 8 | Analisis | Harga harian dengan hari besar, celah data, dan lonjakan | **deret waktu beranotasi** | ya | tooltip |
| 9 | Analisis | Sebaran harga antarpasar per bulan | **box plot** | ya | klik bulan = telusur ke bulan itu, tooltip |
| 10 | Analisis | Kelengkapan laporan dan harga per wilayah | **treemap** | ya | klik kecamatan = telusur Kota > kecamatan > pasar + filter silang, tooltip |
| 11 | Analisis | Tren mingguan semua komoditas | **small multiples** | ya | klik panel = pilih komoditas, tooltip |
| 12 | Analisis | Korelasi perubahan harga antarkomoditas | heatmap | ya | klik baris = pilih komoditas, tooltip |
| 13 | Cerita | Menjelang hari besar vs hari biasa per kategori | batang berkelompok | - | tooltip |
| 14 | Cerita | Volatilitas mingguan per komoditas | batang | - | tooltip |
| 15 | Cerita | Selisih harga termahal-termurah antarpasar | batang | - | tooltip |
| 16 | Cerita | Selisih tiap pasar terhadap median kota | batang divergen | - | tooltip |
| 17 | Cerita | Akurasi model vs baseline per komoditas (setelah model dilatih) | batang berkelompok | - | tooltip |

Jenis lanjutan yang dipakai: **choropleth, heatmap, deret waktu beranotasi, box plot, treemap, small multiples** (6; syarat minimal 5).

## Interaktivitas (syarat panduan)

| Syarat | Implementasi |
|---|---|
| Filter global | Halaman Analisis: komoditas, kecamatan, dan rentang waktu (3 bulan, 6 bulan, 1 tahun, semua, atau satu bulan) berlaku untuk semua grafik di halaman dan tersimpan di URL (tampilan bisa dibagikan) |
| Drill-down hierarki | Treemap: Kota Medan > kecamatan > pasar (remah roti untuk naik); box plot: rentang waktu > satu bulan |
| Cross-filtering | Klik sel heatmap mengubah komoditas dan bulan untuk deret, box plot, dan treemap; klik kecamatan di treemap menyaring deret dan box plot; klik panel small multiples mengubah komoditas |
| Tooltip informatif | Semua visual; tooltip menyebut angka, satuan, jumlah pasar/laporan, dan pembanding |

## Kartu KPI (syarat minimal 4, dengan pembanding)

| KPI | Pembanding |
|---|---|
| Rata-rata perubahan harga 7 hari (median kota, semua komoditas) | minggu sebelumnya |
| Jumlah komoditas yang naik lebih dari 5% dalam 7 hari | minggu sebelumnya |
| Selisih harga antarpasar (termahal - termurah) / median | rata-rata 30 hari sebelumnya |
| Jumlah pasar yang melapor pada hari terakhir | rata-rata 30 hari laporan sebelumnya, target 21 pasar |

## Halaman storytelling (Cerita)

Lima temuan; judul tiap grafik berupa temuannya sendiri dan **dihitung dari data terbaru**, sehingga tetap benar bila data
bertambah. Setiap temuan diberi artinya bagi konsumen, pedagang, dan pemerintah.

Aturan yang dipakai saat memilih angka untuk judul:
- Komoditas dengan catatan kualitas data (`CATATAN_DATA` di `frontend/src/components/viz/util.js`: jagung dan kedelai,
  yang selisih antarpasarnya konsisten per pasar sehingga kemungkinan jenisnya berbeda) tetap tampil di grafik dengan
  warna abu, tetapi tidak dipakai untuk judul.
- Pasar dengan data terbatas (kurang dari 5 komoditas, atau kurang dari separuh jumlah laporan pasar pada umumnya,
  mis. Pasar Induk) tidak dipakai untuk judul temuan 4.

## Aturan warna

- Satu warna untuk besaran satu seri (biru `#2a78d6`).
- Polaritas (naik/turun, di atas/di bawah median): oranye `#eb6834` - abu netral - biru; tidak pernah pelangi.
- Abu `#9aa3b2` untuk pembanding (hari biasa, baseline) dan data dengan catatan.
- Palet diuji untuk buta warna; karena aqua dan abu kontrasnya rendah, setiap batang diberi label angka.

## Endpoint analitik

Semua hanya membaca warehouse dan di-cache di memori backend sampai `versi_data` berubah.

| Endpoint | Isi |
|---|---|
| `GET /api/analitik/kpi` | 4 KPI + perubahan 7 hari per komoditas + selisih antarpasar per komoditas |
| `GET /api/analitik/heatmap?dari&sampai` | rata-rata harga kota per komoditas per bulan, indeks, perubahan bulanan |
| `GET /api/analitik/mingguan?dari&sampai` | rata-rata harga kota per minggu per komoditas |
| `GET /api/analitik/sebaran?komoditas&kecamatan&dari&sampai` | statistik lima angka harga antarpasar per bulan |
| `GET /api/analitik/wilayah?komoditas&dari&sampai` | per pasar: banyak laporan, rata-rata harga, selisih terhadap median kota |
| `GET /api/analitik/deret?komoditas&kecamatan&dari&sampai` | harga harian (median kota atau rata-rata kecamatan) + daftar hari besar |
| `GET /api/analitik/statistik?dari&sampai` | volatilitas, korelasi, dampak hari besar, selisih antarpasar |

Angka level kota memakai aturan yang sama dengan dashboard: median harga pasar pada hari dengan minimal 3 pasar melapor.
Garam halus dan susu bubuk (SP2KP, 2 pasar yang tidak pernah melapor pada hari yang sama) karena itu hanya tersedia di level kecamatan.
