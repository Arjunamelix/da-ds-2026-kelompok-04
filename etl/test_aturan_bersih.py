"""Tes etl/aturan_bersih.py.  Jalankan:  python -m pytest etl/test_aturan_bersih.py -q"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aturan_bersih import KOLOM, bersihkan, gabung_ke_master  # noqa: E402


def baris(tanggal, pasar, komoditas, harga, kecamatan="Medan Area", sumber="simpang_medan"):
    return {"tanggal": tanggal, "kecamatan": kecamatan, "nama_pasar": pasar, "komoditas": komoditas,
            "harga": harga, "sumber": sumber}


def df(*rows):
    return pd.DataFrame(list(rows), columns=KOLOM)


@pytest.fixture
def master():
    return df(
        baris("2026-10-14", "Pasar Bakti", "beras", 16000),
        baris("2026-10-15", "Pasar Bakti", "beras", 16000),
        baris("2026-10-15", "Pasar Sukaramai", "beras", 0),       # belum ada laporan saat ditarik
    )


# --- penggabungan ke master ---------------------------------------------------

def test_baris_baru_ditambahkan(master):
    hasil, info = gabung_ke_master(master, df(baris("2026-10-16", "Pasar Bakti", "beras", 16500)))
    assert len(hasil) == 4 and info["ditambahkan"] == 1
    assert hasil.iloc[-1]["tanggal"] == "2026-10-16"


def test_tarikan_ulang_tidak_menggandakan(master):
    baru = df(baris("2026-10-16", "Pasar Bakti", "beras", 16500), baris("2026-10-15", "Pasar Bakti", "beras", 16000))
    sekali, _ = gabung_ke_master(master, baru)
    dua_kali, info = gabung_ke_master(sekali, baru)
    assert len(dua_kali) == len(sekali) == 4
    assert info["ditambahkan"] == 0 and info["sudah_ada"] == 2
    assert dua_kali.equals(sekali)


def test_harga_nol_diisi_saat_harga_menyusul(master):
    hasil, info = gabung_ke_master(master, df(baris("2026-10-15", "Pasar Sukaramai", "beras", 15500)))
    assert info["diisi_dari_0"] == 1 and len(hasil) == 3
    assert hasil.loc[hasil["nama_pasar"] == "Pasar Sukaramai", "harga"].item() == 15500


def test_harga_nol_baru_tidak_menghapus_harga_lama(master):
    hasil, info = gabung_ke_master(master, df(baris("2026-10-15", "Pasar Bakti", "beras", 0)))
    assert hasil.loc[(hasil["tanggal"] == "2026-10-15") & (hasil["nama_pasar"] == "Pasar Bakti"), "harga"].item() == 16000
    assert info["sudah_ada"] == 1


def test_revisi_harga_lama_diabaikan(master):
    hasil, info = gabung_ke_master(master, df(baris("2026-10-15", "Pasar Bakti", "beras", 17000)))
    assert info["revisi_diabaikan"] == 1
    assert hasil.equals(master)


def test_kunci_tidak_peka_spasi_dan_huruf(master):
    hasil, info = gabung_ke_master(master, df(baris("2026-10-15", " Pasar Bakti ", "Beras", 16000, sumber="SIMPANG_MEDAN")))
    assert len(hasil) == 3 and info["sudah_ada"] == 1


def test_duplikat_di_dalam_tarikan_diambil_sekali(master):
    baru = df(baris("2026-10-16", "Pasar Bakti", "beras", 16500), baris("2026-10-16", "Pasar Bakti", "beras", 16600))
    hasil, info = gabung_ke_master(master, baru)
    assert info["ditambahkan"] == 1
    assert hasil.loc[hasil["tanggal"] == "2026-10-16", "harga"].item() == 16600


# --- pembersihan ----------------------------------------------------------------

def test_aturan_dasar():
    h = bersihkan(df(
        baris("2026-10-15", "Pasar Bakti", "beras", 16000),
        baris("2026-10-15", "Pasar Belawan", "beras", 0),                 # harga 0
        baris("2026-10-15", "Pasar Sambas", "beras", 15),                 # di luar batas wajar
        baris("2026-10-15", "Pasar Sunggal", "telur ayam", 1800),         # per butir
        baris("2026-10-15", "pusat pasar", "Garam Halus", 9000, kecamatan="Medan Kota", sumber="sp2kp"),
        baris("2026-10-15", "Pasar Induk", "emas", 1000000),              # komoditas tidak dikenal
    ))
    assert h.n_nol == 1
    assert set(h.bersih["komoditas"]) == {"beras_medium", "garam_halus"}
    assert "Pusat Pasar" in set(h.bersih["nama_pasar"]) and set(h.bersih["sumber"]) == {"SIMPANG", "SP2KP"}
    assert set(h.ditolak["alasan"]) == {"di luar batas wajar", "satuan per butir, bukan per kg", "komoditas tidak dikenal"}


def test_salinan_butuh_cukup_baris():
    """Dua komoditas stabil berharga sama 3 hari: dengan min_baris_salinan=50 tidak dianggap salinan."""
    rows = []
    for t in ("2026-10-13", "2026-10-14", "2026-10-15"):
        rows += [baris(t, "Pasar Bakti", "gula pasir", 18000), baris(t, "Pasar Bakti", "minyak goreng", 18000)]
    assert len(bersihkan(df(*rows)).bersih) == 3                          # perilaku master: dibuang sebagai salinan
    assert len(bersihkan(df(*rows), min_baris_salinan=50).bersih) == 6    # perilaku pengumpul: dipertahankan