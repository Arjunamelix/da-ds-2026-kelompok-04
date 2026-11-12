package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/go-chi/chi/v5"

	"harga-pangan-medan/backend/internal/config"
)

// ruterScraper merakit hanya rute scraper, tanpa database dan layanan lain.
func ruterScraper(url string) http.Handler {
	h := &Handler{cfg: config.Config{ScraperURL: url}}
	r := chi.NewRouter()
	r.Route("/api", h.rutScraper)
	return r
}

func minta(t *testing.T, srv http.Handler, metode, jalur string) *httptest.ResponseRecorder {
	t.Helper()
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, httptest.NewRequest(metode, jalur, nil))
	return rec
}

func TestScraperDiteruskan(t *testing.T) {
	var jalurDiminta []string
	palsu := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		jalurDiminta = append(jalurDiminta, r.Method+" "+r.URL.Path)
		switch r.URL.Path {
		case "/status":
			_, _ = w.Write([]byte(`{"sedang_berjalan":false,"jadwal":["10:00","16:00"]}`))
		case "/jalankan":
			w.WriteHeader(http.StatusAccepted)
			_, _ = w.Write([]byte(`{"status":"running"}`))
		}
	}))
	defer palsu.Close()
	srv := ruterScraper(palsu.URL)

	rec := minta(t, srv, http.MethodGet, "/api/scraper/status")
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), `"jadwal":["10:00","16:00"]`) {
		t.Fatalf("status: %d %s", rec.Code, rec.Body.String())
	}
	if rec.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("status scraper tidak boleh di-cache")
	}
	rec = minta(t, srv, http.MethodPost, "/api/scraper/jalankan")
	if rec.Code != http.StatusAccepted {
		t.Fatalf("jalankan: %d %s", rec.Code, rec.Body.String())
	}
	if strings.Join(jalurDiminta, ",") != "GET /status,POST /jalankan" {
		t.Fatalf("jalur ke scraper salah: %v", jalurDiminta)
	}
}

func TestScraperSedangBerjalan409(t *testing.T) {
	palsu := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusConflict)
		_, _ = w.Write([]byte(`{"error":"tarikan lain masih berjalan"}`))
	}))
	defer palsu.Close()
	rec := minta(t, ruterScraper(palsu.URL), http.MethodPost, "/api/scraper/jalankan")
	if rec.Code != http.StatusConflict || !strings.Contains(rec.Body.String(), "masih berjalan") {
		t.Fatalf("harus 409 diteruskan: %d %s", rec.Code, rec.Body.String())
	}
}

func TestScraperMati503(t *testing.T) {
	palsu := httptest.NewServer(http.NotFoundHandler())
	url := palsu.URL
	palsu.Close() // alamat tidak lagi didengarkan

	for _, url := range []string{url, ""} {
		rec := minta(t, ruterScraper(url), http.MethodGet, "/api/scraper/status")
		var b errBody
		_ = json.Unmarshal(rec.Body.Bytes(), &b)
		if rec.Code != http.StatusServiceUnavailable || b.Error == "" {
			t.Fatalf("url=%q: harus 503 dengan pesan, dapat %d %s", url, rec.Code, rec.Body.String())
		}
	}
}

func TestScraperGalat502(t *testing.T) {
	for _, isi := range []string{`{"detail":"Internal Server Error"}`, "bukan json"} {
		palsu := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
			w.WriteHeader(http.StatusInternalServerError)
			_, _ = w.Write([]byte(isi))
		}))
		rec := minta(t, ruterScraper(palsu.URL), http.MethodGet, "/api/scraper/status")
		palsu.Close()
		if rec.Code != http.StatusBadGateway {
			t.Fatalf("isi=%q: harus 502, dapat %d", isi, rec.Code)
		}
	}
}