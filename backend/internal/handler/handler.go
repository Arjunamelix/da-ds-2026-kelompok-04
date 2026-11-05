// Package handler berisi endpoint HTTP (kontrak API: docs/kontrak_api.md).
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
	"harga-pangan-medan/backend/internal/csvimport"
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

		// Data: CRUD, impor/ekspor (fitur 6 dan 7)
		r.Get("/harga", h.listHarga)
		r.Post("/harga", h.tambahHarga)
		r.Get("/harga/export", h.eksporHarga)
		r.Get("/harga/template", h.templateImpor)
		r.Post("/harga/import", h.imporHarga)
		r.Put("/harga/{id}", h.ubahHarga)
		r.Delete("/harga/{id}", h.hapusHarga)

		// Analitik (fitur 1, 2, 3)
		r.Get("/ringkasan", h.ringkasan)
		r.Get("/tren", h.tren)
		r.Get("/perbandingan", h.perbandingan)

		// Hasil model (fitur 4, 5)
		r.Get("/prediksi", h.prediksi)
		r.Post("/prediksi/sesudah", h.prediksiSesudah)
		r.Get("/status", h.status)
		r.Get("/evaluasi", h.evaluasi)

		// Versi dan pelatihan ulang
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

func badRequest(w http.ResponseWriter, pesan string) {
	writeJSON(w, http.StatusBadRequest, errBody{Error: pesan})
}

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

func idParam(r *http.Request) (int64, error) {
	return strconv.ParseInt(chi.URLParam(r, "id"), 10, 64)
}

func decodeInput(r *http.Request) (model.HargaInput, error) {
	var in model.HargaInput
	r.Body = http.MaxBytesReader(nil, r.Body, 1<<20)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		return in, fmt.Errorf("isi permintaan tidak valid: %v (harga harus angka bulat)", err)
	}
	return in, nil
}

func (h *Handler) listHarga(w http.ResponseWriter, r *http.Request) {
	f, err := parseFilter(r)
	if err != nil {
		badRequest(w, err.Error())
		return
	}
	rows, total, err := h.svc.Repo().ListHarga(r.Context(), f)
	if err != nil {
		writeErr(w, err)
		return
	}
	if f.PerPage <= 0 {
		f.PerPage = 50
	}
	if f.Page <= 0 {
		f.Page = 1
	}
	writeJSON(w, 200, map[string]any{"data": rows, "total": total, "page": f.Page, "per_page": f.PerPage})
}

func (h *Handler) tambahHarga(w http.ResponseWriter, r *http.Request) {
	in, err := decodeInput(r)
	if err != nil {
		badRequest(w, err.Error())
		return
	}
	res, err := h.svc.Tambah(r.Context(), in)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, res)
}

func (h *Handler) ubahHarga(w http.ResponseWriter, r *http.Request) {
	id, err := idParam(r)
	if err != nil {
		badRequest(w, "id tidak valid")
		return
	}
	in, err := decodeInput(r)
	if err != nil {
		badRequest(w, err.Error())
		return
	}
	res, err := h.svc.Ubah(r.Context(), id, in)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

func (h *Handler) hapusHarga(w http.ResponseWriter, r *http.Request) {
	id, err := idParam(r)
	if err != nil {
		badRequest(w, "id tidak valid")
		return
	}
	res, err := h.svc.Hapus(r.Context(), id)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

func (h *Handler) imporHarga(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, h.cfg.MaxUploadMB<<20)
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		badRequest(w, "unggah gagal: "+err.Error()+" (kirim sebagai multipart/form-data dengan field \"file\")")
		return
	}
	f, _, err := r.FormFile("file")
	if err != nil {
		badRequest(w, "field \"file\" tidak ditemukan")
		return
	}
	defer f.Close()
	res, err := h.svc.Impor(r.Context(), f)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

func (h *Handler) eksporHarga(w http.ResponseWriter, r *http.Request) {
	f, err := parseFilter(r)
	if err != nil {
		badRequest(w, err.Error())
		return
	}
	w.Header().Set("Content-Type", "text/csv; charset=utf-8")
	w.Header().Set("Content-Disposition", `attachment; filename="harga_ekspor_`+time.Now().Format("20060102")+`.csv"`)
	cw, err := csvimport.NewPenulis(w)
	if err != nil {
		return
	}
	if err := h.svc.Repo().Export(r.Context(), f, cw.Tulis); err != nil {
		log.Printf("ekspor: %v", err)
		return
	}
	_ = cw.Selesai()
}

func (h *Handler) templateImpor(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/csv; charset=utf-8")
	w.Header().Set("Content-Disposition", `attachment; filename="template_import.csv"`)
	cw, _ := csvimport.NewPenulis(w)
	ref := h.svc.Ref()
	kec, pasar, sumber := "Medan Petisah", "Nama Pasar Baku", "PIHPS"
	if len(ref.Pasar) > 0 {
		kec, pasar = ref.Pasar[0].Kecamatan, ref.Pasar[0].Nama
	}
	_ = cw.Tulis(model.Harga{Tanggal: "2026-10-20", Kecamatan: kec, NamaPasar: pasar, Komoditas: "beras_medium", Harga: 14200, Sumber: sumber})
	_ = cw.Tulis(model.Harga{Tanggal: "2026-10-20", Kecamatan: ref.Kota.Kecamatan, NamaPasar: ref.Kota.NamaPasar, Komoditas: "beras_medium", Harga: 14000, Sumber: sumber})
	_ = cw.Selesai()
}

func (h *Handler) kecamatanQuery(r *http.Request) string {
	if k := strings.TrimSpace(r.URL.Query().Get("kecamatan")); k != "" {
		return k
	}
	return h.svc.Ref().Kota.Kecamatan
}

func (h *Handler) ringkasan(w http.ResponseWriter, r *http.Request) {
	res, err := h.svc.Ringkasan(r.Context(), h.kecamatanQuery(r))
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

func (h *Handler) tren(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	dari, err := parseTanggal(q.Get("dari"))
	if err != nil {
		badRequest(w, err.Error())
		return
	}
	sampai, err := parseTanggal(q.Get("sampai"))
	if err != nil {
		badRequest(w, err.Error())
		return
	}
	res, err := h.svc.Tren(r.Context(), q.Get("komoditas"), q["kecamatan"], dari, sampai)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

func (h *Handler) perbandingan(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	sampai, err := parseTanggal(q.Get("tanggal"))
	if err != nil {
		badRequest(w, err.Error())
		return
	}
	res, err := h.svc.Perbandingan(r.Context(), q.Get("komoditas"), sampai)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

func (h *Handler) prediksi(w http.ResponseWriter, r *http.Request) {
	res, err := h.svc.PrediksiHalaman(r.Context(), r.URL.Query().Get("komoditas"), h.kecamatanQuery(r))
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

func (h *Handler) status(w http.ResponseWriter, r *http.Request) {
	res, err := h.svc.StatusHalaman(r.Context(), h.kecamatanQuery(r))
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

func (h *Handler) evaluasi(w http.ResponseWriter, r *http.Request) {
	kom := r.URL.Query().Get("komoditas")
	ev, err := h.svc.Repo().EvaluasiDeret(r.Context(), kom)
	if err != nil {
		writeErr(w, err)
		return
	}
	st, err := h.svc.Repo().EvaluasiStatus(r.Context())
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, map[string]any{"deret": ev, "status": st})
}

func (h *Handler) versiData(w http.ResponseWriter, r *http.Request) {
	m, err := h.svc.Repo().GetMetaStatus(r.Context())
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, map[string]int64{"versi_data": m.VersiData, "versi_model": m.VersiModel})
}

func (h *Handler) statusHitung(w http.ResponseWriter, r *http.Request) {
	m, err := h.svc.Repo().GetMetaStatus(r.Context())
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, m)
}

func (h *Handler) retrain(w http.ResponseWriter, r *http.Request) {
	v, err := h.svc.Latih(r.Context())
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusAccepted, map[string]any{"status": "running", "versi_data": v})
}

// prediksiSesudah: body = daftar KunciDeret; balasan = prediksi 7 hari terkini deret-deret itu.
func (h *Handler) prediksiSesudah(w http.ResponseWriter, r *http.Request) {
	var kunci []model.KunciDeret
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	if err := json.NewDecoder(r.Body).Decode(&kunci); err != nil {
		badRequest(w, "isi permintaan harus berupa daftar kunci deret: "+err.Error())
		return
	}
	res, err := h.svc.PrediksiSesudah(r.Context(), kunci)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, map[string]any{"prediksi": res})
}