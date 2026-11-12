"""Alur tarikan dari ujung ke ujung dengan SIMPANG dan backend tiruan."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from conftest import SesiTiruan

from app import backend, config, jadwal, riwayat, tarikan
from app import sumber_simpang as ss
from aturan_bersih import KOLOM

WIB = ZoneInfo("Asia/Jakarta")


class BackendTiruan:
    """Menyimpan kunci baris seperti tabel harga (kunci unik); impor ulang tidak menambah baris."""

    def __init__(self, terakhir=date(2026, 10, 15)):
        self.terakhir, self.kunci, self.kiriman = terakhir, set(), []

    def tanggal_terakhir(self, sumber):
        return self.terakhir

    def impor(self, df, nama=""):
        self.kiriman.append(df.copy())
        baru = 0
        for r in df.itertuples():
            k = (r.tanggal, r.kecamatan, r.nama_pasar, r.komoditas, r.sumber)
            if k not in self.kunci:
                self.kunci.add(k)
                baru += 1
        return {"total_baris": len(df), "disisipkan": baru, "dilewati_sudah_ada": len(df) - baru, "tidak_valid": 0}


@pytest.fixture
def lingkungan(folder_data, monkeypatch):
    be = BackendTiruan()
    monkeypatch.setattr(backend, "tanggal_terakhir", be.tanggal_terakhir)
    monkeypatch.setattr(backend, "impor", be.impor)
    monkeypatch.setattr(tarikan, "sekarang", lambda: datetime(2026, 10, 22, 10, 0, tzinfo=WIB))
    sesi = SesiTiruan()
    monkeypatch.setattr(tarikan, "sesi_http", lambda: sesi)
    # master awal: 8-15 Okt seperti yang sudah ada (grid penuh dari sumber yang sama)
    rows, _, _ = ss.ambil([date(2026, 10, d) for d in range(8, 16)], SesiTiruan(), jeda=0)
    pd.DataFrame(rows, columns=KOLOM).to_csv(config.MASTER, index=False)
    return be, sesi


def test_rentang_tujuh_hari_mundur_sampai_hari_ini():
    t = tarikan.rentang(date(2026, 10, 15), date(2026, 10, 22))
    assert t[0] == date(2026, 10, 8) and t[-1] == date(2026, 10, 22) and len(t) == 15


def test_rentang_dibatasi_maks_hari(monkeypatch):
    monkeypatch.setattr(config, "MAKS_HARI", 30)
    t = tarikan.rentang(date(2025, 1, 1), date(2026, 10, 22))
    assert len(t) == 30 and t[-1] == date(2026, 10, 22)


def test_tarikan_penuh(lingkungan):
    be, sesi = lingkungan
    h = tarikan.jalankan("uji")
    s = h["sumber"]["simpang"]
    assert h["status"] == "sukses"
    assert s["ambil"]["permintaan"] == 15 * 12                       # 8-22 Okt x 12 komoditas
    # master: 16-21 Okt ditambahkan (21 Okt sebagian, tetap ditulis apa adanya); 22 Okt belum ada data
    assert s["master"]["ditambahkan"] == 6 * 252 and s["master"]["sudah_ada"] == 8 * 252
    m = pd.read_csv(config.MASTER)
    assert m["tanggal"].max() == "2026-10-21" and not m.duplicated(["tanggal", "kecamatan", "nama_pasar", "komoditas", "sumber"]).any()
    # impor: 8-20 Okt (lengkap); 21 Okt ditahan karena hanya 6 pasar
    assert s["ditahan"] == [{"tanggal": "2026-10-21", "pasar": 6}]
    assert s["tanggal_berdata"][-1] == "2026-10-20"
    assert h["baris_baru"] == s["impor"]["disisipkan"] == 13 * 252
    assert set(be.kiriman[0]["sumber"]) == {"SIMPANG"} and "beras_medium" in set(be.kiriman[0]["komoditas"])
    # mentah tersimpan, riwayat tercatat
    assert len(list((config.DIR_OTOMATIS / "simpang").glob("*.jsonl"))) == 1
    assert riwayat.baca()[-1]["status"] == "sukses"


def test_tarikan_ulang_tidak_menggandakan(lingkungan):
    be, _ = lingkungan
    tarikan.jalankan("uji")
    m1 = pd.read_csv(config.MASTER)
    h2 = tarikan.jalankan("uji")
    m2 = pd.read_csv(config.MASTER)
    assert m1.equals(m2)
    assert h2["sumber"]["simpang"]["master"]["ditambahkan"] == 0
    assert h2["baris_baru"] == 0
    assert len(be.kunci) == 13 * 252


def test_harga_susulan_mengisi_hari_sebagian(lingkungan, monkeypatch):
    be, _ = lingkungan
    tarikan.jalankan("uji")
    lengkap = SesiTiruan(lengkap_sampai="2026-10-21", sebagian="2026-10-22")    # sore hari: 21 Okt sudah lengkap
    monkeypatch.setattr(tarikan, "sesi_http", lambda: lengkap)
    h = tarikan.jalankan("uji")
    s = h["sumber"]["simpang"]
    assert s["master"]["diisi_dari_0"] == 12 * 15                             # 15 pasar yang tadinya 0 kini berharga
    assert "2026-10-21" in s["tanggal_berdata"] and h["baris_baru"] == 252
    m = pd.read_csv(config.MASTER)
    assert (m.loc[m["tanggal"] == "2026-10-21", "harga"] > 0).sum() == 252


def test_dry_run_tidak_mengubah_apa_pun(lingkungan):
    be, _ = lingkungan
    sebelum = pd.read_csv(config.MASTER)
    h = tarikan.jalankan("uji", dry_run=True)
    assert pd.read_csv(config.MASTER).equals(sebelum)
    assert be.kiriman == [] and riwayat.baca() == []
    assert "dry-run" in h["sumber"]["simpang"]["impor"]["pesan"]


def test_situs_menolak_tidak_mengimpor(lingkungan, monkeypatch):
    be, _ = lingkungan
    monkeypatch.setattr(tarikan, "sesi_http", lambda: SesiTiruan(status=403))
    h = tarikan.jalankan("uji")
    assert h["status"] == "galat" and h["sumber"]["simpang"]["jenis"] == "ditolak"
    assert be.kiriman == []


def test_backend_mati_pesan_jelas(lingkungan, monkeypatch):
    def mati(_):
        raise backend.BackendTakTerjangkau("backend tidak bisa dihubungi di http://localhost:8080")
    monkeypatch.setattr(backend, "tanggal_terakhir", mati)
    h = tarikan.jalankan("uji")
    assert h["status"] == "galat" and h["sumber"]["simpang"]["jenis"] == "backend"
    assert "docker compose" in str(backend._galat_koneksi(ConnectionError()))


def test_database_kosong_dilewati(lingkungan, monkeypatch):
    monkeypatch.setattr(backend, "tanggal_terakhir", lambda s: None)
    h = tarikan.jalankan("uji")
    assert h["status"] == "dilewati"


def test_sp2kp_tanpa_id_pasar_dilewati(lingkungan, monkeypatch):
    monkeypatch.setattr(config, "SP2KP_PASAR", {})
    h = tarikan.jalankan("uji", sumber=("simpang", "sp2kp"))
    assert h["sumber"]["sp2kp"]["status"] == "dilewati" and h["status"] == "sukses"


def test_satu_tarikan_dalam_satu_waktu(lingkungan):
    tarikan._kunci.acquire()
    try:
        with pytest.raises(tarikan.SedangBerjalan):
            tarikan.jalankan("uji")
    finally:
        tarikan._kunci.release()


@pytest.mark.parametrize("jam,harap", [
    ((7, 0), datetime(2026, 11, 4, 10, 0, tzinfo=WIB)),
    ((10, 0), datetime(2026, 11, 4, 16, 0, tzinfo=WIB)),
    ((12, 30), datetime(2026, 11, 4, 16, 0, tzinfo=WIB)),
    ((17, 0), datetime(2026, 11, 5, 10, 0, tzinfo=WIB)),
])
def test_jadwal_berikutnya(jam, harap):
    assert jadwal.berikutnya(datetime(2026, 11, 4, *jam, tzinfo=WIB), ("10:00", "16:00")) == harap


def test_tarik_saat_mulai_dilewati_bila_baru_sukses(folder_data):
    riwayat.tambah({"mulai": "2026-11-04T10:00:00+07:00", "status": "sukses"})
    assert not jadwal.perlu_tarik_saat_mulai(datetime(2026, 11, 4, 11, 0, tzinfo=WIB))
    assert jadwal.perlu_tarik_saat_mulai(datetime(2026, 11, 4, 14, 0, tzinfo=WIB))


def test_api(folder_data, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    monkeypatch.setattr(config, "AKTIF", False)
    jalan = []
    monkeypatch.setattr(main, "_latar", lambda: jalan.append(1))
    with TestClient(main.app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        st = c.get("/status").json()
        assert st["sedang_berjalan"] is False and st["jadwal"] == ["10:00", "16:00"] and st["riwayat"] == []
        assert c.post("/jalankan").status_code == 202