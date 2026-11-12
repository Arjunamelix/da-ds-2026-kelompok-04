// Package csvimport mem-parsing CSV impor (6 kolom) dan menulis CSV ekspor.
package csvimport

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"

	"harga-pangan-medan/backend/internal/model"
)

// Kolom adalah header baku CSV impor/ekspor.
var Kolom = []string{"tanggal", "kecamatan", "nama_pasar", "komoditas", "harga", "sumber"}

// Baris satu baris CSV mentah (semua teks) beserta nomor barisnya di berkas (header = baris 1).
type Baris struct {
	Nomor     int
	Tanggal   string
	Kecamatan string
	NamaPasar string
	Komoditas string
	Harga     string
	Sumber    string
	Galat     string // diisi bila baris tidak bisa dibaca (jumlah kolom salah, dst.)
}

var ErrHeader = errors.New("header CSV tidak sesuai")

// Parse membaca seluruh CSV. Header harus memuat 6 kolom baku (urutan bebas).
func Parse(r io.Reader) ([]Baris, error) {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1
	cr.TrimLeadingSpace = true
	cr.LazyQuotes = true

	head, err := cr.Read()
	if err == io.EOF {
		return nil, fmt.Errorf("%w: berkas kosong", ErrHeader)
	}
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrHeader, err)
	}
	idx := map[string]int{}
	for i, h := range head {
		h = strings.ToLower(strings.TrimSpace(strings.TrimPrefix(h, string(rune(0xFEFF)))))
		idx[h] = i
	}
	var hilang []string
	for _, k := range Kolom {
		if _, ok := idx[k]; !ok {
			hilang = append(hilang, k)
		}
	}
	if len(hilang) > 0 {
		return nil, fmt.Errorf("%w: kolom hilang: %s (header harus %s)", ErrHeader, strings.Join(hilang, ", "), strings.Join(Kolom, ","))
	}

	out := []Baris{}
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		line, _ := cr.FieldPos(0)
		if err != nil {
			out = append(out, Baris{Nomor: line, Galat: "baris tidak bisa dibaca: " + err.Error()})
			continue
		}
		get := func(k string) string {
			i := idx[k]
			if i < len(rec) {
				return strings.TrimSpace(rec[i])
			}
			return ""
		}
		if len(rec) < len(Kolom) {
			out = append(out, Baris{Nomor: line, Galat: fmt.Sprintf("jumlah kolom %d, seharusnya minimal %d", len(rec), len(Kolom))})
			continue
		}
		out = append(out, Baris{
			Nomor: line, Tanggal: get("tanggal"), Kecamatan: get("kecamatan"), NamaPasar: get("nama_pasar"),
			Komoditas: get("komoditas"), Harga: get("harga"), Sumber: get("sumber"),
		})
	}
	return out, nil
}

// ParseHarga hanya menerima angka bulat tanpa titik, koma, atau "Rp".
func ParseHarga(s string) (int, error) {
	if s == "" {
		return 0, errors.New("harga kosong")
	}
	for _, c := range s {
		if c < '0' || c > '9' {
			return 0, fmt.Errorf("harga %q harus angka bulat tanpa titik, koma, atau \"Rp\"", s)
		}
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, fmt.Errorf("harga %q terlalu besar", s)
	}
	return n, nil
}

// Penulis menulis CSV ekspor dengan 6 kolom yang sama dengan impor.
type Penulis struct {
	w *csv.Writer
}

func NewPenulis(w io.Writer) (*Penulis, error) {
	cw := csv.NewWriter(w)
	if err := cw.Write(Kolom); err != nil {
		return nil, err
	}
	return &Penulis{w: cw}, nil
}

func (p *Penulis) Tulis(h model.Harga) error {
	return p.w.Write([]string{h.Tanggal, h.Kecamatan, h.NamaPasar, h.Komoditas, strconv.Itoa(h.Harga), h.Sumber})
}

func (p *Penulis) Selesai() error {
	p.w.Flush()
	return p.w.Error()
}