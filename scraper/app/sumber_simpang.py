"""Adapter SIMPANG Pemko Medan (https://simpang.medan.go.id/?menu=peta).

Satu permintaan POST per komoditas per tanggal (drtanggal = sptanggal = tanggal). Halaman memuat objek JavaScript
`const datahargakecamatan = {...};` berisi semua kecamatan dan pasar beserta harganya (0 = belum ada laporan).
Cara ini mengikuti scraper tim di proyek `dataset_processing` (scrap_simpang_medan.py).

Etika akses: robots.txt SIMPANG mengizinkan akses otomatis (User-agent: * / Allow: /, dicek 4 Nov 2026).
Permintaan memakai identitas jujur dan jeda antarpermintaan. Bila situs menolak (403/429/503) atau mengirim halaman
tantangan anti-bot, adapter BERHENTI dan melaporkan galat; tidak ada upaya menembus perlindungan.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import date

import requests

log = logging.getLogger("scraper.simpang")

URL = "https://simpang.medan.go.id/?menu=peta"
SUMBER = "simpang_medan"           # nilai kolom `sumber` di master_data_harian.csv
SUMBER_BACKEND = "SIMPANG"         # kode sumber di database

# id_komoditi SIMPANG -> nama komoditas seperti di master_data_harian.csv
KOMODITI = {
    1: "beras",
    6: "bawang putih",
    31: "bawang merah",
    8: "cabai merah",
    9: "cabai rawit",
    11: "daging ayam ras",
    12: "daging sapi",
    14: "gula pasir",
    19: "jagung",
    22: "kedelai",
    23: "minyak goreng",           # "Minyak Goreng Kuning Curah" di SIMPANG
    27: "telur ayam",              # "Telur Ras" (bukan 25 Telur Buras atau 26 Telur Itik)
}

_POLA_DATA = re.compile(r"const\s+datahargakecamatan\s*=\s*({.*?});", re.DOTALL | re.IGNORECASE)
_TANDA_KOSONG = "tidak ada harga untuk komoditi"
_TANDA_TANTANGAN = ("cf-turnstile", "cf-chl", "just a moment", "challenge-form", "attention required")


class SumberDitolak(RuntimeError):
    """Situs menolak permintaan otomatis; tarikan sumber ini dihentikan."""


class StrukturBerubah(RuntimeError):
    """Halaman tidak berisi data yang dikenali (struktur situs berubah)."""


def parse_halaman(html: str) -> dict | None:
    """Kembalikan objek datahargakecamatan, atau None bila sumber menyatakan tidak ada harga untuk tanggal itu."""
    rendah = html.lower()
    m = _POLA_DATA.search(html)
    if m:
        return json.loads(m.group(1))
    if _TANDA_KOSONG in rendah:
        return None
    if any(t in rendah for t in _TANDA_TANTANGAN):
        raise SumberDitolak("SIMPANG mengirim halaman tantangan anti-bot; tarikan dihentikan (tidak ditembus)")
    raise StrukturBerubah("objek datahargakecamatan tidak ditemukan; struktur halaman SIMPANG mungkin berubah")


def _harga(v) -> int:
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    angka = re.sub(r"[^\d]", "", str(v))
    return int(angka) if angka else 0


def baris_dari_data(data: dict, tanggal: str, komoditas: str) -> list[dict]:
    """Ubah datahargakecamatan menjadi baris format master (harga 0 tetap ditulis, seperti master)."""
    rows = []
    for kecamatan, detail in (data or {}).items():
        pasar = detail.get("pasar") if isinstance(detail, dict) else None
        for p in pasar if isinstance(pasar, list) else []:
            nama = p.get("nama") if isinstance(p, dict) else None
            if not nama:
                continue
            rows.append({"tanggal": tanggal, "kecamatan": str(kecamatan), "nama_pasar": str(nama),
                         "komoditas": komoditas, "harga": _harga(p.get("harga")), "sumber": SUMBER})
    return rows


def _minta(sesi: requests.Session, tanggal: str, id_komoditi: int, batas_waktu: float, coba: int = 3) -> str:
    galat = None
    for i in range(coba):
        try:
            r = sesi.post(URL, data={"drtanggal": tanggal, "sptanggal": tanggal, "id_komoditi": str(id_komoditi)},
                          timeout=batas_waktu)
        except requests.RequestException as e:
            galat = e
        else:
            if r.status_code in (403, 429, 503):
                raise SumberDitolak(f"SIMPANG menolak permintaan (HTTP {r.status_code}); tarikan dihentikan")
            if r.status_code == 200:
                return r.text
            galat = RuntimeError(f"HTTP {r.status_code}")
        if i < coba - 1:
            time.sleep(10 * (i + 1))
    raise RuntimeError(f"gagal mengambil {tanggal} komoditi {id_komoditi} setelah {coba} percobaan: {galat}")


def ambil(tanggal: list[date], sesi: requests.Session, jeda: float = 2.0, batas_waktu: float = 30.0,
          komoditi: dict[int, str] | None = None) -> tuple[list[dict], list[dict], dict]:
    """Ambil semua komoditas untuk setiap tanggal.

    Kembalikan (baris format master, catatan mentah per permintaan, ringkasan).
    SumberDitolak diteruskan ke pemanggil (seluruh tarikan sumber ini dihentikan).
    """
    komoditi = komoditi or KOMODITI
    rows: list[dict] = []
    mentah: list[dict] = []
    permintaan = kosong = 0
    pertama = True
    log.info("SIMPANG: mengambil %d tanggal x %d komoditas = %d permintaan (jeda %.0f detik)",
             len(tanggal), len(komoditi), len(tanggal) * len(komoditi), jeda)
    for no, t in enumerate(tanggal, 1):
        ts = t.isoformat()
        awal = len(rows)
        for idk, nama in komoditi.items():
            if not pertama and jeda > 0:
                time.sleep(jeda)
            pertama = False
            html = _minta(sesi, ts, idk, batas_waktu)
            permintaan += 1
            data = parse_halaman(html)
            mentah.append({"tanggal": ts, "id_komoditi": idk, "komoditas": nama, "data": data})
            if data is None:
                kosong += 1
                continue
            rows.extend(baris_dari_data(data, ts, nama))
        berharga = sum(1 for r in rows[awal:] if r["harga"] > 0)
        log.info("SIMPANG %s (%d/%d): %d harga terisi", ts, no, len(tanggal), berharga)
    ringkas = {"permintaan": permintaan, "kosong": kosong, "baris": len(rows),
               "dari": tanggal[0].isoformat() if tanggal else None, "sampai": tanggal[-1].isoformat() if tanggal else None}
    log.info("SIMPANG selesai: %d permintaan, %d kosong, %d baris mentah", permintaan, kosong, len(rows))
    return rows, mentah, ringkas