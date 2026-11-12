"""Adapter SP2KP Kemendag (API export-area-daily-json).

Satu permintaan POST per varian komoditas per pasar untuk seluruh rentang tanggal. Parameter dan cara membaca
respons mengikuti scraper tim di proyek `dataset_processing` (scrap_sp2kp.py).

Pasar yang diambil diatur lewat SCRAPER_SP2KP_PASAR, mis.
  {"pasar sukaramai medan": {"id": 123, "kecamatan": "Medan Area"}, "pusat pasar": {"id": 456, "kecamatan": "Medan Kota"}}
Nama pasar memakai ejaan di master_data_harian.csv. Bila kosong, SP2KP tidak diambil.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date

import pandas as pd
import requests

log = logging.getLogger("scraper.sp2kp")

URL = "https://api-sp2kp.kemendag.go.id/report/api/average-price/export-area-daily-json"
SUMBER = "sp2kp"
SUMBER_BACKEND = "SP2KP"

# variant_id SP2KP -> nama komoditas seperti di master_data_harian.csv
VARIAN = {32: "Susu Bubuk", 41: "Garam Halus"}

PARAM_TETAP = {"level": 3, "kode_provinsi": "12", "kode_kab_kota": "1271", "skip_sat_sun": "false", "tipe_komoditas": "1"}


class SumberDitolak(RuntimeError):
    pass


def parse_respons(teks: str) -> list[dict]:
    """Kembalikan [{tanggal, harga}] dari respons JSON (daftarHarga tiap item)."""
    d = json.loads(teks)
    items = d.get("data", d.get("result", [])) if isinstance(d, dict) else d
    if isinstance(items, dict):
        items = [items]
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        for dh in it.get("daftarHarga") or []:
            t = dh.get("date", dh.get("tanggal"))
            if not t:
                continue
            out.append({"tanggal": pd.to_datetime(t).date().isoformat(), "harga": int(float(dh.get("harga") or 0))})
    return out


def ambil(dari: date, sampai: date, sesi: requests.Session, pasar: dict, jeda: float = 2.0,
          batas_waktu: float = 30.0) -> tuple[list[dict], list[dict], dict]:
    rows, mentah = [], []
    permintaan = 0
    for nama_pasar, cfg in pasar.items():
        for vid, komoditas in VARIAN.items():
            if permintaan and jeda > 0:
                time.sleep(jeda)
            data = {"start_date": dari.isoformat(), "end_date": sampai.isoformat(), "variant_ids": str(vid),
                    "pasar_id": str(cfg["id"]), **PARAM_TETAP}
            r = sesi.post(URL, data=data, timeout=batas_waktu)
            permintaan += 1
            if r.status_code in (401, 403, 429, 503):
                raise SumberDitolak(f"SP2KP menolak permintaan (HTTP {r.status_code}); tarikan dihentikan")
            r.raise_for_status()
            harga = parse_respons(r.text)
            mentah.append({"pasar": nama_pasar, "variant_id": vid, "respons": r.text[:200_000]})
            rows += [{"tanggal": h["tanggal"], "kecamatan": cfg["kecamatan"], "nama_pasar": nama_pasar,
                      "komoditas": komoditas, "harga": h["harga"], "sumber": SUMBER} for h in harga]
    log.info("SP2KP: %d permintaan, %d baris mentah", permintaan, len(rows))
    return rows, mentah, {"permintaan": permintaan, "baris": len(rows), "dari": dari.isoformat(), "sampai": sampai.isoformat()}