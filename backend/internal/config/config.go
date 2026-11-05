// Package config memuat variabel lingkungan dan config/referensi.json.
package config

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

// Config berisi pengaturan proses (dari variabel lingkungan).
type Config struct {
	Port          string
	DatabaseURL   string
	MLURL         string
	ScraperURL    string
	ReferensiPath string
	AppEnv        string
	CORSOrigins   []string
	MaxUploadMB   int64
}

func env(k, def string) string {
	if v := strings.TrimSpace(os.Getenv(k)); v != "" {
		return v
	}
	return def
}

// Load membaca konfigurasi dari lingkungan dengan nilai bawaan untuk pengembangan lokal.
func Load() Config {
	origins := []string{}
	for _, o := range strings.Split(env("CORS_ORIGIN", "http://localhost:5173,http://localhost:3000"), ",") {
		if o = strings.TrimSpace(o); o != "" {
			origins = append(origins, o)
		}
	}
	return Config{
		Port:          env("PORT", env("BACKEND_PORT", "8080")),
		DatabaseURL:   env("DATABASE_URL", "postgres://pangan:pangan@localhost:5432/harga_pangan?sslmode=disable"),
		MLURL:         strings.TrimRight(env("ML_URL", "http://localhost:8000"), "/"),
		ScraperURL:    strings.TrimRight(env("SCRAPER_URL", "http://localhost:8001"), "/"),
		ReferensiPath: env("REFERENSI_PATH", "../config/referensi.json"),
		AppEnv:        env("APP_ENV", "dev"),
		CORSOrigins:   origins,
		MaxUploadMB:   64,
	}
}

// IsDev true bila sumber DEV (data sintetis) boleh dipakai.
func (c Config) IsDev() bool { return c.AppEnv != "prod" }

type KomoditasRef struct {
	Kode     string `json:"kode"`
	Nama     string `json:"nama"`
	Satuan   string `json:"satuan"`
	Min      int    `json:"min"`
	Max      int    `json:"max"`
	Kelompok string `json:"kelompok"`
}

type SumberRef struct {
	Kode    string `json:"kode"`
	Nama    string `json:"nama"`
	DevSaja bool   `json:"dev_saja"`
}

type PasarRef struct {
	Nama      string `json:"nama"`
	Kecamatan string `json:"kecamatan"`
}

type Acuan struct {
	Pasar  string `json:"pasar"`
	Sumber string `json:"sumber"`
}

// Seri mengidentifikasi satu deret harga (di luar komoditas).
type Seri struct {
	Kecamatan string `json:"kecamatan"`
	NamaPasar string `json:"nama_pasar"`
	Sumber    string `json:"sumber"`
}

type KotaRef struct {
	Kecamatan string `json:"kecamatan"`
	NamaPasar string `json:"nama_pasar"`
}

type Referensi struct {
	StatusKonfigurasi string           `json:"status_konfigurasi"`
	Kota              KotaRef          `json:"kota"`
	SumberUtamaKota   string           `json:"sumber_utama_kota"`
	Sumber            []SumberRef      `json:"sumber"`
	Kecamatan         []string         `json:"kecamatan"`
	Komoditas         []KomoditasRef   `json:"komoditas"`
	Pasar             []PasarRef       `json:"pasar"`
	PemetaanKecamatan map[string]Acuan `json:"pemetaan_kecamatan"`

	komoditasIdx map[string]KomoditasRef
	pasarIdx     map[string]string
	sumberIdx    map[string]SumberRef
	kecamatanSet map[string]bool
}

// LoadReferensi membaca dan memeriksa konsistensi referensi.json.
func LoadReferensi(path string) (*Referensi, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("baca referensi: %w", err)
	}
	var r Referensi
	if err := json.Unmarshal(b, &r); err != nil {
		return nil, fmt.Errorf("parse referensi: %w", err)
	}
	if err := r.siapkan(); err != nil {
		return nil, err
	}
	return &r, nil
}

func (r *Referensi) siapkan() error {
	r.komoditasIdx = map[string]KomoditasRef{}
	for _, k := range r.Komoditas {
		if k.Min <= 0 || k.Max < k.Min {
			return fmt.Errorf("batas harga komoditas %s tidak valid", k.Kode)
		}
		r.komoditasIdx[k.Kode] = k
	}
	r.sumberIdx = map[string]SumberRef{}
	for _, s := range r.Sumber {
		r.sumberIdx[s.Kode] = s
	}
	r.kecamatanSet = map[string]bool{}
	for _, k := range r.Kecamatan {
		r.kecamatanSet[k] = true
	}
	if len(r.Kecamatan) != 21 {
		return fmt.Errorf("daftar kecamatan harus 21, ditemukan %d", len(r.Kecamatan))
	}
	r.pasarIdx = map[string]string{}
	for _, p := range r.Pasar {
		if !r.kecamatanSet[p.Kecamatan] {
			return fmt.Errorf("pasar %q merujuk kecamatan tak dikenal %q", p.Nama, p.Kecamatan)
		}
		r.pasarIdx[p.Nama] = p.Kecamatan
	}
	if _, ok := r.sumberIdx[r.SumberUtamaKota]; !ok {
		return fmt.Errorf("sumber_utama_kota %q tidak ada di daftar sumber", r.SumberUtamaKota)
	}
	for kec, a := range r.PemetaanKecamatan {
		if !r.kecamatanSet[kec] {
			return fmt.Errorf("pemetaan: kecamatan %q tidak dikenal", kec)
		}
		if _, ok := r.pasarIdx[a.Pasar]; !ok {
			return fmt.Errorf("pemetaan %q: pasar %q tidak ada di daftar pasar", kec, a.Pasar)
		}
		if _, ok := r.sumberIdx[a.Sumber]; !ok {
			return fmt.Errorf("pemetaan %q: sumber %q tidak dikenal", kec, a.Sumber)
		}
	}
	return nil
}

// KomoditasByKode mencari komoditas baku.
func (r *Referensi) KomoditasByKode(kode string) (KomoditasRef, bool) {
	k, ok := r.komoditasIdx[kode]
	return k, ok
}

// KecamatanValid true untuk 21 kecamatan atau "KOTA MEDAN".
func (r *Referensi) KecamatanValid(nama string) bool {
	return nama == r.Kota.Kecamatan || r.kecamatanSet[nama]
}

// KecamatanPasar mengembalikan kecamatan tempat pasar berada.
func (r *Referensi) KecamatanPasar(namaPasar string) (string, bool) {
	k, ok := r.pasarIdx[namaPasar]
	return k, ok
}

// SumberValid memeriksa kode sumber; sumber dev_saja hanya sah bila dev=true.
func (r *Referensi) SumberValid(kode string, dev bool) bool {
	s, ok := r.sumberIdx[kode]
	if !ok {
		return false
	}
	return !s.DevSaja || dev
}

// JumlahPasar banyaknya pasar terpantau di sebuah kecamatan (0 bila tidak ada data pasar).
func (r *Referensi) JumlahPasar(kecamatan string) int {
	n := 0
	for _, p := range r.Pasar {
		if p.Kecamatan == kecamatan {
			n++
		}
	}
	return n
}

func (r *Referensi) AcuanKecamatan(kecamatan string) (Seri, bool) {
	if kecamatan == r.Kota.Kecamatan {
		return Seri{Kecamatan: r.Kota.Kecamatan, NamaPasar: r.Kota.NamaPasar, Sumber: r.SumberUtamaKota}, true
	}
	if r.JumlahPasar(kecamatan) > 0 {
		return Seri{Kecamatan: kecamatan, NamaPasar: r.Kota.NamaPasar, Sumber: r.SumberUtamaKota}, true
	}
	a, ok := r.PemetaanKecamatan[kecamatan]
	if !ok {
		return Seri{}, false
	}
	return Seri{Kecamatan: r.pasarIdx[a.Pasar], NamaPasar: a.Pasar, Sumber: a.Sumber}, true
}