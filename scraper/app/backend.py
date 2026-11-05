"""Komunikasi dengan backend Go: tanggal terakhir per sumber dan impor CSV (validasi + tanpa duplikat)."""
from __future__ import annotations

import io
import time
from datetime import date

import pandas as pd
import requests

from . import config


class BackendTakTerjangkau(RuntimeError):
    """Backend Go tidak bisa dihubungi (belum dinyalakan atau BACKEND_URL salah)."""


def _galat_koneksi(e: Exception) -> BackendTakTerjangkau:
    return BackendTakTerjangkau(f"backend tidak bisa dihubungi di {config.BACKEND_URL} "
                                f"(jalankan 'docker compose up -d' atau periksa BACKEND_URL): {type(e).__name__}")


def siap(batas_detik: float = 120) -> bool:
    """Tunggu sampai backend menjawab /api/health."""
    akhir = time.time() + batas_detik
    while time.time() < akhir:
        try:
            if requests.get(f"{config.BACKEND_URL}/api/health", timeout=5).ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(3)
    return False


def tanggal_terakhir(sumber_backend: str) -> date | None:
    """Tanggal data terbaru sumber ini di database (GET /api/harga diurutkan dari tanggal terbaru)."""
    try:
        r = requests.get(f"{config.BACKEND_URL}/api/harga", params={"sumber": sumber_backend, "per_page": 1}, timeout=30)
    except (requests.ConnectionError, requests.Timeout) as e:
        raise _galat_koneksi(e) from None
    r.raise_for_status()
    data = r.json().get("data") or []
    return date.fromisoformat(data[0]["tanggal"][:10]) if data else None


def impor(df: pd.DataFrame, nama_berkas: str = "scraper.csv") -> dict:
    """Kirim baris bersih (6 kolom, kode baku) ke POST /api/harga/import."""
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    try:
        r = requests.post(f"{config.BACKEND_URL}/api/harga/import",
                          files={"file": (nama_berkas, buf.getvalue().encode("utf-8"), "text/csv")}, timeout=300)
    except (requests.ConnectionError, requests.Timeout) as e:
        raise _galat_koneksi(e) from None
    if not r.ok:
        raise RuntimeError(f"impor ditolak backend (HTTP {r.status_code}): {r.text[:300]}")
    j = r.json()
    return {k: j.get(k) for k in ("total_baris", "disisipkan", "dilewati_sudah_ada", "tidak_valid", "versi_data", "peringatan_total")}