#!/usr/bin/env python3
"""Impor CSV 6 kolom lewat API Go (POST /api/harga/import). Hanya memakai pustaka standar.

    python etl/impor_csv.py data/dev/harga_dev.csv
    python etl/impor_csv.py data/processed/harga_harian.csv --api http://localhost:8080

Aman dijalankan berulang: baris yang sudah ada dilewati (idempotent).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def multipart(nama_field: str, nama_file: str, isi: bytes) -> tuple[bytes, str]:
    batas = uuid.uuid4().hex
    kepala = (
        f"--{batas}\r\n"
        f'Content-Disposition: form-data; name="{nama_field}"; filename="{nama_file}"\r\n'
        "Content-Type: text/csv\r\n\r\n"
    ).encode()
    badan = kepala + isi + f"\r\n--{batas}--\r\n".encode()
    return badan, f"multipart/form-data; boundary={batas}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("berkas")
    ap.add_argument("--api", default="http://localhost:8080", help="alamat backend Go (bawaan http://localhost:8080)")
    a = ap.parse_args()

    p = Path(a.berkas)
    if not p.is_file():
        print(f"Berkas tidak ditemukan: {p}", file=sys.stderr)
        return 2
    badan, tipe = multipart("file", p.name, p.read_bytes())
    req = urllib.request.Request(a.api.rstrip("/") + "/api/harga/import", data=badan, headers={"Content-Type": tipe}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            hasil = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"API menolak ({e.code}): {e.read().decode(errors='replace')[:500]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Backend tidak terjangkau di {a.api}: {e.reason}", file=sys.stderr)
        return 1

    print(
        f"Baris dibaca {hasil['total_baris']} | baru disimpan {hasil['disisipkan']} | "
        f"dilewati (sudah ada) {hasil['dilewati_sudah_ada']} | tidak valid {hasil['tidak_valid']}"
    )
    for g in hasil.get("galat", [])[:20]:
        print(f"  baris {g['baris']}: {g['pesan']}")
    if hasil.get("peringatan_total"):
        print(f"  {hasil['peringatan_total']} baris berubah harga > 50% (tetap disimpan)")
    if hasil["disisipkan"]:
        print(f"Versi data {hasil['versi_data']}; model dilatih ulang otomatis (pantau di web).")
    return 0 if hasil["tidak_valid"] == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
