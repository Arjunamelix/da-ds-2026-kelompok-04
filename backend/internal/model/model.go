// Package model berisi tipe data yang dipakai bersama oleh repository, service, dan handler.
package model

import "time"

// Harga satu baris pada tabel harga.
type Harga struct {
	ID             int64     `json:"id"`
	Tanggal        string    `json:"tanggal"`
	Kecamatan      string    `json:"kecamatan"`
	NamaPasar      string    `json:"nama_pasar"`
	Komoditas      string    `json:"komoditas"`
	Harga          int       `json:"harga"`
	Sumber         string    `json:"sumber"`
	Satuan         string    `json:"satuan"`
	TingkatWilayah string    `json:"tingkat_wilayah"`
	Interpolasi    int       `json:"interpolasi"`
	DibuatPada     time.Time `json:"dibuat_pada"`
}

// HargaInput adalah 6 kolom yang diisi pengguna (CRUD dan impor CSV).
type HargaInput struct {
	Tanggal   string `json:"tanggal"`
	Kecamatan string `json:"kecamatan"`
	NamaPasar string `json:"nama_pasar"`
	Komoditas string `json:"komoditas"`
	Harga     int    `json:"harga"`
	Sumber    string `json:"sumber"`
}

// BarisValid adalah baris yang sudah lolos validasi dan siap ditulis.
type BarisValid struct {
	Input   HargaInput
	Tanggal time.Time
	Satuan  string
}

// FilterHarga untuk daftar dan ekspor.
type FilterHarga struct {
	Kecamatan string
	NamaPasar string
	Komoditas string
	Sumber    string
	Dari      *time.Time
	Sampai    *time.Time
	Page      int
	PerPage   int
}

// KunciDeret mengidentifikasi satu deret (komoditas + kecamatan + pasar + sumber).
type KunciDeret struct {
	Kecamatan string `json:"kecamatan"`
	NamaPasar string `json:"nama_pasar"`
	Komoditas string `json:"komoditas"`
	Sumber    string `json:"sumber"`
}

// Titik satu titik pada grafik tren.
type Titik struct {
	Tanggal string `json:"tanggal"`
	Harga   int    `json:"harga"`
}

// Prediksi hasil model untuk satu horizon.
type Prediksi struct {
	Horizon       int     `json:"horizon"`
	TanggalDasar  string  `json:"tanggal_dasar"`
	HargaDasar    float64 `json:"harga_dasar"`
	HargaPrediksi float64 `json:"harga_prediksi"`
	BatasBawah    float64 `json:"batas_bawah"`
	BatasAtas     float64 `json:"batas_atas"`
}

// PrediksiSeri prediksi 7 hari untuk satu deret (dipakai tampilan sebelum -> sesudah).
type PrediksiSeri struct {
	KunciDeret
	Prediksi7 float64 `json:"prediksi_7h"`
}

// Status klasifikasi Normal / Waspada / Lonjakan.
type Status struct {
	Status               string  `json:"status"`
	PerubahanPrediksiPct float64 `json:"perubahan_prediksi_pct"`
	AmbangWaspadaPct     float64 `json:"ambang_waspada_pct"`
	AmbangLonjakanPct    float64 `json:"ambang_lonjakan_pct"`
	TanggalDasar         string  `json:"tanggal_dasar"`
}

// Evaluasi metrik walk-forward satu deret dan horizon.
type Evaluasi struct {
	KunciDeret
	Horizon             int     `json:"horizon"`
	NUji                int     `json:"n_uji"`
	MAEModel            float64 `json:"mae_model"`
	RMSEModel           float64 `json:"rmse_model"`
	MAPEModel           float64 `json:"mape_model"`
	MAEBaseline         float64 `json:"mae_baseline"`
	RMSEBaseline        float64 `json:"rmse_baseline"`
	MAPEBaseline        float64 `json:"mape_baseline"`
	MengalahkanBaseline bool    `json:"mengalahkan_baseline"`
}

// EvaluasiStatus recall dan presisi kelas berisiko per komoditas.
type EvaluasiStatus struct {
	Komoditas         string   `json:"komoditas"`
	NUji              int      `json:"n_uji"`
	NBerisiko         int      `json:"n_berisiko"`
	RecallBerisiko    *float64 `json:"recall_berisiko"`
	PresisiBerisiko   *float64 `json:"presisi_berisiko"`
	AmbangWaspadaPct  float64  `json:"ambang_waspada_pct"`
	AmbangLonjakanPct float64  `json:"ambang_lonjakan_pct"`
}

// Dilewati alasan sebuah deret tidak dimodelkan.
type Dilewati struct {
	Alasan string `json:"alasan"`
	NHari  int    `json:"n_hari"`
}

// Peringatan harga berubah drastis dari data sebelumnya (tetap disimpan).
type Peringatan struct {
	Tanggal   string `json:"tanggal"`
	Kecamatan string `json:"kecamatan"`
	NamaPasar string `json:"nama_pasar"`
	Komoditas string `json:"komoditas"`
	Sebelum   int    `json:"harga_sebelumnya"`
	Sekarang  int    `json:"harga"`
	Pesan     string `json:"pesan"`
}

// MetaStatus status pelatihan ulang.
type MetaStatus struct {
	VersiData     int64  `json:"versi_data"`
	VersiModel    int64  `json:"versi_model"`
	StatusHitung  string `json:"status_hitung"`
	PesanHitung   string `json:"pesan_hitung"`
	HitungMulai   string `json:"hitung_mulai"`
	HitungSelesai string `json:"hitung_selesai"`
}

// KartuRingkasan satu kartu komoditas pada dashboard.
type KartuRingkasan struct {
	Komoditas            string   `json:"komoditas"`
	Nama                 string   `json:"nama"`
	Satuan               string   `json:"satuan"`
	TanggalTerakhir      string   `json:"tanggal_terakhir"`
	HargaTerakhir        int      `json:"harga_terakhir"`
	Harga7HLalu          *int     `json:"harga_7h_lalu"`
	PerubahanAbs         *int     `json:"perubahan_7h_abs"`
	PerubahanPct         *float64 `json:"perubahan_7h_pct"`
	Prediksi7            *float64 `json:"prediksi_7h"`
	Prediksi7Bawah       *float64 `json:"prediksi_7h_bawah"`
	Prediksi7Atas        *float64 `json:"prediksi_7h_atas"`
	Status               *string  `json:"status"`
	PerubahanPrediksiPct *float64 `json:"perubahan_prediksi_pct"`
	Keterangan           string   `json:"keterangan"`
}

// DetailPasar rincian harga di satu pasar dalam kecamatan.
type DetailPasar struct {
	NamaPasar string `json:"nama_pasar"`
	Harga     int    `json:"harga"`
}

// BarisPerbandingan satu kecamatan pada halaman perbandingan.
type BarisPerbandingan struct {
	Kecamatan   string        `json:"kecamatan"`
	PasarAcuan  string        `json:"pasar_acuan"`
	Sumber      string        `json:"sumber"`
	LangsungAda bool          `json:"pasar_sendiri"`
	TanggalData string        `json:"tanggal_data"`
	Harga       *int          `json:"harga"`
	SelisihPct  *float64      `json:"selisih_pct_vs_kota"`
	TanpaData   bool          `json:"tanpa_data"`
	Keterangan  string        `json:"keterangan"`
	JumlahPasar int           `json:"jumlah_pasar"`
	DetailPasar []DetailPasar `json:"detail_pasar,omitempty"`
}