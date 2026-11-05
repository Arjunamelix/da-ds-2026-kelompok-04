from datetime import date

import pytest
from conftest import Respons, SesiTiruan, halaman

from app import sumber_simpang as ss
from app import sumber_sp2kp as sp


def test_parse_halaman_berisi_data():
    d = ss.parse_halaman(halaman("beras"))
    assert sum(len(v["pasar"]) for v in d.values()) == 21


def test_parse_halaman_kosong():
    assert ss.parse_halaman("<p>Tidak ada harga untuk komoditi ini</p>") is None


def test_skrip_pemantau_cloudflare_bukan_penolakan():
    """challenge-platform ada di halaman normal SIMPANG; data tetap dibaca."""
    assert ss.parse_halaman(halaman("beras")) is not None


def test_halaman_tantangan_dihentikan():
    with pytest.raises(ss.SumberDitolak):
        ss.parse_halaman("<html><div class='cf-turnstile'></div>Just a moment...</html>")


def test_struktur_berubah():
    with pytest.raises(ss.StrukturBerubah):
        ss.parse_halaman("<html><table>harga</table></html>")


@pytest.mark.parametrize("masuk,keluar", [(16000, 16000), ("16.000", 16000), ("Rp 15.500", 15500), (None, 0), ("", 0)])
def test_format_harga(masuk, keluar):
    rows = ss.baris_dari_data({"Medan Area": {"pasar": [{"nama": "Pasar Bakti", "harga": masuk}]}}, "2026-10-15", "beras")
    assert rows == [{"tanggal": "2026-10-15", "kecamatan": "Medan Area", "nama_pasar": "Pasar Bakti",
                     "komoditas": "beras", "harga": keluar, "sumber": "simpang_medan"}]


def test_ambil_semua_komoditas_per_tanggal():
    sesi = SesiTiruan()
    rows, mentah, info = ss.ambil([date(2026, 10, 15), date(2026, 10, 16)], sesi, jeda=0)
    assert info["permintaan"] == 24 and len(mentah) == 24
    assert len(rows) == 2 * 12 * 21                      # grid penuh seperti master (252 baris per hari)
    assert {c["id_komoditi"] for c in sesi.panggilan} == {str(k) for k in ss.KOMODITI}
    assert all(c["drtanggal"] == c["sptanggal"] for c in sesi.panggilan)


def test_telur_memakai_id_telur_ras():
    assert ss.KOMODITI[27] == "telur ayam" and 25 not in ss.KOMODITI and 26 not in ss.KOMODITI


@pytest.mark.parametrize("kode", [403, 429, 503])
def test_penolakan_http_menghentikan(kode):
    with pytest.raises(ss.SumberDitolak):
        ss.ambil([date(2026, 10, 15)], SesiTiruan(status=kode), jeda=0)


def test_parse_sp2kp():
    teks = '{"data": [{"variant": "Garam Halus", "variant_id": 41, "satuan": "kg", ' \
           '"daftarHarga": [{"date": "2026-10-15", "harga": 9000}, {"date": "2026-10-16", "harga": "8500.0"}]}]}'
    assert sp.parse_respons(teks) == [{"tanggal": "2026-10-15", "harga": 9000}, {"tanggal": "2026-10-16", "harga": 8500}]


def test_ambil_sp2kp():
    class Sesi:
        def __init__(self):
            self.panggilan = []

        def post(self, url, data=None, timeout=None):
            self.panggilan.append(data)
            return Respons('{"data": [{"daftarHarga": [{"date": "2026-10-15", "harga": 9000}]}]}')

    s = Sesi()
    rows, _, info = sp.ambil(date(2026, 10, 15), date(2026, 10, 16), s,
                             {"pusat pasar": {"id": 1, "kecamatan": "Medan Kota"}}, jeda=0)
    assert info["permintaan"] == 2 and len(rows) == 2
    assert {r["komoditas"] for r in rows} == {"Garam Halus", "Susu Bubuk"}
    assert rows[0]["nama_pasar"] == "pusat pasar" and rows[0]["kecamatan"] == "Medan Kota"
    assert s.panggilan[0]["kode_kab_kota"] == "1271" and s.panggilan[0]["start_date"] == "2026-10-15"