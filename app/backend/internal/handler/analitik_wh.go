package handler

// Endpoint analitik yang membaca data warehouse (migrasi 000003) untuk halaman Analisis, Cerita,
// dan kartu KPI di Dashboard. Semua endpoint hanya membaca, dan hasilnya disimpan di cache memori
// sampai versi_data berubah (data ditambah, diubah, dihapus, atau diimpor).

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/go-chi/chi/v5"

	"harga-pangan-medan/backend/internal/repository"
)

// rutAnalitik dipasang di dalam r.Route("/api", ...) pada handler.go.
func (h *Handler) rutAnalitik(r chi.Router) {
	r.Route("/analitik", func(r chi.Router) {
		r.Get("/kpi", h.dariCache(h.anKPI))
		r.Get("/heatmap", h.dariCache(h.anHeatmap))
		r.Get("/mingguan", h.dariCache(h.anMingguan))
		r.Get("/sebaran", h.dariCache(h.anSebaran))
		r.Get("/wilayah", h.dariCache(h.anWilayah))
		r.Get("/deret", h.dariCache(h.anDeret))
		r.Get("/statistik", h.dariCache(h.anStatistik))
	})
}

// ---------------------------------------------------------------------------
// cache per versi_data
// ---------------------------------------------------------------------------

type cacheAnalitik struct {
	mu    sync.Mutex
	versi int64
	isi   map[string][]byte
}

var cacheAn = &cacheAnalitik{isi: map[string][]byte{}}

type galatMasukan struct{ pesan string }

func (g galatMasukan) Error() string { return g.pesan }

func (h *Handler) dariCache(fn func(*http.Request) (any, error)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		v, err := h.svc.Repo().VersiData(r.Context())
		if err != nil {
			writeErr(w, err)
			return
		}
		kunci := r.URL.Path + "?" + r.URL.Query().Encode()

		cacheAn.mu.Lock()
		if cacheAn.versi != v {
			cacheAn.versi, cacheAn.isi = v, map[string][]byte{}
		}
		b, ada := cacheAn.isi[kunci]
		cacheAn.mu.Unlock()

		if !ada {
			hasil, err := fn(r)
			if err != nil {
				if gm, ok := err.(galatMasukan); ok {
					badRequest(w, gm.pesan)
					return
				}
				writeErr(w, err)
				return
			}
			if b, err = json.Marshal(hasil); err != nil {
				writeErr(w, err)
				return
			}
			cacheAn.mu.Lock()
			if cacheAn.versi == v {
				cacheAn.isi[kunci] = b
			}
			cacheAn.mu.Unlock()
		}
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.Header().Set("X-Versi-Data", fmt.Sprint(v))
		if _, err := w.Write(append(b, '\n')); err != nil {
			log.Printf("tulis analitik: %v", err)
		}
	}
}

// ---------------------------------------------------------------------------
// parameter
// ---------------------------------------------------------------------------

func (h *Handler) filterAnalitik(r *http.Request, wajibKomoditas bool) (repository.FilterAnalitik, error) {
	q := r.URL.Query()
	var f repository.FilterAnalitik
	var err error
	if f.Dari, err = parseTanggal(q.Get("dari")); err != nil {
		return f, galatMasukan{err.Error()}
	}
	if f.Sampai, err = parseTanggal(q.Get("sampai")); err != nil {
		return f, galatMasukan{err.Error()}
	}
	ref := h.svc.Ref()
	f.Komoditas = strings.TrimSpace(q.Get("komoditas"))
	if f.Komoditas == "" && wajibKomoditas {
		return f, galatMasukan{"parameter komoditas wajib diisi"}
	}
	if f.Komoditas != "" {
		if _, ok := ref.KomoditasByKode(f.Komoditas); !ok {
			return f, galatMasukan{fmt.Sprintf("komoditas %q tidak dikenal", f.Komoditas)}
		}
	}
	f.Kecamatan = strings.TrimSpace(q.Get("kecamatan"))
	if f.Kecamatan == ref.Kota.Kecamatan {
		f.Kecamatan = "" // level kota
	}
	if f.Kecamatan != "" && !ref.KecamatanValid(f.Kecamatan) {
		return f, galatMasukan{fmt.Sprintf("kecamatan %q tidak dikenal", f.Kecamatan)}
	}
	return f, nil
}

func angkaF(v any) (float64, bool) {
	switch x := v.(type) {
	case float64:
		return x, true
	case int32:
		return float64(x), true
	case int64:
		return float64(x), true
	}
	return 0, false
}

func rata(xs []float64) any {
	if len(xs) == 0 {
		return nil
	}
	s := 0.0
	for _, x := range xs {
		s += x
	}
	return s / float64(len(xs))
}

// ---------------------------------------------------------------------------
// endpoint
// ---------------------------------------------------------------------------

// anKPI empat kartu KPI dengan pembanding, ditambah perubahan 7 hari per komoditas.
func (h *Handler) anKPI(r *http.Request) (any, error) {
	ctx := r.Context()
	kom, err := h.svc.Repo().KPIKomoditas(ctx)
	if err != nil {
		return nil, err
	}
	var kini, lalu []float64
	naikKini, naikLalu := 0, 0
	tanggal := ""
	for _, k := range kom {
		h0, ok0 := angkaF(k["harga"])
		h7, ok7 := angkaF(k["harga_7h"])
		h14, ok14 := angkaF(k["harga_14h"])
		k["perubahan_7h_pct"], k["perubahan_7h_lalu_pct"] = nil, nil
		if ok0 && ok7 && h7 > 0 {
			p := (h0/h7 - 1) * 100
			k["perubahan_7h_pct"] = p
			kini = append(kini, p)
			if p > 5 {
				naikKini++
			}
		}
		if ok7 && ok14 && h14 > 0 {
			p := (h7/h14 - 1) * 100
			k["perubahan_7h_lalu_pct"] = p
			lalu = append(lalu, p)
			if p > 5 {
				naikLalu++
			}
		}
		if t, _ := k["tanggal"].(string); t > tanggal {
			tanggal = t
		}
	}

	var dari *time.Time
	if t, err := time.Parse("2006-01-02", tanggal); err == nil {
		d := t.AddDate(0, 0, -60)
		dari = &d
	}
	disp, err := h.svc.Repo().KPIDisparitas(ctx, repository.FilterAnalitik{Dari: dari})
	if err != nil {
		return nil, err
	}
	var dKini, dLalu []float64
	for _, d := range disp {
		if v, ok := angkaF(d["kini"]); ok {
			dKini = append(dKini, v)
		}
		if v, ok := angkaF(d["pembanding"]); ok {
			dLalu = append(dLalu, v)
		}
	}
	pel, err := h.svc.Repo().KPIPelapor(ctx)
	if err != nil {
		return nil, err
	}
	var pelapor map[string]any
	if len(pel) > 0 {
		pelapor = pel[0]
	}

	kpi := []map[string]any{
		{
			"kode": "perubahan_7h", "judul": "Rata-rata perubahan harga 7 hari", "satuan": "%",
			"nilai": rata(kini), "pembanding": rata(lalu), "label_pembanding": "minggu sebelumnya",
			"keterangan": fmt.Sprintf("rata-rata %d komoditas, harga median kota", len(kini)), "naik_buruk": true,
		},
		{
			"kode": "naik_5", "judul": "Komoditas naik lebih dari 5%", "satuan": "komoditas",
			"nilai": naikKini, "pembanding": naikLalu, "label_pembanding": "minggu sebelumnya",
			"keterangan": fmt.Sprintf("dari %d komoditas dalam 7 hari terakhir", len(kini)), "naik_buruk": true,
		},
		{
			"kode": "disparitas", "judul": "Selisih harga antarpasar", "satuan": "%",
			"nilai": rata(dKini), "pembanding": rata(dLalu), "label_pembanding": "rata-rata 30 hari sebelumnya",
			"keterangan": "(termahal - termurah) / median, rata-rata semua komoditas, 7 hari terakhir", "naik_buruk": true,
		},
	}
	if pelapor != nil {
		kpi = append(kpi, map[string]any{
			"kode": "pelapor", "judul": "Pasar yang melapor", "satuan": "pasar",
			"nilai": pelapor["kini"], "pembanding": pelapor["pembanding"], "label_pembanding": "rata-rata 30 hari laporan sebelumnya",
			"target": pelapor["target"], "keterangan": "pada hari laporan terakhir", "naik_buruk": false,
		})
	}
	return map[string]any{"tanggal": tanggal, "kpi": kpi, "komoditas": kom, "disparitas": disp}, nil
}

func (h *Handler) anHeatmap(r *http.Request) (any, error) {
	f, err := h.filterAnalitik(r, false)
	if err != nil {
		return nil, err
	}
	rows, err := h.svc.Repo().Heatmap(r.Context(), f)
	return map[string]any{"sel": rows}, err
}

func (h *Handler) anMingguan(r *http.Request) (any, error) {
	f, err := h.filterAnalitik(r, false)
	if err != nil {
		return nil, err
	}
	rows, err := h.svc.Repo().Mingguan(r.Context(), f)
	return map[string]any{"titik": rows}, err
}

func (h *Handler) anSebaran(r *http.Request) (any, error) {
	f, err := h.filterAnalitik(r, true)
	if err != nil {
		return nil, err
	}
	rows, err := h.svc.Repo().Sebaran(r.Context(), f)
	return map[string]any{"komoditas": f.Komoditas, "kecamatan": f.Kecamatan, "bulan": rows}, err
}

func (h *Handler) anWilayah(r *http.Request) (any, error) {
	f, err := h.filterAnalitik(r, false)
	if err != nil {
		return nil, err
	}
	rows, err := h.svc.Repo().Wilayah(r.Context(), f)
	return map[string]any{"komoditas": f.Komoditas, "pasar": rows}, err
}

// anDeret deret harian satu komoditas dan anotasinya (hari besar pada rentang yang sama).
func (h *Handler) anDeret(r *http.Request) (any, error) {
	f, err := h.filterAnalitik(r, true)
	if err != nil {
		return nil, err
	}
	ctx := r.Context()
	rows, err := h.svc.Repo().DeretHarian(ctx, f)
	if err != nil {
		return nil, err
	}
	hb := []map[string]any{}
	if len(rows) > 0 {
		awal, _ := rows[0]["tanggal"].(string)
		akhir, _ := rows[len(rows)-1]["tanggal"].(string)
		if hb, err = h.svc.Repo().HariBesar(ctx, awal, akhir); err != nil {
			return nil, err
		}
	}
	res := map[string]any{"komoditas": f.Komoditas, "kecamatan": f.Kecamatan, "titik": rows, "hari_besar": hb}
	if len(rows) == 0 && f.Kecamatan == "" {
		res["catatan"] = "Komoditas ini tidak punya angka level kota pada rentang ini (kurang dari 3 pasar melapor pada hari yang sama). Pilih satu kecamatan."
	}
	return res, nil
}

// anStatistik bahan halaman Cerita dan Analisis: volatilitas, korelasi, dampak hari besar, disparitas.
func (h *Handler) anStatistik(r *http.Request) (any, error) {
	f, err := h.filterAnalitik(r, false)
	if err != nil {
		return nil, err
	}
	ctx := r.Context()
	type langkah struct {
		nama string
		fn   func(context.Context, repository.FilterAnalitik) ([]map[string]any, error)
	}
	out := map[string]any{}
	for _, l := range []langkah{
		{"volatilitas", h.svc.Repo().Volatilitas},
		{"korelasi", h.svc.Repo().Korelasi},
		{"hari_besar", h.svc.Repo().HariBesarDampak},
		{"disparitas", h.svc.Repo().KPIDisparitas},
	} {
		rows, err := l.fn(ctx, f)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", l.nama, err)
		}
		out[l.nama] = rows
	}
	return out, nil
}
