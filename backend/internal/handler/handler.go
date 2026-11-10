// Package handler merakit dan menangani endpoint HTTP API (kontrak API: docs/kontrak_api.md).
package handler

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"

	"harga-pangan-medan/backend/internal/config"
	"harga-pangan-medan/backend/internal/model"
	"harga-pangan-medan/backend/internal/repository"
	"harga-pangan-medan/backend/internal/service"
)

type Handler struct {
	svc *service.Service
	cfg config.Config
}

func New(svc *service.Service, cfg config.Config) *Handler { return &Handler{svc: svc, cfg: cfg} }

// Router merakit semua rute di bawah /api.
func (h *Handler) Router() http.Handler {
	r := chi.NewRouter()
	r.Use(middleware.RealIP, middleware.Recoverer)
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins: h.cfg.CORSOrigins,
		AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders: []string{"Content-Type", "Accept"},
		MaxAge:         300,
	}))

	r.Route("/api", func(r chi.Router) {
		r.Get("/health", func(w http.ResponseWriter, _ *http.Request) { writeJSON(w, 200, map[string]string{"status": "ok"}) })
		r.Get("/referensi", func(w http.ResponseWriter, _ *http.Request) { writeJSON(w, 200, h.svc.Referensi()) })

		// Data: CRUD, impor/ekspor (diatur di harga.go)
		r.Get("/harga", h.listHarga)
		r.Post("/harga", h.tambahHarga)
		r.Get("/harga/export", h.eksporHarga)
		r.Get("/harga/template", h.templateImpor)
		r.Post("/harga/import", h.imporHarga)
		r.Put("/harga/{id}", h.ubahHarga)
		r.Delete("/harga/{id}", h.hapusHarga)

		// Analitik (diatur di ringkasan.go, tren.go, perbandingan.go)
		r.Get("/ringkasan", h.ringkasan)
		r.Get("/tren", h.tren)
		r.Get("/perbandingan", h.perbandingan)

		// Hasil model (diatur di prediksi.go)
		r.Get("/prediksi", h.prediksi)
		r.Post("/prediksi/sesudah", h.prediksiSesudah)
		r.Get("/status", h.status)
		r.Get("/evaluasi", h.evaluasi)

		// Versi dan pelatihan ulang (diatur di prediksi.go)
		r.Get("/versi-data", h.versiData)
		r.Get("/status-hitung", h.statusHitung)
		r.Post("/retrain", h.retrain)

		// Analitik dari data warehouse (halaman Analisis, Cerita, kartu KPI): analitik_wh.go
		h.rutAnalitik(r)

		// Pengambilan data otomatis (layanan scraper): scraper.go
		h.rutScraper(r)
	})
	return r
}

// writeJSON adalah helper untuk mengirim balasan JSON terstandar.
func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("tulis json: %v", err)
	}
}

type errBody struct {
	Error  string   `json:"error"`
	Detail []string `json:"detail,omitempty"`
}

// writeErr adalah helper penanganan galat HTTP terpusat.
func writeErr(w http.ResponseWriter, err error) {
	if v, ok := service.IsValidasi(err); ok {
		writeJSON(w, http.StatusUnprocessableEntity, errBody{Error: "validasi gagal", Detail: v.Pesan})
		return
	}
	switch {
	case errors.Is(err, repository.ErrDuplikat):
		writeJSON(w, http.StatusConflict, errBody{Error: err.Error()})
	case errors.Is(err, repository.ErrTidakDitemukan):
		writeJSON(w, http.StatusNotFound, errBody{Error: err.Error()})
	default:
		log.Printf("galat internal: %v", err)
		writeJSON(w, http.StatusInternalServerError, errBody{Error: "terjadi kesalahan pada server"})
	}
}

// badRequest merespons galat 400 Bad Request.
func badRequest(w http.ResponseWriter, pesan string) {
	writeJSON(w, http.StatusBadRequest, errBody{Error: pesan})
}

// parseTanggal memparsing string YYYY-MM-DD ke *time.Time.
func parseTanggal(s string) (*time.Time, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil, nil
	}
	t, err := time.Parse("2006-01-02", s)
	if err != nil {
		return nil, fmt.Errorf("tanggal %q tidak valid (YYYY-MM-DD)", s)
	}
	return &t, nil
}

// parseFilter mengekstrak parameter query harga dari request URL.
func parseFilter(r *http.Request) (model.FilterHarga, error) {
	q := r.URL.Query()
	f := model.FilterHarga{
		Kecamatan: q.Get("kecamatan"), NamaPasar: q.Get("pasar"), Komoditas: q.Get("komoditas"), Sumber: q.Get("sumber"),
	}
	var err error
	if f.Dari, err = parseTanggal(q.Get("dari")); err != nil {
		return f, err
	}
	if f.Sampai, err = parseTanggal(q.Get("sampai")); err != nil {
		return f, err
	}
	f.Page, _ = strconv.Atoi(q.Get("page"))
	f.PerPage, _ = strconv.Atoi(q.Get("per_page"))
	if f.PerPage > 500 {
		f.PerPage = 500
	}
	return f, nil
}

// idParam mengekstrak parameter numerik {id} dari URL path.
func idParam(r *http.Request) (int64, error) {
	return strconv.ParseInt(chi.URLParam(r, "id"), 10, 64)
}

// decodeInput memvalidasi dan mendecode payload JSON ke model.HargaInput.
func decodeInput(r *http.Request) (model.HargaInput, error) {
	var in model.HargaInput
	r.Body = http.MaxBytesReader(nil, r.Body, 1<<20)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		return in, fmt.Errorf("isi permintaan tidak valid: %v (harga harus angka bulat)", err)
	}
	return in, nil
}

// kecamatanQuery mengambil nama kecamatan dari parameter URL atau default KOTA MEDAN.
func (h *Handler) kecamatanQuery(r *http.Request) string {
	if k := strings.TrimSpace(r.URL.Query().Get("kecamatan")); k != "" {
		return k
	}
	return h.svc.Ref().Kota.Kecamatan
}
