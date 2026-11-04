"""
scraper_simpang.py — Scraper otomatis data harga bahan pokok dari SIMPANG Pemko Medan
=======================================================================================
Website: https://simpang.medan.go.id/?menu=harga

Fitur:
  - Menggunakan curl_cffi (impersonate Chrome) untuk bypass proteksi Cloudflare Turnstile
  - Mengambil data harga harian per komoditas dan per pasar dari SIMPANG Pemko Medan
  - Ekstraksi otomatis tanggal pembaruan dari website (format YYYY-MM-DD)
  - Output langsung kompatibel dengan pipeline ETL proyek (6 kolom standar)

Cara pakai:
  python scripts/scraper_simpang.py                          # simpan ke data/raw/scraper_output.csv
  python scripts/scraper_simpang.py --output data/raw/hasil.csv
  python scripts/scraper_simpang.py --tanggal 2026-11-03     # paksa tanggal tertentu
  python scripts/scraper_simpang.py --dry-run                # cek koneksi tanpa simpan
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Fix encoding untuk Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Dependency check ──────────────────────────────────────────────────────────
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as cffi_requests
    HAS_CURL_CFFI = False

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ Library BeautifulSoup belum terinstall. Jalankan: pip install beautifulsoup4")
    sys.exit(1)

# ─── Konfigurasi ───────────────────────────────────────────────────────────────
BASE_URL = "https://simpang.medan.go.id"
MENU_HARGA_URL = "https://simpang.medan.go.id/?menu=harga"
MENU_PETA_URL = "https://simpang.medan.go.id/?menu=peta"

BULAN_INDO = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
}

# Pemetaan komoditas SIMPANG -> kode proyek
PETA_KOMODITAS = {
    "beras": "beras_medium",
    "beras medium": "beras_medium",
    "bawang putih": "bawang_putih",
    "bawang merah": "bawang_merah",
    "cabai merah": "cabai_merah",
    "cabai rawit": "cabai_rawit",
    "cabe merah": "cabai_merah",
    "cabe rawit": "cabai_rawit",
    "daging ayam": "daging_ayam_ras",
    "daging ayam ras": "daging_ayam_ras",
    "ayam ras": "daging_ayam_ras",
    "daging sapi": "daging_sapi",
    "gula pasir": "gula_pasir",
    "jagung": "jagung",
    "kedelai": "kedelai",
    "minyak goreng": "minyak_goreng_curah",
    "minyak goreng curah": "minyak_goreng_curah",
    "minyak goreng kuning curah": "minyak_goreng_curah",
    "telur ayam": "telur_ayam_ras",
    "telur ras": "telur_ayam_ras",
    "telur buras": "telur_ayam_ras",
    "telur itik": "telur_ayam_ras",
}


def bersihkan_harga(teks: str) -> int | None:
    if not teks:
        return None
    angka = re.sub(r"[^\d]", "", str(teks))
    if not angka:
        return None
    h = int(angka)
    return h if 1000 <= h <= 10_000_000 else None


def normalisasi_komoditas(nama: str) -> str | None:
    key = nama.strip().lower()
    if key in PETA_KOMODITAS:
        return PETA_KOMODITAS[key]
    for k, v in PETA_KOMODITAS.items():
        if k in key or key in k:
            return v
    return None


def fetch_url(url: str) -> str | None:
    """Ambil konten URL dengan curl_cffi (bypass Cloudflare) atau fallback ke requests."""
    try:
        if HAS_CURL_CFFI:
            r = cffi_requests.get(url, impersonate="chrome120", timeout=20)
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            r = cffi_requests.get(url, headers=headers, timeout=20)

        if r.status_code == 200:
            return r.text
        print(f"  ⚠️ HTTP {r.status_code} saat mengakses {url}")
        return None
    except Exception as e:
        print(f"  ❌ Gagal mengakses {url}: {e}")
        return None


def ekstrak_tanggal_web(html: str) -> str | None:
    """Cari teks 'Diperbarui DD Bulan YYYY' di halaman."""
    match = re.search(r"Diperbarui\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", html, re.IGNORECASE)
    if match:
        hari = int(match.group(1))
        bulan_str = match.group(2).lower()
        tahun = int(match.group(3))
        bulan = BULAN_INDO.get(bulan_str)
        if bulan:
            try:
                return date(tahun, bulan, hari).isoformat()
            except ValueError:
                pass
    return None


def parse_menu_harga(html: str, tanggal_default: str) -> list[dict]:
    """Parse harga komoditas per pasar dari halaman ?menu=harga."""
    soup = BeautifulSoup(html, "html.parser")
    tanggal_web = ekstrak_tanggal_web(html)
    tanggal = tanggal_web or tanggal_default

    print(f"  📅 Tanggal data terdeteksi: {tanggal}")

    cards = soup.find_all("div", class_="price-card")
    print(f"  📦 Ditemukan {len(cards)} kartu komoditas")

    hasil = []
    for c in cards:
        komoditi_el = c.find("div", class_="komoditi")
        if not komoditi_el:
            continue
        nama_komoditi_mentah = komoditi_el.text.strip()
        kode_komoditas = normalisasi_komoditas(nama_komoditi_mentah)
        if not kode_komoditas:
            continue

        pasar_div = c.find("div", class_="pasar")
        if not pasar_div:
            continue

        # Format tiap baris di pasar: "Medan Area [ Pasar Bakti ] : Rp 16.000"
        for line in pasar_div.stripped_strings:
            m = re.match(r"^(.*?)\s*\[\s*(.*?)\s*\]\s*:\s*Rp\s*([\d\.]+)", line)
            if m:
                kecamatan, nama_pasar, harga_str = m.groups()
                harga = bersihkan_harga(harga_str)
                if harga:
                    hasil.append({
                        "tanggal": tanggal,
                        "kecamatan": kecamatan.strip(),
                        "nama_pasar": nama_pasar.strip(),
                        "komoditas": kode_komoditas,
                        "harga": harga,
                        "sumber": "SIMPANG",
                    })

    return hasil


def simpan_csv(data: list[dict], path_output: str) -> bool:
    if not data:
        print("⚠️ Tidak ada data untuk disimpan!")
        return False

    Path(path_output).parent.mkdir(parents=True, exist_ok=True)

    # Dedup
    seen = set()
    unik = []
    for r in data:
        k = (r["tanggal"], r["kecamatan"], r["nama_pasar"], r["komoditas"])
        if k not in seen:
            seen.add(k)
            unik.append(r)

    with open(path_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["tanggal", "kecamatan", "nama_pasar", "komoditas", "harga", "sumber"]
        )
        writer.writeheader()
        writer.writerows(unik)

    print(f"\n✅ Berhasil simpan {len(unik)} baris ke: {path_output}")
    print(f"   Komoditas unik: {sorted(set(r['komoditas'] for r in unik))}")
    print(f"   Pasar unik    : {len(set(r['nama_pasar'] for r in unik))} pasar")
    return True


def main():
    parser = argparse.ArgumentParser(description="Scraper otomatis SIMPANG Pemko Medan")
    parser.add_argument(
        "--output", default="data/raw/scraper_output.csv",
        help="Path file CSV output (default: data/raw/scraper_output.csv)"
    )
    parser.add_argument(
        "--tanggal", default=date.today().isoformat(),
        help="Tanggal default jika tidak terdeteksi dari web (format YYYY-MM-DD)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Cek koneksi dan scraping saja, tidak simpan file"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  SCRAPER SIMPANG PEMKO MEDAN (Bypass Cloudflare Aktif)")
    print(f"  Target URL : {MENU_HARGA_URL}")
    print(f"  Engine     : {'curl_cffi (Chrome 120)' if HAS_CURL_CFFI else 'requests standard'}")
    print("=" * 60)

    print("\n🌐 Mengunduh halaman harga pangan SIMPANG...")
    html = fetch_url(MENU_HARGA_URL)
    if not html:
        print("❌ Gagal mengunduh halaman. Periksa koneksi internet.")
        sys.exit(1)

    data = parse_menu_harga(html, args.tanggal)
    print(f"  📊 Hasil ekstraksi: {len(data)} entri harga")

    if args.dry_run:
        print("\n✅ Dry-run selesai. Data berhasil diekstrak tanpa disimpan ke file.")
        for r in data[:5]:
            print(f"   {r}")
        sys.exit(0)

    if simpan_csv(data, args.output):
        print("\n🚀 Langkah selanjutnya (jalankan pipeline):")
        print(f"   python scripts/pipeline_update_data.py --skip-scrape")
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
