package handler

import (
	"net/http"
)

// ringkasan menangani data kartu ringkasan untuk dashboard utama.
func (h *Handler) ringkasan(w http.ResponseWriter, r *http.Request) {
	res, err := h.svc.Ringkasan(r.Context(), h.kecamatanQuery(r))
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

