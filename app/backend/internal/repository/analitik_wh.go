package repository

// Query analitik yang membaca data warehouse skema bintang (migrasi 000003): fakta_harga + dim_waktu,
// dim_wilayah, dim_komoditas, dim_sumber. Dipakai halaman Analisis, Cerita, dan kartu KPI.
//
// Deret "kota" = median harga semua pasar pada hari, komoditas, dan sumber yang sama, hanya pada hari dengan
// minimal 3 pasar melapor (aturan yang sama dengan view harga_agregat dan dashboard). Komoditas yang tidak pernah
// dilaporkan 3 pasar pada hari yang sama (garam halus dan susu bubuk dari SP2KP) tidak punya deret kota;
// analisisnya lewat level kecamatan.

import (
	"context"
	"math"
	"time"

	"github.com/jackc/pgx/v5"
)

// FilterAnalitik parameter umum; nil/kosong = tanpa batas.
type FilterAnalitik struct {
	Dari      *time.Time
	Sampai    *time.Time
	Komoditas string
	Kecamatan string
}

func teksAtauNil(s string) any {
	if s == "" {
		return nil
	}
	return s
}

// queryMaps menjalankan query dan mengembalikan baris sebagai map kolom -> nilai (siap di-JSON-kan).
// Kolom pada query dicast eksplisit (::text, ::int, ::float8) agar tipe Go-nya sederhana.
func (r *Repo) queryMaps(ctx context.Context, sql string, args ...any) ([]map[string]any, error) {
	rows, err := r.pool.Query(ctx, sql, args...)
	if err != nil {
		return nil, err
	}
	out, err := pgx.CollectRows(rows, pgx.RowToMap)
	if err != nil {
		return nil, err
	}
	for _, m := range out {
		for k, v := range m {
			if f, ok := v.(float64); ok && (math.IsNaN(f) || math.IsInf(f, 0)) {
				m[k] = nil
			}
		}
	}
	if out == nil {
		out = []map[string]any{}
	}
	return out, nil
}

// VersiData dipakai sebagai kunci cache analitik.
func (r *Repo) VersiData(ctx context.Context) (int64, error) {
	var v int64
	err := r.pool.QueryRow(ctx, `SELECT nilai::bigint FROM meta WHERE kunci = 'versi_data'`).Scan(&v)
	return v, err
}

const minPasarKota = 3

const cteKota = `
kota AS (
  SELECT DISTINCT t.tanggal, t.tahun_bulan, k.kode AS komoditas, k.nama, k.kategori, k.satuan, s.kode AS sumber,
         f.median_kota, f.jumlah_pasar_melapor
  FROM fakta_harga f
  JOIN dim_wilayah w ON w.kunci_wilayah = f.kunci_wilayah AND w.tingkat_wilayah = 'pasar'
  JOIN dim_waktu t ON t.kunci_waktu = f.kunci_waktu
  JOIN dim_komoditas k ON k.kunci_komoditas = f.kunci_komoditas
  JOIN dim_sumber s ON s.kunci_sumber = f.kunci_sumber
  WHERE f.jumlah_pasar_melapor >= 3
    AND ($1::date IS NULL OR t.tanggal >= $1) AND ($2::date IS NULL OR t.tanggal <= $2)
)`

// KPIKomoditas harga kota terakhir tiap komoditas beserta harga sekitar 7 dan 14 hari sebelumnya.
// Hanya membaca 60 hari terakhir agar cepat.
func (r *Repo) KPIKomoditas(ctx context.Context) ([]map[string]any, error) {
	var tmax *time.Time
	if err := r.pool.QueryRow(ctx, `SELECT max(t.tanggal) FROM fakta_harga f JOIN dim_waktu t ON t.kunci_waktu = f.kunci_waktu`).Scan(&tmax); err != nil {
		return nil, err
	}
	if tmax == nil {
		return []map[string]any{}, nil
	}
	dari := tmax.AddDate(0, 0, -60)
	return r.queryMaps(ctx, `
WITH `+cteKota+`,
akhir AS (SELECT komoditas, nama, kategori, satuan, sumber, max(tanggal) AS tmax FROM kota GROUP BY 1,2,3,4,5)
SELECT a.komoditas, a.nama, a.kategori, a.satuan, a.sumber, a.tmax::text AS tanggal,
  (SELECT k.median_kota FROM kota k WHERE k.komoditas = a.komoditas AND k.sumber = a.sumber AND k.tanggal = a.tmax)::float8 AS harga,
  (SELECT k.median_kota FROM kota k WHERE k.komoditas = a.komoditas AND k.sumber = a.sumber
     AND k.tanggal BETWEEN a.tmax - 14 AND a.tmax - 7 ORDER BY k.tanggal DESC LIMIT 1)::float8 AS harga_7h,
  (SELECT k.median_kota FROM kota k WHERE k.komoditas = a.komoditas AND k.sumber = a.sumber
     AND k.tanggal BETWEEN a.tmax - 21 AND a.tmax - 14 ORDER BY k.tanggal DESC LIMIT 1)::float8 AS harga_14h,
  (SELECT k.jumlah_pasar_melapor FROM kota k WHERE k.komoditas = a.komoditas AND k.sumber = a.sumber AND k.tanggal = a.tmax)::int AS pasar
FROM akhir a ORDER BY a.kategori, a.komoditas`, dari, (*time.Time)(nil))
}

// KPIDisparitas selisih harga termahal-termurah antarpasar (% terhadap median) per komoditas:
// rata-rata 7 hari terakhir vs 30 hari sebelumnya.
func (r *Repo) KPIDisparitas(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
WITH harian AS (
  SELECT t.tanggal, k.kode AS komoditas, k.nama,
         (100.0 * (max(f.harga) - min(f.harga)) / percentile_cont(0.5) WITHIN GROUP (ORDER BY f.harga))::float8 AS disparitas_pct
  FROM fakta_harga f
  JOIN dim_wilayah w ON w.kunci_wilayah = f.kunci_wilayah AND w.tingkat_wilayah = 'pasar'
  JOIN dim_waktu t ON t.kunci_waktu = f.kunci_waktu
  JOIN dim_komoditas k ON k.kunci_komoditas = f.kunci_komoditas
  WHERE ($1::date IS NULL OR t.tanggal >= $1) AND ($2::date IS NULL OR t.tanggal <= $2)
  GROUP BY t.tanggal, k.kode, k.nama HAVING count(*) >= 3
), batas AS (SELECT max(tanggal) AS tmax FROM harian)
SELECT h.komoditas, h.nama,
  avg(h.disparitas_pct) FILTER (WHERE h.tanggal > b.tmax - 7)::float8 AS kini,
  avg(h.disparitas_pct) FILTER (WHERE h.tanggal <= b.tmax - 7 AND h.tanggal > b.tmax - 37)::float8 AS pembanding,
  avg(h.disparitas_pct)::float8 AS rata_periode,
  max(h.disparitas_pct)::float8 AS maks_periode
FROM harian h CROSS JOIN batas b GROUP BY 1, 2 ORDER BY rata_periode DESC`, f.Dari, f.Sampai)
}

// KPIPelapor banyak pasar yang melapor pada hari terakhir vs rata-rata 30 hari laporan sebelumnya.
func (r *Repo) KPIPelapor(ctx context.Context) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
WITH harian AS (
  SELECT t.tanggal, count(DISTINCT w.nama_pasar)::int AS pasar
  FROM fakta_harga f
  JOIN dim_wilayah w ON w.kunci_wilayah = f.kunci_wilayah AND w.tingkat_wilayah = 'pasar'
  JOIN dim_waktu t ON t.kunci_waktu = f.kunci_waktu
  GROUP BY t.tanggal
), urut AS (SELECT tanggal, pasar, row_number() OVER (ORDER BY tanggal DESC) AS rn FROM harian)
SELECT (SELECT tanggal::text FROM urut WHERE rn = 1) AS tanggal,
       (SELECT pasar FROM urut WHERE rn = 1) AS kini,
       (SELECT avg(pasar) FROM urut WHERE rn BETWEEN 2 AND 31)::float8 AS pembanding,
       (SELECT count(*) FROM dim_wilayah WHERE tingkat_wilayah = 'pasar')::int AS target`)
}

// Heatmap rata-rata harga kota per komoditas per bulan, indeks terhadap rata-rata periode (=100),
// dan perubahan terhadap bulan sebelumnya.
func (r *Repo) Heatmap(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
WITH `+cteKota+`,
bulan AS (
  SELECT komoditas, nama, kategori, sumber, tahun_bulan, avg(median_kota) AS rata, count(*) AS hari
  FROM kota GROUP BY 1,2,3,4,5
)
SELECT komoditas, nama, kategori, sumber, tahun_bulan, rata::float8 AS rata, hari::int AS hari,
       (100 * rata / avg(rata) OVER (PARTITION BY komoditas, sumber))::float8 AS indeks,
       (100 * (rata / lag(rata) OVER (PARTITION BY komoditas, sumber ORDER BY tahun_bulan) - 1))::float8 AS perubahan_bulanan_pct
FROM bulan ORDER BY kategori, komoditas, tahun_bulan`, f.Dari, f.Sampai)
}

// Mingguan harga kota rata-rata per minggu untuk setiap komoditas (small multiples).
func (r *Repo) Mingguan(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
WITH `+cteKota+`
SELECT komoditas, nama, kategori, satuan, sumber, date_trunc('week', tanggal)::date::text AS minggu,
       avg(median_kota)::float8 AS harga, max(jumlah_pasar_melapor)::int AS pasar
FROM kota GROUP BY 1,2,3,4,5,6 ORDER BY kategori, komoditas, minggu`, f.Dari, f.Sampai)
}

// Sebaran statistik lima angka harga antarpasar per bulan untuk satu komoditas (box plot);
// kecamatan opsional.
func (r *Repo) Sebaran(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
SELECT t.tahun_bulan,
       count(*)::int AS n, count(DISTINCT w.nama_pasar)::int AS pasar,
       min(f.harga)::float8 AS minimum,
       percentile_cont(0.05) WITHIN GROUP (ORDER BY f.harga)::float8 AS p05,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY f.harga)::float8 AS q1,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY f.harga)::float8 AS median,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY f.harga)::float8 AS q3,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY f.harga)::float8 AS p95,
       max(f.harga)::float8 AS maksimum
FROM fakta_harga f
JOIN dim_wilayah w ON w.kunci_wilayah = f.kunci_wilayah AND w.tingkat_wilayah = 'pasar'
JOIN dim_waktu t ON t.kunci_waktu = f.kunci_waktu
JOIN dim_komoditas k ON k.kunci_komoditas = f.kunci_komoditas
WHERE k.kode = $3 AND ($4::text IS NULL OR w.kecamatan = $4)
  AND ($1::date IS NULL OR t.tanggal >= $1) AND ($2::date IS NULL OR t.tanggal <= $2)
GROUP BY t.tahun_bulan ORDER BY t.tahun_bulan`, f.Dari, f.Sampai, f.Komoditas, teksAtauNil(f.Kecamatan))
}

// Wilayah ringkasan per pasar (hierarki kecamatan > pasar) untuk treemap: banyak laporan, rata-rata harga,
// dan rata-rata selisih terhadap median kota. Komoditas opsional (kosong = semua komoditas).
func (r *Repo) Wilayah(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
SELECT w.kecamatan, w.nama_pasar, count(*)::int AS laporan, count(DISTINCT k.kode)::int AS komoditas,
       avg(f.harga)::float8 AS rata_harga, avg(f.selisih_median_kota_pct)::float8 AS selisih_pct
FROM fakta_harga f
JOIN dim_wilayah w ON w.kunci_wilayah = f.kunci_wilayah AND w.tingkat_wilayah = 'pasar'
JOIN dim_waktu t ON t.kunci_waktu = f.kunci_waktu
JOIN dim_komoditas k ON k.kunci_komoditas = f.kunci_komoditas
WHERE ($3::text IS NULL OR k.kode = $3)
  AND ($1::date IS NULL OR t.tanggal >= $1) AND ($2::date IS NULL OR t.tanggal <= $2)
GROUP BY w.kecamatan, w.nama_pasar ORDER BY w.kecamatan, w.nama_pasar`, f.Dari, f.Sampai, teksAtauNil(f.Komoditas))
}

// Deret harian satu komoditas: median kota (kecamatan kosong) atau rata-rata pasar di satu kecamatan.
func (r *Repo) DeretHarian(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
SELECT t.tanggal::text AS tanggal, s.kode AS sumber,
       (CASE WHEN $4::text IS NULL THEN min(f.median_kota) ELSE avg(f.harga) END)::float8 AS harga,
       count(*)::int AS pasar
FROM fakta_harga f
JOIN dim_wilayah w ON w.kunci_wilayah = f.kunci_wilayah AND w.tingkat_wilayah = 'pasar'
JOIN dim_waktu t ON t.kunci_waktu = f.kunci_waktu
JOIN dim_komoditas k ON k.kunci_komoditas = f.kunci_komoditas
JOIN dim_sumber s ON s.kunci_sumber = f.kunci_sumber
WHERE k.kode = $3 AND ($4::text IS NULL OR w.kecamatan = $4)
  AND ($1::date IS NULL OR t.tanggal >= $1) AND ($2::date IS NULL OR t.tanggal <= $2)
GROUP BY t.tanggal, s.kode
HAVING $4::text IS NOT NULL OR count(*) >= $5
ORDER BY t.tanggal`, f.Dari, f.Sampai, f.Komoditas, teksAtauNil(f.Kecamatan), minPasarKota)
}

// HariBesar daftar hari besar pada rentang tanggal (anotasi grafik).
func (r *Repo) HariBesar(ctx context.Context, dari, sampai string) ([]map[string]any, error) {
	return r.queryMaps(ctx, `SELECT tanggal::text AS tanggal, nama FROM ref_hari_besar
		WHERE tanggal BETWEEN $1::date AND $2::date ORDER BY tanggal`, dari, sampai)
}

// Volatilitas simpangan baku perubahan mingguan harga kota per komoditas (hanya minggu yang berurutan).
func (r *Repo) Volatilitas(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
WITH `+cteKota+`,
mg AS (
  SELECT komoditas, nama, kategori, sumber, date_trunc('week', tanggal)::date AS minggu, avg(median_kota) AS h
  FROM kota GROUP BY 1,2,3,4,5
), r AS (
  SELECT *, h / lag(h) OVER w - 1 AS ret, minggu - lag(minggu) OVER w AS jarak
  FROM mg WINDOW w AS (PARTITION BY komoditas, sumber ORDER BY minggu)
)
SELECT komoditas, nama, kategori, sumber, count(ret)::int AS minggu,
       (100 * stddev_samp(ret))::float8 AS volatilitas_pct,
       (100 * avg(abs(ret)))::float8 AS rata_abs_pct,
       (100 * max(ret))::float8 AS naik_maks_pct,
       (100 * min(ret))::float8 AS turun_maks_pct
FROM r WHERE jarak = 7 GROUP BY 1,2,3,4 HAVING count(ret) >= 8 ORDER BY volatilitas_pct DESC`, f.Dari, f.Sampai)
}

// Korelasi antar perubahan mingguan harga kota setiap pasangan komoditas.
func (r *Repo) Korelasi(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
WITH `+cteKota+`,
mg AS (SELECT komoditas, date_trunc('week', tanggal)::date AS minggu, avg(median_kota) AS h FROM kota GROUP BY 1,2),
r AS (
  SELECT komoditas, minggu, h / lag(h) OVER w - 1 AS ret, minggu - lag(minggu) OVER w AS jarak
  FROM mg WINDOW w AS (PARTITION BY komoditas ORDER BY minggu)
), ok AS (SELECT * FROM r WHERE jarak = 7)
SELECT a.komoditas AS komoditas_a, b.komoditas AS komoditas_b, corr(a.ret, b.ret)::float8 AS korelasi, count(*)::int AS minggu
FROM ok a JOIN ok b USING (minggu) GROUP BY 1,2 HAVING count(*) >= 12`, f.Dari, f.Sampai)
}

// HariBesarDampak rata-rata perubahan 7 hari per komoditas: menjelang hari besar (1-7 hari sebelumnya) vs hari lain.
func (r *Repo) HariBesarDampak(ctx context.Context, f FilterAnalitik) ([]map[string]any, error) {
	return r.queryMaps(ctx, `
SELECT k.kode AS komoditas, k.nama, k.kategori, t.menjelang_hari_besar,
       avg(f.perubahan_7h_pct)::float8 AS rata_perubahan_7h_pct, count(f.perubahan_7h_pct)::int AS n
FROM fakta_harga f
JOIN dim_waktu t ON t.kunci_waktu = f.kunci_waktu
JOIN dim_komoditas k ON k.kunci_komoditas = f.kunci_komoditas
WHERE ($1::date IS NULL OR t.tanggal >= $1) AND ($2::date IS NULL OR t.tanggal <= $2)
GROUP BY 1,2,3,4 ORDER BY 3,1,4`, f.Dari, f.Sampai)
}
