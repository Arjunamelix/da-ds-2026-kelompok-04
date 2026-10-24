package config

import "testing"

func muat(t *testing.T) *Referensi {
	t.Helper()
	r, err := LoadReferensi("../../../config/referensi.json")
	if err != nil {
		t.Fatalf("LoadReferensi: %v", err)
	}
	return r
}

func TestReferensiDraf(t *testing.T) {
	r := muat(t)
	if len(r.Kecamatan) != 21 {
		t.Fatalf("kecamatan = %d, harus 21", len(r.Kecamatan))
	}
	if len(r.PemetaanKecamatan) != 21 {
		t.Fatalf("pemetaan = %d, harus 21 (opsi B)", len(r.PemetaanKecamatan))
	}
	if !r.KecamatanValid("KOTA MEDAN") || !r.KecamatanValid("Medan Petisah") || r.KecamatanValid("Medan Antah") {
		t.Fatal("KecamatanValid salah")
	}
}

func TestAcuan(t *testing.T) {
	r := muat(t)
	s, ok := r.AcuanKecamatan("Medan Petisah")
	if !ok || s.NamaPasar != "Pasar Dev Medan Sunggal" || s.Kecamatan != "Medan Sunggal" {
		t.Fatalf("acuan Petisah salah: %+v ok=%v", s, ok)
	}
	k, ok := r.AcuanKecamatan("KOTA MEDAN")
	if !ok || k.NamaPasar != "SEMUA" {
		t.Fatalf("acuan kota salah: %+v", k)
	}
}

func TestSumberDev(t *testing.T) {
	r := muat(t)
	if !r.SumberValid("DEV", true) || r.SumberValid("DEV", false) {
		t.Fatal("sumber DEV hanya boleh saat dev")
	}
	if !r.SumberValid("PIHPS", false) || r.SumberValid("XYZ", true) {
		t.Fatal("SumberValid salah")
	}
}