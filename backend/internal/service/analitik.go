package service

import (
	"context"
	"fmt"
	"math"
	"sort"
	"time"

	"harga-pangan-medan/backend/internal/config"
	"harga-pangan-medan/backend/internal/model"
)

func ptrF(v float64) *float64 { return &v }
func ptrI(v int) *int         { return &v }

// Ringkasan menyusun kartu per komoditas untuk satu kecamatan (atau KOTA MEDAN): harga terakhir,
// perubahan 7 hari, prediksi 7 hari, dan status. Deret diambil dari pemetaan opsi B.
func (s *Service) Ringkasan(ctx context.Context, kecamatan string) (map[string]any, error) {
	seri, ok := s.ref.AcuanKecamatan(kecamatan)
	if !ok {
		return map[string]any{"kecamatan": kecamatan, "tanpa_data": true, "kartu": []model.KartuRingkasan{}}, nil
	}
	last, err := s.repo.TerakhirPerKomoditas(ctx, seri.Kecamatan, seri.NamaPasar, seri.Sumber)
	if err != nil {
		return nil, err
	}
	pred, err := s.repo.PrediksiSeri(ctx, seri.Kecamatan, seri.NamaPasar, seri.Sumber)
	if err != nil {
		return nil, err
	}
	stat, err := s.repo.StatusSeri(ctx, seri.Kecamatan, seri.NamaPasar, seri.Sumber)
	if err != nil {
		return nil, err
	}
	skip, err := s.repo.DilewatiSeri(ctx, seri.Kecamatan, seri.NamaPasar, seri.Sumber)
	if err != nil {
		return nil, err
	}
	byKom := map[string]struct {
		tgl   string
		harga int
		h7    *int
	}{}
	for _, t := range last {
		byKom[t.Komoditas] = struct {
			tgl   string
			harga int
			h7    *int
		}{t.Tanggal, t.Harga, t.Harga7H}
	}

	kartu := []model.KartuRingkasan{}
	for _, k := range s.ref.Komoditas {
		t, ada := byKom[k.Kode]
		if !ada {
			continue
		}
		c := model.KartuRingkasan{
			Komoditas: k.Kode, Nama: k.Nama, Satuan: k.Satuan,
			TanggalTerakhir: t.tgl, HargaTerakhir: t.harga, Harga7HLalu: t.h7,
		}
		if t.h7 != nil && *t.h7 > 0 {
			c.PerubahanAbs = ptrI(t.harga - *t.h7)
			c.PerubahanPct = ptrF(float64(t.harga-*t.h7) / float64(*t.h7) * 100)
		}
		for _, p := range pred[k.Kode] {
			if p.Horizon == 7 {
				c.Prediksi7, c.Prediksi7Bawah, c.Prediksi7Atas = ptrF(p.HargaPrediksi), ptrF(p.BatasBawah), ptrF(p.BatasAtas)
			}
		}
		if st, ok := stat[k.Kode]; ok {
			c.Status = &st.Status
			c.PerubahanPrediksiPct = ptrF(st.PerubahanPrediksiPct)
		}
		switch {
		case c.Prediksi7 != nil:
		case skip[k.Kode].Alasan != "":
			c.Keterangan = "data_belum_cukup"
		default:
			c.Keterangan = "model_belum_ada"
		}
		kartu = append(kartu, c)
	}
	return map[string]any{
		"kecamatan": kecamatan, "pasar_acuan": seri.NamaPasar, "sumber": seri.Sumber,
		"pasar_sendiri": kecamatan == seri.Kecamatan, "kartu": kartu,
	}, nil
}

// Tren titik harga satu komoditas untuk maksimal 3 kecamatan (aturan visualisasi 6.6).
func (s *Service) Tren(ctx context.Context, komoditas string, kecamatan []string, dari, sampai *time.Time) (map[string]any, error) {
	if _, ok := s.ref.KomoditasByKode(komoditas); !ok {
		return nil, &ValidasiError{Pesan: []string{fmt.Sprintf("komoditas %q tidak dikenal", komoditas)}}
	}
	if len(kecamatan) == 0 {
		kecamatan = []string{s.ref.Kota.Kecamatan}
	}
	if len(kecamatan) > 3 {
		return nil, &ValidasiError{Pesan: []string{"maksimal 3 kecamatan per grafik"}}
	}
	type seriOut struct {
		Kecamatan    string        `json:"kecamatan"`
		PasarAcuan   string        `json:"pasar_acuan"`
		Sumber       string        `json:"sumber"`
		PasarSendiri bool          `json:"pasar_sendiri"`
		TanpaData    bool          `json:"tanpa_data"`
		Titik        []model.Titik `json:"titik"`
	}
	out := []seriOut{}
	for _, kec := range kecamatan {
		if !s.ref.KecamatanValid(kec) {
			return nil, &ValidasiError{Pesan: []string{fmt.Sprintf("kecamatan %q tidak dikenal", kec)}}
		}
		seri, ok := s.ref.AcuanKecamatan(kec)
		so := seriOut{Kecamatan: kec, Titik: []model.Titik{}}
		if !ok {
			so.TanpaData = true
			out = append(out, so)
			continue
		}
		so.PasarAcuan, so.Sumber, so.PasarSendiri = seri.NamaPasar, seri.Sumber, seri.Kecamatan == kec
		t, err := s.repo.Tren(ctx, seri.Kecamatan, seri.NamaPasar, komoditas, seri.Sumber, dari, sampai)
		if err != nil {
			return nil, err
		}
		so.Titik = t
		so.TanpaData = len(t) == 0
		out = append(out, so)
	}
	k, _ := s.ref.KomoditasByKode(komoditas)
	return map[string]any{"komoditas": komoditas, "nama": k.Nama, "satuan": k.Satuan, "seri": out}, nil
}

// Perbandingan harga satu komoditas di seluruh 21 kecamatan beserta selisih terhadap rata-rata Kota Medan.
// Rata-rata Kota Medan = harga deret level kota bila ada; bila tidak, rata-rata harga kecamatan yang punya data.
// Kecamatan tanpa data tetap ditampilkan.
func (s *Service) Perbandingan(ctx context.Context, komoditas string, sampai *time.Time) (map[string]any, error) {
	k, ok := s.ref.KomoditasByKode(komoditas)
	if !ok {
		return nil, &ValidasiError{Pesan: []string{fmt.Sprintf("komoditas %q tidak dikenal", komoditas)}}
	}
	type kunci struct{ kec, pasar, sumber string }
	need := map[kunci]bool{}
	for _, kec := range s.ref.Kecamatan {
		if a, ok := s.ref.AcuanKecamatan(kec); ok {
			need[kunci{a.Kecamatan, a.NamaPasar, a.Sumber}] = true
		}
	}
	kotaSeri, _ := s.ref.AcuanKecamatan(s.ref.Kota.Kecamatan)
	need[kunci{kotaSeri.Kecamatan, kotaSeri.NamaPasar, kotaSeri.Sumber}] = true

	var ks, ps, ss []string
	for k := range need {
		ks, ps, ss = append(ks, k.kec), append(ps, k.pasar), append(ss, k.sumber)
	}
	rows, err := s.repo.TerakhirBanyakDeret(ctx, komoditas, sampai, ks, ps, ss)
	if err != nil {
		return nil, err
	}
	harga := map[kunci]struct {
		tgl string
		h   int
	}{}
	for _, r := range rows {
		harga[kunci{r.Kecamatan, r.NamaPasar, r.Sumber}] = struct {
			tgl string
			h   int
		}{r.Tanggal, r.Harga}
	}

	out := []model.BarisPerbandingan{}
	var rata float64
	var sumber string
	if kh, ada := harga[kunci{kotaSeri.Kecamatan, kotaSeri.NamaPasar, kotaSeri.Sumber}]; ada {
		rata, sumber = float64(kh.h), "harga level Kota Medan ("+kotaSeri.Sumber+")"
	}
	var jumlah float64
	var n int
	for _, kec := range s.ref.Kecamatan {
		b := model.BarisPerbandingan{Kecamatan: kec}
		a, ok := s.ref.AcuanKecamatan(kec)
		if !ok {
			b.TanpaData, b.Keterangan = true, "belum dipetakan ke pasar acuan"
			out = append(out, b)
			continue
		}
		b.PasarAcuan, b.Sumber, b.LangsungAda = a.NamaPasar, a.Sumber, a.Kecamatan == kec
		if !b.LangsungAda {
			b.Keterangan = "mengacu pada " + a.NamaPasar
		}
		if h, ada := harga[kunci{a.Kecamatan, a.NamaPasar, a.Sumber}]; ada {
			b.Harga, b.TanggalData = ptrI(h.h), h.tgl
			jumlah += float64(h.h)
			n++
		} else {
			b.TanpaData, b.Keterangan = true, "belum ada data harga untuk komoditas ini"
		}
		out = append(out, b)
	}
	if sumber == "" && n > 0 {
		rata, sumber = jumlah/float64(n), "rata-rata kecamatan yang punya data"
	}
	if rata > 0 {
		for i := range out {
			if out[i].Harga != nil {
				out[i].SelisihPct = ptrF((float64(*out[i].Harga)/rata - 1) * 100)
			}
		}
	}
	// Urut dari termahal; yang tanpa data di akhir (tidak disembunyikan).
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i].Harga, out[j].Harga
		if a == nil || b == nil {
			return a != nil && b == nil
		}
		return *a > *b
	})
	res := map[string]any{
		"komoditas": komoditas, "nama": k.Nama, "satuan": k.Satuan, "kecamatan": out,
		"rata_rata_kota": nil, "dasar_rata_rata": sumber,
	}
	if rata > 0 {
		res["rata_rata_kota"] = math.Round(rata)
	}
	return res, nil
}

// PrediksiHalaman data halaman prediksi: prediksi 7/14 hari, status, evaluasi untuk satu komoditas dan kecamatan.
func (s *Service) PrediksiHalaman(ctx context.Context, komoditas, kecamatan string) (map[string]any, error) {
	if _, ok := s.ref.KomoditasByKode(komoditas); !ok {
		return nil, &ValidasiError{Pesan: []string{fmt.Sprintf("komoditas %q tidak dikenal", komoditas)}}
	}
	if !s.ref.KecamatanValid(kecamatan) {
		return nil, &ValidasiError{Pesan: []string{fmt.Sprintf("kecamatan %q tidak dikenal", kecamatan)}}
	}
	seri, ok := s.ref.AcuanKecamatan(kecamatan)
	if !ok {
		return map[string]any{"kecamatan": kecamatan, "komoditas": komoditas, "tanpa_data": true}, nil
	}
	pred, err := s.repo.PrediksiSeri(ctx, seri.Kecamatan, seri.NamaPasar, seri.Sumber)
	if err != nil {
		return nil, err
	}
	stat, err := s.repo.StatusSeri(ctx, seri.Kecamatan, seri.NamaPasar, seri.Sumber)
	if err != nil {
		return nil, err
	}
	skip, err := s.repo.DilewatiSeri(ctx, seri.Kecamatan, seri.NamaPasar, seri.Sumber)
	if err != nil {
		return nil, err
	}
	ev, err := s.repo.EvaluasiDeret(ctx, komoditas)
	if err != nil {
		return nil, err
	}
	evSeri := []model.Evaluasi{}
	for _, e := range ev {
		if e.Kecamatan == seri.Kecamatan && e.NamaPasar == seri.NamaPasar && e.Sumber == seri.Sumber {
			evSeri = append(evSeri, e)
		}
	}
	res := map[string]any{
		"kecamatan": kecamatan, "komoditas": komoditas, "pasar_acuan": seri.NamaPasar, "sumber": seri.Sumber,
		"pasar_sendiri": seri.Kecamatan == kecamatan, "prediksi": nzP(pred[komoditas]), "evaluasi": evSeri,
	}
	if st, ok := stat[komoditas]; ok {
		res["status"] = st
	}
	if d, ok := skip[komoditas]; ok {
		res["dilewati"] = d
	}
	return res, nil
}

func nzP(p []model.Prediksi) []model.Prediksi {
	if p == nil {
		return []model.Prediksi{}
	}
	return p
}

// StatusHalaman status per komoditas untuk satu kecamatan.
func (s *Service) StatusHalaman(ctx context.Context, kecamatan string) (map[string]any, error) {
	seri, ok := s.ref.AcuanKecamatan(kecamatan)
	if !ok {
		return map[string]any{"kecamatan": kecamatan, "tanpa_data": true, "status": []any{}}, nil
	}
	stat, err := s.repo.StatusSeri(ctx, seri.Kecamatan, seri.NamaPasar, seri.Sumber)
	if err != nil {
		return nil, err
	}
	type item struct {
		Komoditas string `json:"komoditas"`
		Nama      string `json:"nama"`
		model.Status
	}
	out := []item{}
	for _, k := range s.ref.Komoditas {
		if st, ok := stat[k.Kode]; ok {
			out = append(out, item{k.Kode, k.Nama, st})
		}
	}
	return map[string]any{"kecamatan": kecamatan, "pasar_acuan": seri.NamaPasar, "status": out}, nil
}

// Referensi bentuk ringkas config untuk dropdown di frontend.
func (s *Service) Referensi() map[string]any {
	pemetaan := map[string]config.Seri{}
	for _, kec := range s.ref.Kecamatan {
		if a, ok := s.ref.AcuanKecamatan(kec); ok {
			pemetaan[kec] = a
		}
	}
	sumber := []config.SumberRef{}
	for _, sm := range s.ref.Sumber {
		if !sm.DevSaja || s.cfg.IsDev() {
			sumber = append(sumber, sm)
		}
	}
	kotaSeri, _ := s.ref.AcuanKecamatan(s.ref.Kota.Kecamatan)
	return map[string]any{
		"data_sintetis":      kotaSeri.Sumber == "DEV",
		"status_konfigurasi": s.ref.StatusKonfigurasi,
		"app_env":            s.cfg.AppEnv,
		"kota":               s.ref.Kota,
		"kecamatan":          s.ref.Kecamatan,
		"komoditas":          s.ref.Komoditas,
		"pasar":              s.ref.Pasar,
		"sumber":             sumber,
		"pemetaan_kecamatan": pemetaan,
	}
}

// PrediksiSesudah prediksi 7 hari terkini untuk deret yang tepat (dipakai tampilan sebelum -> sesudah setelah retrain).
func (s *Service) PrediksiSesudah(ctx context.Context, kunci []model.KunciDeret) ([]model.PrediksiSeri, error) {
	if len(kunci) > 50 {
		return nil, &ValidasiError{Pesan: []string{"maksimal 50 deret per permintaan"}}
	}
	return s.repo.Prediksi7Untuk(ctx, s.repo.DB(), kunci)
}