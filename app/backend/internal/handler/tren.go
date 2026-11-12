package handler

import (
	"net/http"
)

// tren menangani data deret waktu harga untuk grafik halaman tren.
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

