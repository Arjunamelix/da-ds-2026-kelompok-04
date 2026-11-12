package config

import "testing"

func muat(t *testing.T) *Referensi {
	t.Helper()
	r, err := LoadReferensi("../../../../config/referensi.json")
	if err != nil {
		t.Fatalf("LoadReferensi: %v", err)
	}
	return r
}

func TestReferensiSimpang(t *testing.T) {
	r := muat(t)
	if len(r.Kecamatan) != 21 {
		t.Fatalf("kecamatan = %d, harus 21", len(r.Kecamatan))
	}
	if len(r.Pasar) != 21 {
		t.Fatalf("pasar = %d, SIMPANG punya 21 pasar", len(r.Pasar))
	}
	if len(r.Komoditas) != 14 {
		t.Fatalf("komoditas = %d, referensi berisi 14 (12 SIMPANG + 2 SP2KP)", len(r.Komoditas))
	}
	if !r.KecamatanValid("KOTA MEDAN") || !r.KecamatanValid("Medan Petisah") || r.KecamatanValid("Medan Antah") {
		t.Fatal("KecamatanValid salah")
	}
}

func TestAcuanKecamatan(t *testing.T) {
	r := muat(t)
	// kecamatan berpasar -> deret rata-rata kecamatan (kecamatan, SEMUA)
	s, ok := r.AcuanKecamatan("Medan Kota")
	if !ok || s.Kecamatan != "Medan Kota" || s.NamaPasar != "SEMUA" || s.Sumber != "SIMPANG" {
		t.Fatalf("acuan Medan Kota salah: %+v ok=%v", s, ok)
	}
	if n := r.JumlahPasar("Medan Kota"); n != 3 {
		t.Fatalf("Medan Kota punya 3 pasar, dapat %d", n)
	}
	// kecamatan tanpa pasar di SIMPANG -> tidak ada data, tidak ditebak
	for _, kec := range []string{"Medan Amplas", "Medan Baru", "Medan Denai", "Medan Labuhan", "Medan Maimun", "Medan Polonia", "Medan Tembung", "Medan Timur"} {
		if _, ok := r.AcuanKecamatan(kec); ok {
			t.Fatalf("%s tidak punya pasar, seharusnya tanpa data", kec)
		}
	}
	k, ok := r.AcuanKecamatan("KOTA MEDAN")
	if !ok || k.NamaPasar != "SEMUA" || k.Kecamatan != "KOTA MEDAN" {
		t.Fatalf("acuan kota salah: %+v", k)
	}
	berpasar := 0
	for _, kec := range r.Kecamatan {
		if _, ok := r.AcuanKecamatan(kec); ok {
			berpasar++
		}
	}
	if berpasar != 13 {
		t.Fatalf("kecamatan dengan data = %d, harus 13", berpasar)
	}
}

func TestSumberDev(t *testing.T) {
	r := muat(t)
	if !r.SumberValid("DEV", true) || r.SumberValid("DEV", false) {
		t.Fatal("sumber DEV hanya boleh saat dev")
	}
	if !r.SumberValid("SIMPANG", false) || r.SumberValid("XYZ", true) {
		t.Fatal("SumberValid salah")
	}
}