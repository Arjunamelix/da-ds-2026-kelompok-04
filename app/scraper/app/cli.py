"""Jalankan satu tarikan dari terminal.

  python -m app.cli --dry-run         ambil dan bersihkan saja; master dan database TIDAK diubah
  python -m app.cli                   tarikan penuh (sama dengan tarikan terjadwal)
  python -m app.cli --dari 2026-10-16 --sampai 2026-10-20   rentang tertentu (mis. mengisi celah)

Di laptop (tanpa Docker), jalankan dari folder induk repo dengan:
  $env:PYTHONPATH="scraper"; $env:BACKEND_URL="http://localhost:8080"; python -m app.cli --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date

from . import tarikan


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="jangan ubah master dan database")
    ap.add_argument("--dari", type=date.fromisoformat, help="tanggal awal (YYYY-MM-DD); bawaan: tanggal terakhir di database - 7 hari")
    ap.add_argument("--sampai", type=date.fromisoformat, help="tanggal akhir (YYYY-MM-DD); bawaan: hari ini")
    ap.add_argument("--sumber", help="mis. simpang atau simpang,sp2kp; bawaan: SCRAPER_SUMBER")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    sumber = tuple(s.strip() for s in a.sumber.split(",")) if a.sumber else None
    hasil = tarikan.jalankan("cli", dry_run=a.dry_run, dari=a.dari, sampai=a.sampai, sumber=sumber)
    print(json.dumps(hasil, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()