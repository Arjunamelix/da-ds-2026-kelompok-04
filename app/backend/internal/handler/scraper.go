package handler

// Endpoint layanan scraper (pengambil data harga otomatis dari SIMPANG, folder app/scraper/ di repo).
// Backend hanya meneruskan permintaan ke service scraper di jaringan Docker (SCRAPER_URL);
// frontend tidak pernah berbicara langsung dengan scraper, sama seperti dengan layanan ML.
//
//   GET  /api/scraper/status    -> sedang berjalan atau tidak, jadwal, tarikan terakhir, riwayat
//   POST /api/scraper/jalankan  -> mulai tarikan sekarang: 202, atau 409 bila tarikan lain masih berjalan
//
// Bila scraper mati atau belum dinyalakan, balasannya 503 dengan pesan jelas; endpoint lain tetap jalan.

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
)

const (
	batasWaktuScraper = 10 * time.Second // /status dan /jalankan menjawab cepat; tarikannya sendiri berjalan di latar
	batasBalasan      = 1 << 20          // 1 MB
)

var klienScraper = &http.Client{Timeout: batasWaktuScraper}

// rutScraper dipasang di dalam r.Route("/api", ...) pada handler.go.
func (h *Handler) rutScraper(r chi.Router) {
	r.Route("/scraper", func(r chi.Router) {
		r.Get("/status", h.teruskanScraper(http.MethodGet, "/status"))
		r.Post("/jalankan", h.teruskanScraper(http.MethodPost, "/jalankan"))
	})
}

// teruskanScraper meneruskan permintaan ke layanan scraper dan mengembalikan balasannya apa adanya
// (200, 202, 409). Galat di sisi scraper menjadi 502, scraper tak terjangkau menjadi 503.
func (h *Handler) teruskanScraper(metode, jalur string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if h.cfg.ScraperURL == "" {
			writeJSON(w, http.StatusServiceUnavailable, errBody{Error: "layanan scraper tidak diatur (SCRAPER_URL kosong)"})
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), batasWaktuScraper)
		defer cancel()
		req, err := http.NewRequestWithContext(ctx, metode, h.cfg.ScraperURL+jalur, nil)
		if err != nil {
			writeErr(w, err)
			return
		}
		res, err := klienScraper.Do(req)
		if err != nil {
			log.Printf("scraper %s %s: %v", metode, jalur, err)
			pesan := "layanan scraper tidak dapat dihubungi"
			if errors.Is(err, context.DeadlineExceeded) {
				pesan = "layanan scraper tidak menjawab dalam " + batasWaktuScraper.String()
			}
			writeJSON(w, http.StatusServiceUnavailable, errBody{Error: pesan,
				Detail: []string{"pastikan service scraper berjalan: docker compose ps"}})
			return
		}
		defer res.Body.Close()

		isi, err := io.ReadAll(io.LimitReader(res.Body, batasBalasan))
		if err != nil || !json.Valid(isi) {
			log.Printf("scraper %s %s: balasan tidak valid (HTTP %d, err=%v)", metode, jalur, res.StatusCode, err)
			writeJSON(w, http.StatusBadGateway, errBody{Error: "balasan layanan scraper tidak valid"})
			return
		}
		kode := res.StatusCode
		if kode >= 500 {
			log.Printf("scraper %s %s: HTTP %d: %s", metode, jalur, kode, isi)
			writeJSON(w, http.StatusBadGateway, errBody{Error: "layanan scraper mengalami galat"})
			return
		}
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		w.WriteHeader(kode)
		_, _ = w.Write(isi)
	}
}