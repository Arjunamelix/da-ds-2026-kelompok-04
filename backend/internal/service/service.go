// Package service berisi logika bisnis: validasi (Project.md 5.4), tulis data, impor, versi_data, dan pemicu retrain.
package service

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"harga-pangan-medan/backend/internal/config"
	"harga-pangan-medan/backend/internal/csvimport"
	"harga-pangan-medan/backend/internal/model"
	"harga-pangan-medan/backend/internal/repository"
)

// ValidasiError dikembalikan bila input tidak lolos aturan 5.4.
type ValidasiError struct {
	Pesan []string
}

func (e *ValidasiError) Error() string { return strings.Join(e.Pesan, "; ") }

type Service struct {
	repo *repository.Repo
	ref  *config.Referensi
	cfg  config.Config
	http *http.Client
}

func New(repo *repository.Repo, ref *config.Referensi, cfg config.Config) *Service {
	return &Service{repo: repo, ref: ref, cfg: cfg, http: &http.Client{Timeout: 10 * time.Second}}
}

func (s *Service) Ref() *config.Referensi { return s.ref }
func (s *Service) Repo() *repository.Repo { return s.repo }

// ---------------------------------------------------------------------------
// Validasi
// ---------------------------------------------------------------------------

// Validasi memeriksa satu baris menurut Project.md 5.4. Mengembalikan baris siap tulis, atau daftar galat.
func (s *Service) Validasi(in model.HargaInput) (model.BarisValid, []string) {
	var errs []string
	in.Tanggal = strings.TrimSpace(in.Tanggal)
	in.Kecamatan = strings.TrimSpace(in.Kecamatan)
	in.NamaPasar = strings.TrimSpace(in.NamaPasar)
	in.Komoditas = strings.TrimSpace(in.Komoditas)
	in.Sumber = strings.TrimSpace(in.Sumber)

	tgl, err := time.Parse("2006-01-02", in.Tanggal)
	if err != nil {
		errs = append(errs, fmt.Sprintf("tanggal %q tidak valid (format YYYY-MM-DD)", in.Tanggal))
	}

	kota := s.ref.Kota
	kecOK := s.ref.KecamatanValid(in.Kecamatan)
	if !kecOK {
		errs = append(errs, fmt.Sprintf("kecamatan %q tidak ada di daftar baku (21 kecamatan atau %q)", in.Kecamatan, kota.Kecamatan))
	}

	if in.NamaPasar == "" {
		errs = append(errs, fmt.Sprintf("nama_pasar tidak boleh kosong (gunakan %q untuk harga level kota)", kota.NamaPasar))
	} else if kecOK {
		switch {
		case in.Kecamatan == kota.Kecamatan && in.NamaPasar != kota.NamaPasar:
			errs = append(errs, fmt.Sprintf("kecamatan %q hanya boleh dipasangkan dengan nama_pasar %q", kota.Kecamatan, kota.NamaPasar))
		case in.Kecamatan != kota.Kecamatan && in.NamaPasar == kota.NamaPasar:
			errs = append(errs, fmt.Sprintf("nama_pasar %q hanya untuk kecamatan %q (harga level kota)", kota.NamaPasar, kota.Kecamatan))
		case in.Kecamatan != kota.Kecamatan:
			kecPasar, ok := s.ref.KecamatanPasar(in.NamaPasar)
			if !ok {
				errs = append(errs, fmt.Sprintf("pasar %q tidak ada di daftar baku", in.NamaPasar))
			} else if kecPasar != in.Kecamatan {
				errs = append(errs, fmt.Sprintf("pasar %q berada di kecamatan %q, bukan %q", in.NamaPasar, kecPasar, in.Kecamatan))
			}
		}
	}

	kom, komOK := s.ref.KomoditasByKode(in.Komoditas)
	if !komOK {
		errs = append(errs, fmt.Sprintf("komoditas %q tidak ada di daftar baku", in.Komoditas))
	}
	if !s.ref.SumberValid(in.Sumber, s.cfg.IsDev()) {
		errs = append(errs, fmt.Sprintf("sumber %q tidak valid", in.Sumber))
	}
	if in.Harga <= 0 {
		errs = append(errs, "harga harus bilangan bulat positif")
	} else if komOK && (in.Harga < kom.Min || in.Harga > kom.Max) {
		errs = append(errs, fmt.Sprintf("harga %d di luar batas wajar %s (%d sampai %d)", in.Harga, kom.Kode, kom.Min, kom.Max))
	}

	if len(errs) > 0 {
		return model.BarisValid{}, errs
	}
	return model.BarisValid{Input: in, Tanggal: tgl, Satuan: kom.Satuan}, nil
}

// ---------------------------------------------------------------------------
// Tulis data
// ---------------------------------------------------------------------------

// HasilTulis balasan operasi CRUD.
type HasilTulis struct {
	Harga           *model.Harga         `json:"harga,omitempty"`
	Peringatan      []string             `json:"peringatan"`
	VersiData       int64                `json:"versi_data"`
	PrediksiSebelum []model.PrediksiSeri `json:"prediksi_sebelum"`
}

func kunciDari(h model.Harga) model.KunciDeret {
	return model.KunciDeret{Kecamatan: h.Kecamatan, NamaPasar: h.NamaPasar, Komoditas: h.Komoditas, Sumber: h.Sumber}
}

func kunciInput(b model.BarisValid) model.KunciDeret {
	return model.KunciDeret{Kecamatan: b.Input.Kecamatan, NamaPasar: b.Input.NamaPasar, Komoditas: b.Input.Komoditas, Sumber: b.Input.Sumber}
}

func (s *Service) peringatanUbah(ctx context.Context, q repository.DBTX, b model.BarisValid, kecualiID int64) ([]string, error) {
	prev, ada, err := s.repo.HargaSebelumnya(ctx, q, b, kecualiID)
	if err != nil || !ada || prev == 0 {
		return nil, err
	}
	d := float64(b.Input.Harga-prev) / float64(prev)
	if d < 0 {
		d = -d
	}
	if d > 0.5 {
		return []string{fmt.Sprintf("harga berubah %.0f%% dari data sebelumnya (%d -> %d); data tetap disimpan, mohon periksa", d*100, prev, b.Input.Harga)}, nil
	}
	return nil, nil
}

// selesaiTulis menaikkan versi_data dan menandai pelatihan berjalan di dalam transaksi, lalu commit dan memicu retrain.
func (s *Service) selesaiTulis(ctx context.Context, tx pgxTx) (int64, error) {
	v, err := s.repo.NaikkanVersiData(ctx, tx)
	if err != nil {
		return 0, err
	}
	if err := s.repo.TandaiMenghitung(ctx, tx); err != nil {
		return 0, err
	}
	if err := tx.Commit(ctx); err != nil {
		return 0, err
	}
	go s.picuRetrain(v)
	return v, nil
}

func (s *Service) Tambah(ctx context.Context, in model.HargaInput) (*HasilTulis, error) {
	b, errs := s.Validasi(in)
	if len(errs) > 0 {
		return nil, &ValidasiError{Pesan: errs}
	}
	tx, err := s.repo.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)

	sebelum, err := s.repo.Prediksi7Untuk(ctx, tx, []model.KunciDeret{kunciInput(b)})
	if err != nil {
		return nil, err
	}
	warn, err := s.peringatanUbah(ctx, tx, b, 0)
	if err != nil {
		return nil, err
	}
	h, err := s.repo.InsertHarga(ctx, tx, b)
	if err != nil {
		return nil, err
	}
	v, err := s.selesaiTulis(ctx, tx)
	if err != nil {
		return nil, err
	}
	return &HasilTulis{Harga: &h, Peringatan: nz(warn), VersiData: v, PrediksiSebelum: sebelum}, nil
}

func (s *Service) Ubah(ctx context.Context, id int64, in model.HargaInput) (*HasilTulis, error) {
	b, errs := s.Validasi(in)
	if len(errs) > 0 {
		return nil, &ValidasiError{Pesan: errs}
	}
	tx, err := s.repo.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)

	lama, err := s.repo.GetHarga(ctx, tx, id)
	if err != nil {
		return nil, err
	}
	sebelum, err := s.repo.Prediksi7Untuk(ctx, tx, uniqKunci([]model.KunciDeret{kunciDari(lama), kunciInput(b)}))
	if err != nil {
		return nil, err
	}
	warn, err := s.peringatanUbah(ctx, tx, b, id)
	if err != nil {
		return nil, err
	}
	h, err := s.repo.UpdateHarga(ctx, tx, id, b)
	if err != nil {
		return nil, err
	}
	v, err := s.selesaiTulis(ctx, tx)
	if err != nil {
		return nil, err
	}
	return &HasilTulis{Harga: &h, Peringatan: nz(warn), VersiData: v, PrediksiSebelum: sebelum}, nil
}

func (s *Service) Hapus(ctx context.Context, id int64) (*HasilTulis, error) {
	tx, err := s.repo.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)

	lama, err := s.repo.GetHarga(ctx, tx, id)
	if err != nil {
		return nil, err
	}
	sebelum, err := s.repo.Prediksi7Untuk(ctx, tx, []model.KunciDeret{kunciDari(lama)})
	if err != nil {
		return nil, err
	}
	if _, err := s.repo.DeleteHarga(ctx, tx, id); err != nil {
		return nil, err
	}
	v, err := s.selesaiTulis(ctx, tx)
	if err != nil {
		return nil, err
	}
	return &HasilTulis{Peringatan: []string{}, VersiData: v, PrediksiSebelum: sebelum}, nil
}

func nz(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

func uniqKunci(in []model.KunciDeret) []model.KunciDeret {
	seen := map[model.KunciDeret]bool{}
	out := []model.KunciDeret{}
	for _, k := range in {
		if !seen[k] {
			seen[k] = true
			out = append(out, k)
		}
	}
	return out
}

// ---------------------------------------------------------------------------
// Impor CSV (idempotent)
// ---------------------------------------------------------------------------

type GalatBaris struct {
	Baris int    `json:"baris"`
	Pesan string `json:"pesan"`
}

type HasilImpor struct {
	TotalBaris      int                  `json:"total_baris"`
	Disisipkan      int                  `json:"disisipkan"`
	Dilewati        int                  `json:"dilewati_sudah_ada"`
	TidakValid      int                  `json:"tidak_valid"`
	Galat           []GalatBaris         `json:"galat"`
	GalatDipotong   bool                 `json:"galat_dipotong"`
	Peringatan      []model.Peringatan   `json:"peringatan"`
	PeringatanTotal int                  `json:"peringatan_total"`
	VersiData       int64                `json:"versi_data"`
	PrediksiSebelum []model.PrediksiSeri `json:"prediksi_sebelum"`
}

const (
	maksGalatDilaporkan = 100
	maksDeretSebelum    = 20
)

// Impor memvalidasi tiap baris, menyisipkan yang valid (yang sudah ada dilewati), dan melaporkan sisanya
// lengkap dengan nomor barisnya.
func (s *Service) Impor(ctx context.Context, r io.Reader) (*HasilImpor, error) {
	baris, err := csvimport.Parse(r)
	if err != nil {
		return nil, &ValidasiError{Pesan: []string{err.Error()}}
	}
	res := &HasilImpor{TotalBaris: len(baris), Galat: []GalatBaris{}, Peringatan: []model.Peringatan{}}
	catat := func(n int, pesan string) {
		res.TidakValid++
		if len(res.Galat) < maksGalatDilaporkan {
			res.Galat = append(res.Galat, GalatBaris{Baris: n, Pesan: pesan})
		} else {
			res.GalatDipotong = true
		}
	}

	valid := make([]model.BarisValid, 0, len(baris))
	for _, b := range baris {
		if b.Galat != "" {
			catat(b.Nomor, b.Galat)
			continue
		}
		harga, err := csvimport.ParseHarga(b.Harga)
		if err != nil {
			catat(b.Nomor, err.Error())
			continue
		}
		bv, errs := s.Validasi(model.HargaInput{
			Tanggal: b.Tanggal, Kecamatan: b.Kecamatan, NamaPasar: b.NamaPasar,
			Komoditas: b.Komoditas, Harga: harga, Sumber: b.Sumber,
		})
		if len(errs) > 0 {
			catat(b.Nomor, strings.Join(errs, "; "))
			continue
		}
		valid = append(valid, bv)
	}

	// Deret yang terdampak (untuk tampilan sebelum -> sesudah).
	kunci := []model.KunciDeret{}
	seen := map[model.KunciDeret]bool{}
	for _, b := range valid {
		k := kunciInput(b)
		if !seen[k] && len(kunci) < maksDeretSebelum {
			seen[k] = true
			kunci = append(kunci, k)
		}
	}

	tx, err := s.repo.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)

	sebelum, err := s.repo.Prediksi7Untuk(ctx, tx, kunci)
	if err != nil {
		return nil, err
	}
	res.PrediksiSebelum = sebelum

	ids, err := s.repo.ImportBatch(ctx, tx, valid)
	if err != nil {
		return nil, err
	}
	res.Disisipkan = len(ids)
	res.Dilewati = len(valid) - len(ids)

	if len(ids) > 0 {
		res.Peringatan, res.PeringatanTotal, err = s.repo.PeringatanLonjakan(ctx, tx, ids)
		if err != nil {
			return nil, err
		}
		v, err := s.selesaiTulis(ctx, tx)
		if err != nil {
			return nil, err
		}
		res.VersiData = v
		return res, nil
	}
	// Tidak ada baris baru: tidak ada perubahan data, versi tidak dinaikkan.
	if err := tx.Commit(ctx); err != nil {
		return nil, err
	}
	if m, err := s.repo.GetMetaStatus(ctx); err == nil {
		res.VersiData = m.VersiData
	}
	return res, nil
}

// ---------------------------------------------------------------------------
// Pemicu pelatihan ulang (asinkron)
// ---------------------------------------------------------------------------

// Latih memicu pelatihan ulang manual (tombol "Latih ulang").
func (s *Service) Latih(ctx context.Context) (int64, error) {
	tx, err := s.repo.Begin(ctx)
	if err != nil {
		return 0, err
	}
	defer tx.Rollback(ctx)
	if err := s.repo.TandaiMenghitung(ctx, tx); err != nil {
		return 0, err
	}
	if err := tx.Commit(ctx); err != nil {
		return 0, err
	}
	m, err := s.repo.GetMetaStatus(ctx)
	if err != nil {
		return 0, err
	}
	go s.picuRetrain(m.VersiData)
	return m.VersiData, nil
}

func (s *Service) picuRetrain(versi int64) {
	body, _ := json.Marshal(map[string]int64{"versi_data": versi})
	req, err := http.NewRequest(http.MethodPost, s.cfg.MLURL+"/retrain", bytes.NewReader(body))
	if err != nil {
		s.galatRetrain(fmt.Sprintf("permintaan retrain gagal dibuat: %v", err))
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := s.http.Do(req)
	if err != nil {
		s.galatRetrain("layanan ML tidak terjangkau: " + err.Error())
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 300))
		s.galatRetrain(fmt.Sprintf("layanan ML menolak retrain (%d): %s", resp.StatusCode, strings.TrimSpace(string(b))))
	}
}

func (s *Service) galatRetrain(pesan string) {
	log.Printf("retrain: %s", pesan)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := s.repo.TandaiError(ctx, pesan); err != nil {
		log.Printf("retrain: gagal menulis status error: %v", err)
	}
}

var ErrTidakDitemukan = repository.ErrTidakDitemukan
var ErrDuplikat = repository.ErrDuplikat

func IsValidasi(err error) (*ValidasiError, bool) {
	var v *ValidasiError
	if errors.As(err, &v) {
		return v, true
	}
	return nil, false
}