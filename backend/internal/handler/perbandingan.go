package handler

import (
	"net/http"
)

// perbandingan menangani data perbandingan harga komoditas antar-kecamatan pada tanggal tertentu.
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

