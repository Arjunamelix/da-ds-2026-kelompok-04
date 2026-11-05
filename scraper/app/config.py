"""Pengaturan layanan scraper (dari variabel lingkungan)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _int(nama: str, bawaan: int) -> int:
    try:
        return int(os.getenv(nama, bawaan))
    except ValueError:
        return bawaan


def _float(nama: str, bawaan: float) -> float:
    try:
        return float(os.getenv(nama, bawaan))
    except ValueError:
        return bawaan


def _daftar(nama: str, bawaan: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in os.getenv(nama, bawaan).split(",") if x.strip())


# Alamat backend Go (impor data dan tanggal terakhir di database)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080").rstrip("/")

# Folder data repo (di Docker: ./data dipasang ke /data)
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
MASTER = DATA_DIR / "raw" / "master_data_harian.csv"
DIR_OTOMATIS = DATA_DIR / "raw" / "otomatis"          # respons mentah per tarikan + riwayat_tarikan.jsonl

# Lokasi scripts/aturan_bersih.py (di Docker: ./scripts dipasang ke /app/scripts)
SCRIPTS_DIR = Path(os.getenv("SCRIPTS_DIR", "scripts"))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Penjadwal
AKTIF = os.getenv("SCRAPER_AKTIF", "1") == "1"                 # 0 = hanya jalan bila dipicu manual
JADWAL = _daftar("SCRAPER_JADWAL", "10:00,16:00")              # jam tarikan harian (waktu ZONA)
ZONA = os.getenv("SCRAPER_ZONA", "Asia/Jakarta")
JEDA_MIN_JAM = _float("SCRAPER_JEDA_MIN_JAM", 3.0)             # tarikan saat menyala dilewati bila sukses terakhir < N jam lalu

# Rentang tanggal
HARI_MUNDUR = _int("SCRAPER_HARI_MUNDUR", 7)                   # ambil ulang N hari sebelum tanggal terakhir di database
MAKS_HARI = _int("SCRAPER_MAKS_HARI", 60)                      # rentang terpanjang dalam satu tarikan

# Sumber
SUMBER = _daftar("SCRAPER_SUMBER", "simpang")                  # simpang, sp2kp
JEDA_DETIK = _float("SCRAPER_JEDA_DETIK", 2.0)                 # jeda antarpermintaan (sopan ke server sumber)
BATAS_WAKTU = _float("SCRAPER_BATAS_WAKTU", 30.0)              # batas waktu satu permintaan (detik)
KONTAK = os.getenv("SCRAPER_KONTAK", "").strip()               # kontak tim di User-Agent (opsional)
USER_AGENT = "HargaPanganMedan/1.0 (proyek mahasiswa IT Del" + (f"; kontak: {KONTAK}" if KONTAK else "") + ")"

# Pengaman: tanggal dengan pasar melapor kurang dari angka ini ditahan (tidak diimpor)
MIN_PASAR = {"simpang": _int("SCRAPER_MIN_PASAR_SIMPANG", 15), "sp2kp": _int("SCRAPER_MIN_PASAR_SP2KP", 1)}

# Master dataset ikut diperbarui (tanpa duplikat)
TULIS_MASTER = os.getenv("SCRAPER_TULIS_MASTER", "1") == "1"

# SP2KP: {"nama pasar seperti di master": {"id": <pasar_id SP2KP>, "kecamatan": "..."}}; kosong = SP2KP tidak diambil
try:
    SP2KP_PASAR: dict = json.loads(os.getenv("SCRAPER_SP2KP_PASAR", "{}") or "{}")
except json.JSONDecodeError:
    SP2KP_PASAR = {}