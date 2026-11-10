package handler

import (
	"log"
	"net/http"
	"time"

	"harga-pangan-medan/backend/internal/csvimport"
	"harga-pangan-medan/backend/internal/model"
)

// listHarga menangani pencarian dan pagination data harga.
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

// tambahHarga menambahkan 1 baris transaksi harga baru.
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

// ubahHarga memperbarui baris data harga berdasarkan ID.
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

// hapusHarga menghapus baris data harga berdasarkan ID.
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

// imporHarga memproses upload file CSV untuk impor massal data harga.
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

// eksporHarga mengekspor seluruh atau hasil filter data harga ke file CSV.
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

// templateImpor menyediakan file CSV template acuan untuk pengguna yang ingin impor data.
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

