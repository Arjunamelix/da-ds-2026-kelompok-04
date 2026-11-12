package handler

import (
	"encoding/json"
	"net/http"

	"harga-pangan-medan/backend/internal/model"
)

// prediksi menangani pengambilan hasil prediksi model untuk komoditas dan wilayah tertentu.
func (h *Handler) prediksi(w http.ResponseWriter, r *http.Request) {
	res, err := h.svc.PrediksiHalaman(r.Context(), r.URL.Query().Get("komoditas"), h.kecamatanQuery(r))
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

// status menangani status harga (Normal, Waspada, Lonjakan) seluruh komoditas.
func (h *Handler) status(w http.ResponseWriter, r *http.Request) {
	res, err := h.svc.StatusHalaman(r.Context(), h.kecamatanQuery(r))
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, res)
}

// evaluasi mengambil metrik performa model (MAE, MAPE, RMSE) dibanding model baseline.
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

// versiData mengambil nomor versi data dan model yang aktif saat ini.
func (h *Handler) versiData(w http.ResponseWriter, r *http.Request) {
	m, err := h.svc.Repo().GetMetaStatus(r.Context())
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, map[string]int64{"versi_data": m.VersiData, "versi_model": m.VersiModel})
}

// statusHitung mengambil status proses pelatihan model ML (idle, running, error).
func (h *Handler) statusHitung(w http.ResponseWriter, r *http.Request) {
	m, err := h.svc.Repo().GetMetaStatus(r.Context())
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, 200, m)
}

// retrain memicu proses pelatihan ulang model Machine Learning secara asinkron.
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

