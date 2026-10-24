// Package repository berisi seluruh akses ke PostgreSQL.
package repository

import (
	"context"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"harga-pangan-medan/backend/internal/model"
)

var (
	ErrDuplikat       = errors.New("data dengan kunci yang sama sudah ada")
	ErrTidakDitemukan = errors.New("data tidak ditemukan")
)

// DBTX dipenuhi oleh *pgxpool.Pool maupun pgx.Tx.
type DBTX interface {
	Exec(ctx context.Context, sql string, args ...any) (pgconn.CommandTag, error)
	Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error)
	QueryRow(ctx context.Context, sql string, args ...any) pgx.Row
}

type Repo struct {
	pool *pgxpool.Pool
}

func New(pool *pgxpool.Pool) *Repo { return &Repo{pool: pool} }

// DB mengembalikan pool untuk pembacaan di luar transaksi.
func (r *Repo) DB() DBTX { return r.pool }

func (r *Repo) Begin(ctx context.Context) (pgx.Tx, error) { return r.pool.Begin(ctx) }

func isUnique(err error) bool {
	var pe *pgconn.PgError
	return errors.As(err, &pe) && pe.Code == "23505"
}

// ---------------------------------------------------------------------------
// harga: CRUD
// ---------------------------------------------------------------------------

const kolomHarga = `id, tanggal::text, kecamatan, nama_pasar, komoditas, harga, sumber, satuan, tingkat_wilayah, interpolasi, dibuat_pada`

func scanHarga(row pgx.Row) (model.Harga, error) {
	var h model.Harga
	err := row.Scan(&h.ID, &h.Tanggal, &h.Kecamatan, &h.NamaPasar, &h.Komoditas, &h.Harga, &h.Sumber,
		&h.Satuan, &h.TingkatWilayah, &h.Interpolasi, &h.DibuatPada)
	return h, err
}

func (r *Repo) InsertHarga(ctx context.Context, q DBTX, b model.BarisValid) (model.Harga, error) {
	row := q.QueryRow(ctx, `INSERT INTO harga (tanggal, kecamatan, nama_pasar, komoditas, harga, sumber, satuan)
		VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING `+kolomHarga,
		b.Tanggal, b.Input.Kecamatan, b.Input.NamaPasar, b.Input.Komoditas, b.Input.Harga, b.Input.Sumber, b.Satuan)
	h, err := scanHarga(row)
	if isUnique(err) {
		return h, ErrDuplikat
	}
	return h, err
}

func (r *Repo) UpdateHarga(ctx context.Context, q DBTX, id int64, b model.BarisValid) (model.Harga, error) {
	row := q.QueryRow(ctx, `UPDATE harga SET tanggal=$2, kecamatan=$3, nama_pasar=$4, komoditas=$5, harga=$6, sumber=$7, satuan=$8
		WHERE id=$1 RETURNING `+kolomHarga,
		id, b.Tanggal, b.Input.Kecamatan, b.Input.NamaPasar, b.Input.Komoditas, b.Input.Harga, b.Input.Sumber, b.Satuan)
	h, err := scanHarga(row)
	if errors.Is(err, pgx.ErrNoRows) {
		return h, ErrTidakDitemukan
	}
	if isUnique(err) {
		return h, ErrDuplikat
	}
	return h, err
}

func (r *Repo) GetHarga(ctx context.Context, q DBTX, id int64) (model.Harga, error) {
	h, err := scanHarga(q.QueryRow(ctx, `SELECT `+kolomHarga+` FROM harga WHERE id=$1`, id))
	if errors.Is(err, pgx.ErrNoRows) {
		return h, ErrTidakDitemukan
	}
	return h, err
}

func (r *Repo) DeleteHarga(ctx context.Context, q DBTX, id int64) (model.Harga, error) {
	h, err := scanHarga(q.QueryRow(ctx, `DELETE FROM harga WHERE id=$1 RETURNING `+kolomHarga, id))
	if errors.Is(err, pgx.ErrNoRows) {
		return h, ErrTidakDitemukan
	}
	return h, err
}

// HargaSebelumnya harga terakhir pada deret yang sama dengan tanggal lebih awal (untuk peringatan > 50%).
func (r *Repo) HargaSebelumnya(ctx context.Context, q DBTX, b model.BarisValid, kecualiID int64) (int, bool, error) {
	var prev int
	err := q.QueryRow(ctx, `SELECT harga FROM harga
		WHERE kecamatan=$1 AND nama_pasar=$2 AND komoditas=$3 AND sumber=$4 AND tanggal < $5 AND id <> $6
		ORDER BY tanggal DESC LIMIT 1`,
		b.Input.Kecamatan, b.Input.NamaPasar, b.Input.Komoditas, b.Input.Sumber, b.Tanggal, kecualiID).Scan(&prev)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, false, nil
	}
	return prev, err == nil, err
}

type argBuilder struct {
	clauses []string
	args    []any
}

func (a *argBuilder) add(clause string, v any) {
	a.args = append(a.args, v)
	a.clauses = append(a.clauses, strings.Replace(clause, "?", "$"+strconv.Itoa(len(a.args)), 1))
}

func (a *argBuilder) where() string {
	if len(a.clauses) == 0 {
		return ""
	}
	return " WHERE " + strings.Join(a.clauses, " AND ")
}

func filterToBuilder(f model.FilterHarga) *argBuilder {
	b := &argBuilder{}
	if f.Kecamatan != "" {
		b.add("kecamatan = ?", f.Kecamatan)
	}
	if f.NamaPasar != "" {
		b.add("nama_pasar = ?", f.NamaPasar)
	}
	if f.Komoditas != "" {
		b.add("komoditas = ?", f.Komoditas)
	}
	if f.Sumber != "" {
		b.add("sumber = ?", f.Sumber)
	}
	if f.Dari != nil {
		b.add("tanggal >= ?", *f.Dari)
	}
	if f.Sampai != nil {
		b.add("tanggal <= ?", *f.Sampai)
	}
	return b
}

// ListHarga daftar berhalaman beserta total baris yang cocok.
func (r *Repo) ListHarga(ctx context.Context, f model.FilterHarga) ([]model.Harga, int, error) {
	b := filterToBuilder(f)
	var total int
	if err := r.pool.QueryRow(ctx, `SELECT count(*) FROM harga`+b.where(), b.args...).Scan(&total); err != nil {
		return nil, 0, err
	}
	if f.PerPage <= 0 {
		f.PerPage = 50
	}
	if f.Page <= 0 {
		f.Page = 1
	}
	args := append([]any{}, b.args...)
	args = append(args, f.PerPage, (f.Page-1)*f.PerPage)
	sql := fmt.Sprintf(`SELECT %s FROM harga%s ORDER BY tanggal DESC, id DESC LIMIT $%d OFFSET $%d`,
		kolomHarga, b.where(), len(args)-1, len(args))
	rows, err := r.pool.Query(ctx, sql, args...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	out := []model.Harga{}
	for rows.Next() {
		h, err := scanHarga(rows)
		if err != nil {
			return nil, 0, err
		}
		out = append(out, h)
	}
	return out, total, rows.Err()
}

// Export mengalirkan seluruh baris yang cocok (urut tanggal naik) ke fn.
func (r *Repo) Export(ctx context.Context, f model.FilterHarga, fn func(model.Harga) error) error {
	b := filterToBuilder(f)
	rows, err := r.pool.Query(ctx, `SELECT `+kolomHarga+` FROM harga`+b.where()+` ORDER BY tanggal, kecamatan, nama_pasar, komoditas, sumber`, b.args...)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		h, err := scanHarga(rows)
		if err != nil {
			return err
		}
		if err := fn(h); err != nil {
			return err
		}
	}
	return rows.Err()
}

// ---------------------------------------------------------------------------
// impor massal
// ---------------------------------------------------------------------------

// ImportBatch menyisipkan baris lewat tabel sementara (COPY) lalu INSERT ... ON CONFLICT DO NOTHING.
// Mengembalikan id baris yang benar-benar baru; baris yang sudah ada dilewati.
func (r *Repo) ImportBatch(ctx context.Context, tx pgx.Tx, rows []model.BarisValid) ([]int64, error) {
	if len(rows) == 0 {
		return nil, nil
	}
	if _, err := tx.Exec(ctx, `CREATE TEMP TABLE harga_stage (
		tanggal date, kecamatan text, nama_pasar text, komoditas text, harga integer, sumber text, satuan text
	) ON COMMIT DROP`); err != nil {
		return nil, err
	}
	_, err := tx.CopyFrom(ctx, pgx.Identifier{"harga_stage"},
		[]string{"tanggal", "kecamatan", "nama_pasar", "komoditas", "harga", "sumber", "satuan"},
		pgx.CopyFromSlice(len(rows), func(i int) ([]any, error) {
			b := rows[i]
			return []any{b.Tanggal, b.Input.Kecamatan, b.Input.NamaPasar, b.Input.Komoditas, b.Input.Harga, b.Input.Sumber, b.Satuan}, nil
		}))
	if err != nil {
		return nil, err
	}
	res, err := tx.Query(ctx, `INSERT INTO harga (tanggal, kecamatan, nama_pasar, komoditas, harga, sumber, satuan)
		SELECT tanggal, kecamatan, nama_pasar, komoditas, harga, sumber, satuan FROM harga_stage
		ON CONFLICT ON CONSTRAINT harga_kunci_unik DO NOTHING RETURNING id`)
	if err != nil {
		return nil, err
	}
	defer res.Close()
	ids := []int64{}
	for res.Next() {
		var id int64
		if err := res.Scan(&id); err != nil {
			return nil, err
		}
		ids = append(ids, id)
	}
	return ids, res.Err()
}

// PeringatanLonjakan mencari baris (dari id yang diberikan) yang harganya berubah > 50% dari data sebelumnya.
// Mengembalikan maksimal 50 baris dan total yang cocok.
func (r *Repo) PeringatanLonjakan(ctx context.Context, q DBTX, ids []int64) ([]model.Peringatan, int, error) {
	if len(ids) == 0 {
		return nil, 0, nil
	}
	rows, err := q.Query(ctx, `
		WITH s AS (SELECT DISTINCT komoditas, kecamatan, nama_pasar, sumber FROM harga WHERE id = ANY($1)),
		w AS (
			SELECT h.id, h.tanggal, h.kecamatan, h.nama_pasar, h.komoditas, h.harga,
			       LAG(h.harga) OVER (PARTITION BY h.komoditas, h.kecamatan, h.nama_pasar, h.sumber ORDER BY h.tanggal) AS prev
			FROM harga h JOIN s USING (komoditas, kecamatan, nama_pasar, sumber)
		)
		SELECT tanggal::text, kecamatan, nama_pasar, komoditas, prev, harga, count(*) OVER () AS total
		FROM w WHERE id = ANY($1) AND prev IS NOT NULL AND ABS(harga - prev)::float8 / prev > 0.5
		ORDER BY tanggal LIMIT 50`, ids)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	out := []model.Peringatan{}
	total := 0
	for rows.Next() {
		var p model.Peringatan
		if err := rows.Scan(&p.Tanggal, &p.Kecamatan, &p.NamaPasar, &p.Komoditas, &p.Sebelum, &p.Sekarang, &total); err != nil {
			return nil, 0, err
		}
		p.Pesan = fmt.Sprintf("harga berubah lebih dari 50%% (%d -> %d)", p.Sebelum, p.Sekarang)
		out = append(out, p)
	}
	return out, total, rows.Err()
}

// ---------------------------------------------------------------------------
// meta
// ---------------------------------------------------------------------------

func (r *Repo) NaikkanVersiData(ctx context.Context, q DBTX) (int64, error) {
	var v int64
	err := q.QueryRow(ctx, `UPDATE meta SET nilai = (nilai::bigint + 1)::text WHERE kunci = 'versi_data' RETURNING nilai::bigint`).Scan(&v)
	return v, err
}

func (r *Repo) SetMeta(ctx context.Context, q DBTX, kunci, nilai string) error {
	_, err := q.Exec(ctx, `INSERT INTO meta (kunci, nilai) VALUES ($1,$2) ON CONFLICT (kunci) DO UPDATE SET nilai = EXCLUDED.nilai`, kunci, nilai)
	return err
}

// TandaiMenghitung menandai pelatihan ulang sedang berjalan (dipanggil dalam transaksi tulis data).
func (r *Repo) TandaiMenghitung(ctx context.Context, q DBTX) error {
	if err := r.SetMeta(ctx, q, "status_hitung", "running"); err != nil {
		return err
	}
	if err := r.SetMeta(ctx, q, "pesan_hitung", ""); err != nil {
		return err
	}
	return r.SetMeta(ctx, q, "hitung_mulai", time.Now().UTC().Format(time.RFC3339))
}

func (r *Repo) TandaiError(ctx context.Context, pesan string) error {
	if err := r.SetMeta(ctx, r.pool, "pesan_hitung", pesan); err != nil {
		return err
	}
	return r.SetMeta(ctx, r.pool, "status_hitung", "error")
}

func (r *Repo) GetMetaStatus(ctx context.Context) (model.MetaStatus, error) {
	rows, err := r.pool.Query(ctx, `SELECT kunci, nilai FROM meta`)
	if err != nil {
		return model.MetaStatus{}, err
	}
	defer rows.Close()
	m := map[string]string{}
	for rows.Next() {
		var k, v string
		if err := rows.Scan(&k, &v); err != nil {
			return model.MetaStatus{}, err
		}
		m[k] = v
	}
	if err := rows.Err(); err != nil {
		return model.MetaStatus{}, err
	}
	vd, _ := strconv.ParseInt(m["versi_data"], 10, 64)
	vm, _ := strconv.ParseInt(m["versi_model"], 10, 64)
	return model.MetaStatus{
		VersiData: vd, VersiModel: vm, StatusHitung: m["status_hitung"], PesanHitung: m["pesan_hitung"],
		HitungMulai: m["hitung_mulai"], HitungSelesai: m["hitung_selesai"],
	}, rows.Err()
}

// ---------------------------------------------------------------------------
// analitik (fitur 1, 2, 3)
// ---------------------------------------------------------------------------

// TitikTerakhir harga terbaru satu komoditas pada satu deret beserta harga ~7 hari sebelumnya.
type TitikTerakhir struct {
	Komoditas string
	Tanggal   string
	Harga     int
	Harga7H   *int
}

func (r *Repo) TerakhirPerKomoditas(ctx context.Context, kec, pasar, sumber string) ([]TitikTerakhir, error) {
	rows, err := r.pool.Query(ctx, `
		WITH last AS (
			SELECT DISTINCT ON (komoditas) komoditas, tanggal, harga
			FROM harga WHERE kecamatan=$1 AND nama_pasar=$2 AND sumber=$3
			ORDER BY komoditas, tanggal DESC
		)
		SELECT l.komoditas, l.tanggal::text, l.harga,
		  (SELECT h2.harga FROM harga h2
		    WHERE h2.kecamatan=$1 AND h2.nama_pasar=$2 AND h2.sumber=$3 AND h2.komoditas=l.komoditas
		      AND h2.tanggal <= l.tanggal - 7
		    ORDER BY h2.tanggal DESC LIMIT 1) AS harga_7h
		FROM last l`, kec, pasar, sumber)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []TitikTerakhir{}
	for rows.Next() {
		var t TitikTerakhir
		if err := rows.Scan(&t.Komoditas, &t.Tanggal, &t.Harga, &t.Harga7H); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

func (r *Repo) Tren(ctx context.Context, kec, pasar, komoditas, sumber string, dari, sampai *time.Time) ([]model.Titik, error) {
	rows, err := r.pool.Query(ctx, `SELECT tanggal::text, harga FROM harga
		WHERE kecamatan=$1 AND nama_pasar=$2 AND komoditas=$3 AND sumber=$4
		  AND ($5::date IS NULL OR tanggal >= $5::date) AND ($6::date IS NULL OR tanggal <= $6::date)
		ORDER BY tanggal`, kec, pasar, komoditas, sumber, dari, sampai)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []model.Titik{}
	for rows.Next() {
		var t model.Titik
		if err := rows.Scan(&t.Tanggal, &t.Harga); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

// TerakhirBeberapaDeret harga terbaru (<= sampai) satu komoditas untuk sekumpulan deret.
type HargaDeret struct {
	Kecamatan string
	NamaPasar string
	Sumber    string
	Tanggal   string
	Harga     int
}

func (r *Repo) TerakhirBanyakDeret(ctx context.Context, komoditas string, sampai *time.Time, kec, pasar, sumber []string) ([]HargaDeret, error) {
	rows, err := r.pool.Query(ctx, `
		SELECT DISTINCT ON (kecamatan, nama_pasar, sumber) kecamatan, nama_pasar, sumber, tanggal::text, harga
		FROM harga
		WHERE komoditas=$1 AND ($2::date IS NULL OR tanggal <= $2::date)
		  AND (kecamatan, nama_pasar, sumber) IN (SELECT k, p, s FROM unnest($3::text[], $4::text[], $5::text[]) AS t(k, p, s))
		ORDER BY kecamatan, nama_pasar, sumber, tanggal DESC`, komoditas, sampai, kec, pasar, sumber)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []HargaDeret{}
	for rows.Next() {
		var h HargaDeret
		if err := rows.Scan(&h.Kecamatan, &h.NamaPasar, &h.Sumber, &h.Tanggal, &h.Harga); err != nil {
			return nil, err
		}
		out = append(out, h)
	}
	return out, rows.Err()
}

// ---------------------------------------------------------------------------
// hasil model (fitur 4, 5) — dibaca saja; penulisnya layanan Python
// ---------------------------------------------------------------------------

func (r *Repo) PrediksiSeri(ctx context.Context, kec, pasar, sumber string) (map[string][]model.Prediksi, error) {
	rows, err := r.pool.Query(ctx, `SELECT komoditas, horizon, tanggal_dasar::text, harga_dasar, harga_prediksi, batas_bawah, batas_atas
		FROM prediksi WHERE kecamatan=$1 AND nama_pasar=$2 AND sumber=$3 ORDER BY komoditas, horizon`, kec, pasar, sumber)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[string][]model.Prediksi{}
	for rows.Next() {
		var k string
		var p model.Prediksi
		var h int16
		if err := rows.Scan(&k, &h, &p.TanggalDasar, &p.HargaDasar, &p.HargaPrediksi, &p.BatasBawah, &p.BatasAtas); err != nil {
			return nil, err
		}
		p.Horizon = int(h)
		out[k] = append(out[k], p)
	}
	return out, rows.Err()
}

func (r *Repo) StatusSeri(ctx context.Context, kec, pasar, sumber string) (map[string]model.Status, error) {
	rows, err := r.pool.Query(ctx, `SELECT komoditas, status, perubahan_prediksi_pct, ambang_waspada_pct, ambang_lonjakan_pct, tanggal_dasar::text
		FROM status_harga WHERE kecamatan=$1 AND nama_pasar=$2 AND sumber=$3`, kec, pasar, sumber)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[string]model.Status{}
	for rows.Next() {
		var k string
		var s model.Status
		if err := rows.Scan(&k, &s.Status, &s.PerubahanPrediksiPct, &s.AmbangWaspadaPct, &s.AmbangLonjakanPct, &s.TanggalDasar); err != nil {
			return nil, err
		}
		out[k] = s
	}
	return out, rows.Err()
}

func (r *Repo) DilewatiSeri(ctx context.Context, kec, pasar, sumber string) (map[string]model.Dilewati, error) {
	rows, err := r.pool.Query(ctx, `SELECT komoditas, alasan, n_hari FROM deret_dilewati WHERE kecamatan=$1 AND nama_pasar=$2 AND sumber=$3`, kec, pasar, sumber)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[string]model.Dilewati{}
	for rows.Next() {
		var k string
		var d model.Dilewati
		if err := rows.Scan(&k, &d.Alasan, &d.NHari); err != nil {
			return nil, err
		}
		out[k] = d
	}
	return out, rows.Err()
}

// EvaluasiDeret metrik walk-forward; komoditas/kecamatan/pasar/sumber opsional (kosong = semua).
func (r *Repo) EvaluasiDeret(ctx context.Context, komoditas string) ([]model.Evaluasi, error) {
	b := &argBuilder{}
	if komoditas != "" {
		b.add("komoditas = ?", komoditas)
	}
	rows, err := r.pool.Query(ctx, `SELECT kecamatan, nama_pasar, komoditas, sumber, horizon, n_uji,
		mae_model, rmse_model, mape_model, mae_baseline, rmse_baseline, mape_baseline, mengalahkan_baseline
		FROM evaluasi_model`+b.where()+` ORDER BY komoditas, kecamatan, nama_pasar, sumber, horizon`, b.args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []model.Evaluasi{}
	for rows.Next() {
		var e model.Evaluasi
		var h int16
		if err := rows.Scan(&e.Kecamatan, &e.NamaPasar, &e.Komoditas, &e.Sumber, &h, &e.NUji,
			&e.MAEModel, &e.RMSEModel, &e.MAPEModel, &e.MAEBaseline, &e.RMSEBaseline, &e.MAPEBaseline, &e.MengalahkanBaseline); err != nil {
			return nil, err
		}
		e.Horizon = int(h)
		out = append(out, e)
	}
	return out, rows.Err()
}

func (r *Repo) EvaluasiStatus(ctx context.Context) ([]model.EvaluasiStatus, error) {
	rows, err := r.pool.Query(ctx, `SELECT komoditas, n_uji, n_berisiko, recall_berisiko, presisi_berisiko, ambang_waspada_pct, ambang_lonjakan_pct
		FROM evaluasi_status ORDER BY komoditas`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []model.EvaluasiStatus{}
	for rows.Next() {
		var e model.EvaluasiStatus
		if err := rows.Scan(&e.Komoditas, &e.NUji, &e.NBerisiko, &e.RecallBerisiko, &e.PresisiBerisiko, &e.AmbangWaspadaPct, &e.AmbangLonjakanPct); err != nil {
			return nil, err
		}
		out = append(out, e)
	}
	return out, rows.Err()
}

// Prediksi7Untuk membaca prediksi 7 hari dari sekumpulan deret (untuk tampilan sebelum -> sesudah).
func (r *Repo) Prediksi7Untuk(ctx context.Context, q DBTX, kunci []model.KunciDeret) ([]model.PrediksiSeri, error) {
	out := []model.PrediksiSeri{}
	for _, k := range kunci {
		var v float64
		err := q.QueryRow(ctx, `SELECT harga_prediksi FROM prediksi
			WHERE kecamatan=$1 AND nama_pasar=$2 AND komoditas=$3 AND sumber=$4 AND horizon=7`,
			k.Kecamatan, k.NamaPasar, k.Komoditas, k.Sumber).Scan(&v)
		if errors.Is(err, pgx.ErrNoRows) {
			continue
		}
		if err != nil {
			return nil, err
		}
		out = append(out, model.PrediksiSeri{KunciDeret: k, Prediksi7: v})
	}
	return out, nil
}