import json
import os
import sys
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[2]                  # folder induk repo
sys.path.insert(0, str(AKAR / "scraper"))
os.environ.setdefault("SCRIPTS_DIR", str(AKAR / "etl"))
os.environ.setdefault("SCRAPER_AKTIF", "0")

REF = json.loads((AKAR / "config" / "referensi.json").read_text(encoding="utf-8"))
PASAR = [(p["kecamatan"], p["nama"]) for p in REF["pasar"]]   # 21 pasar

HARGA = {"beras": 16000, "bawang putih": 32000, "bawang merah": 30000, "cabai merah": 60000, "cabai rawit": 65000,
         "daging ayam ras": 36000, "daging sapi": 140000, "gula pasir": 18500, "jagung": 9000, "kedelai": 15000,
         "minyak goreng": 20000, "telur ayam": 27000}


def halaman(komoditas: str, n_pasar: int = 21, hari: int = 0) -> str:
    """Halaman ?menu=peta tiruan: datahargakecamatan dengan n_pasar pertama berharga, sisanya 0."""
    data = {}
    for i, (kec, nama) in enumerate(PASAR):
        harga = HARGA[komoditas] + 500 * (i % 5) + 100 * hari if i < n_pasar else 0
        data.setdefault(kec, {"rata-rata": 0, "pasar": []})["pasar"].append({"nama": nama, "harga": harga})
    return f"<html><head><script src='/cdn-cgi/challenge-platform/x.js'></script></head><body><script>" \
           f"const datahargakecamatan = {json.dumps(data)};</script></body></html>"


class Respons:
    def __init__(self, teks: str, status: int = 200):
        self.text, self.status_code = teks, status
        self.ok = status < 400

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class SesiTiruan:
    """Meniru SIMPANG: lengkap 21 pasar sampai `lengkap_sampai`, 6 pasar pada `sebagian`, kosong sesudahnya."""

    def __init__(self, lengkap_sampai="2026-10-20", sebagian="2026-10-21", status=200, teks=None):
        self.lengkap_sampai, self.sebagian, self.status, self.teks = lengkap_sampai, sebagian, status, teks
        self.panggilan = []
        self.headers = {}

    def post(self, url, data=None, timeout=None):
        self.panggilan.append(data)
        if self.teks is not None or self.status != 200:
            return Respons(self.teks or "", self.status)
        from app.sumber_simpang import KOMODITI
        t = data["drtanggal"]
        kom = KOMODITI[int(data["id_komoditi"])]
        hari = int(t[-2:])
        if t <= self.lengkap_sampai:
            return Respons(halaman(kom, 21, hari))
        if t == self.sebagian:
            return Respons(halaman(kom, 6, hari))
        return Respons("<html>Tidak ada harga untuk komoditi ini</html>")


@pytest.fixture
def folder_data(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "MASTER", tmp_path / "raw" / "master_data_harian.csv")
    monkeypatch.setattr(config, "DIR_OTOMATIS", tmp_path / "raw" / "otomatis")
    monkeypatch.setattr(config, "JEDA_DETIK", 0.0)
    (tmp_path / "raw").mkdir(parents=True)
    return tmp_path