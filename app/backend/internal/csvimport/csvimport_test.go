package csvimport

import (
	"strings"
	"testing"
)

func TestParseBaris(t *testing.T) {
	in := "tanggal,kecamatan,nama_pasar,komoditas,harga,sumber\n" +
		"2024-01-02,Medan Petisah,Pasar X,beras_medium,14200,PIHPS\n" +
		"\n" +
		"2024-01-03,Medan Petisah,Pasar X\n" +
		"2024-01-04, KOTA MEDAN ,SEMUA,beras_medium,14000,PIHPS\n"
	b, err := Parse(strings.NewReader(in))
	if err != nil {
		t.Fatal(err)
	}
	if len(b) != 3 {
		t.Fatalf("baris = %d, diharapkan 3 (baris kosong dilewati)", len(b))
	}
	if b[0].Nomor != 2 || b[0].Harga != "14200" {
		t.Fatalf("baris 1 salah: %+v", b[0])
	}
	if b[1].Galat == "" || b[1].Nomor != 4 {
		t.Fatalf("baris dengan kolom kurang harus bergalat dan bernomor 4: %+v", b[1])
	}
	if b[2].Kecamatan != "KOTA MEDAN" {
		t.Fatalf("spasi harus dipangkas: %q", b[2].Kecamatan)
	}
}

func TestParseHeaderBOMDanUrutan(t *testing.T) {
	in := string(rune(0xFEFF)) + "sumber,harga,komoditas,nama_pasar,kecamatan,tanggal\nPIHPS,100,beras_medium,P,K,2024-01-01\n"
	b, err := Parse(strings.NewReader(in))
	if err != nil || len(b) != 1 {
		t.Fatalf("err=%v n=%d", err, len(b))
	}
	if b[0].Tanggal != "2024-01-01" || b[0].Sumber != "PIHPS" {
		t.Fatalf("urutan kolom bebas gagal: %+v", b[0])
	}
}

func TestParseHeaderKurang(t *testing.T) {
	if _, err := Parse(strings.NewReader("tanggal,harga\n2024-01-01,5\n")); err == nil {
		t.Fatal("header kurang harus ditolak")
	}
	if _, err := Parse(strings.NewReader("")); err == nil {
		t.Fatal("berkas kosong harus ditolak")
	}
}

func TestParseHarga(t *testing.T) {
	for _, ok := range []string{"52000", "1"} {
		if _, err := ParseHarga(ok); err != nil {
			t.Errorf("%q seharusnya valid: %v", ok, err)
		}
	}
	for _, bad := range []string{"", "52.000", "52,000", "Rp52000", "-5", "12.5", "abc"} {
		if _, err := ParseHarga(bad); err == nil {
			t.Errorf("%q seharusnya ditolak", bad)
		}
	}
}