"""
pipeline_update_data.py — Pipeline otomatis: Scrape SIMPANG -> Validasi -> Import Database
=============================================================================================
Script ini menggabungkan seluruh alur update data harian:
  1. Scrape data harga terbaru langsung dari SIMPANG Pemko Medan (bypass Cloudflare)
  2. Validasi batas wajar harga dan kecamatan berdasarkan config/referensi.json
  3. Import langsung ke PostgreSQL melalui Backend Go API (/api/harga/import)

Cara pakai:
  python scripts/pipeline_update_data.py                    # jalankan semua langkah
  python scripts/pipeline_update_data.py --api http://localhost:8080
  python scripts/pipeline_update_data.py --dry-run          # scrape & validasi tanpa import
  python scripts/pipeline_update_data.py --skip-scrape      # pakai file CSV yang sudah ada
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

# Fix encoding untuk Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DIR_PROYEK = Path(__file__).resolve().parent.parent
DIR_SCRIPTS = DIR_PROYEK / "scripts"
DIR_DATA_RAW = DIR_PROYEK / "data" / "raw"
CSV_SCRAPER = DIR_DATA_RAW / "scraper_output.csv"
REFERENSI_PATH = DIR_PROYEK / "config" / "referensi.json"

DEFAULT_API = os.environ.get("API_URL", "http://localhost:8080")
PYTHON = sys.executable


def validasi_data(csv_path: Path) -> tuple[int, int]:
    """Validasi baris terhadap referensi.json: batas min/max harga dan nama kecamatan."""
    if not REFERENSI_PATH.exists():
        print("  ⚠️ config/referensi.json tidak ditemukan, melewati validasi batas.")
        return 0, 0

    with open(REFERENSI_PATH, encoding="utf-8") as f:
        ref = json.load(f)

    batas_harga = {k["kode"]: (k.get("min", 0), k.get("max", 10_000_000)) for k in ref.get("komoditas", [])}
    kecamatan_valid = set(ref.get("kecamatan", []))

    valid = 0
    invalid = 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            kom = r.get("komoditas")
            kec = r.get("kecamatan")
            try:
                hrg = int(r.get("harga", 0))
            except ValueError:
                invalid += 1
                continue

            if kec and kec not in kecamatan_valid:
                print(f"  ⚠️ Kecamatan tidak dikenal: {kec}")
                invalid += 1
                continue

            if kom in batas_harga:
                b_min, b_max = batas_harga[kom]
                if not (b_min <= hrg <= b_max):
                    print(f"  ⚠️ Harga {kom} Rp{hrg:,} di luar batas ({b_min:,} - {b_max:,})")
                    invalid += 1
                    continue

            valid += 1

    return valid, invalid


def main():
    parser = argparse.ArgumentParser(description="Pipeline update data harga SIMPANG otomatis")
    parser.add_argument("--dry-run", action="store_true", help="Scrape dan cek tanpa import ke database")
    parser.add_argument("--skip-scrape", action="store_true", help="Gunakan file scraper_output.csv yang sudah ada")
    parser.add_argument("--api", default=DEFAULT_API, help=f"Alamat API backend (default: {DEFAULT_API})")
    parser.add_argument("--tanggal", default=date.today().isoformat(), help="Tanggal target (YYYY-MM-DD)")
    args = parser.parse_args()

    print("=" * 60)
    print("  PIPELINE UPDATE DATA HARGA BAHAN POKOK (REAL-TIME)")
    print(f"  API Backend : {args.api}")
    print(f"  Mode        : {'DRY RUN (tidak simpan ke DB)' if args.dry_run else 'LIVE UPDATE'}")
    print("=" * 60)

    # 1. Scraping
    if not args.skip_scrape:
        print("\n📡 LANGKAH 1: Scraping harga terbaru dari SIMPANG...")
        cmd_scrape = [PYTHON, str(DIR_SCRIPTS / "scraper_simpang.py"), "--output", str(CSV_SCRAPER)]
        res = subprocess.run(cmd_scrape, cwd=str(DIR_PROYEK))
        if res.returncode != 0:
            print("\n❌ Scraping gagal. Periksa koneksi internet!")
            sys.exit(1)
    else:
        print("\n⏭️ LANGKAH 1: Scraping dilewati (--skip-scrape).")

    if not CSV_SCRAPER.exists():
        print(f"❌ File tidak ditemukan: {CSV_SCRAPER}")
        sys.exit(1)

    # 2. Validasi
    print("\n🔍 LANGKAH 2: Validasi integritas & batas kewajaran data...")
    n_valid, n_invalid = validasi_data(CSV_SCRAPER)
    print(f"  ✅ Data lolos validasi: {n_valid} baris")
    if n_invalid > 0:
        print(f"  ⚠️ Data ditolak/peringatan: {n_invalid} baris")

    if args.dry_run:
        print("\n✅ Dry run selesai. Database TIDAK dimodifikasi.")
        sys.exit(0)

    # 3. Import ke Database
    print(f"\n💾 LANGKAH 3: Mengirim data ke Database melalui API ({args.api})...")
    cmd_import = [PYTHON, str(DIR_SCRIPTS / "impor_csv.py"), str(CSV_SCRAPER), "--api", args.api]
    res_import = subprocess.run(cmd_import, cwd=str(DIR_PROYEK))
    if res_import.returncode != 0:
        print("\n❌ Import gagal! Pastikan server backend sedang berjalan di:", args.api)
        sys.exit(2)

    print("\n" + "=" * 60)
    print("  🎉 SUKSES! Data harga harian berhasil diperbarui secara otomatis.")
    print("=" * 60)


if __name__ == "__main__":
    main()
