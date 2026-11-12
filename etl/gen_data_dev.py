#!/usr/bin/env python3
"""Pembangkit data SINTETIS khusus pengembangan (sumber = DEV).

Menghasilkan CSV 6 kolom (format impor) di data/dev/harga_dev.csv. Data ini BUKAN data asli:
- tidak boleh di-commit sebagai dataset (folder data/dev/ di-.gitignore),
- tidak boleh dipakai di laporan,
- harus dihapus dari database sebelum data asli dimuat dan model dilatih sungguhan.

Pemakaian:
    python etl/gen_data_dev.py                       # 2024-01-01 s.d. hari ini
    python etl/gen_data_dev.py --sampai 2026-10-20 --seed 7
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# komoditas -> (harga dasar, volatilitas harian log, amplitudo musiman, sensitif hari besar, drift tahunan)
PARAM = {
    "beras_medium": (13500, 0.002, 0.01, 0.01, 0.04),
    "cabai_merah_keriting": (45000, 0.025, 0.10, 0.20, 0.00),
    "cabai_rawit_merah": (50000, 0.028, 0.12, 0.20, 0.00),
    "bawang_merah": (35000, 0.015, 0.06, 0.12, 0.00),
    "bawang_putih": (33000, 0.008, 0.03, 0.05, 0.00),
    "minyak_goreng_curah": (15000, 0.004, 0.02, 0.05, 0.02),
    "gula_pasir": (16000, 0.003, 0.01, 0.04, 0.03),
    "telur_ayam_ras": (28000, 0.007, 0.03, 0.08, 0.02),
    "daging_ayam_ras": (34000, 0.006, 0.03, 0.07, 0.02),
    "daging_sapi": (130000, 0.003, 0.01, 0.04, 0.03),
}

# Perkiraan hari besar (sama dengan ml/app/kalender.py) untuk lonjakan musiman buatan.
HARI_BESAR = [
    "2024-03-11", "2024-04-10", "2024-06-17", "2024-12-25",
    "2025-03-01", "2025-03-31", "2025-06-06", "2025-12-25",
    "2026-02-19", "2026-03-20", "2026-05-27", "2026-12-25",
]


def bump(tgl: date, hb: list[date]) -> float:
    """Kenaikan menjelang hari besar (puncak 3 hari sebelumnya, turun setelahnya)."""
    best = 0.0
    for h in hb:
        d = (h - tgl).days
        if -4 <= d <= 14:
            best = max(best, math.exp(-((d - 3) ** 2) / 40.0))
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dari", default="2024-01-01")
    ap.add_argument("--sampai", default=date.today().isoformat())
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--keluar", default=str(ROOT / "data" / "dev" / "harga_dev.csv"))
    ap.add_argument("--bolong", type=float, default=0.02, help="peluang hari kerja tanpa baris")
    a = ap.parse_args()

    ref = json.loads((ROOT / "config" / "referensi.json").read_text(encoding="utf-8"))
    kota = ref["kota"]
    kom_info = {k["kode"]: k for k in ref["komoditas"]}
    pasar = ref["pasar"]
    rnd = random.Random(a.seed)
    hb = [date.fromisoformat(x) for x in HARI_BESAR]

    d0, d1 = date.fromisoformat(a.dari), date.fromisoformat(a.sampai)
    hari = [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]
    hari_kerja = [d for d in hari if d.weekday() < 5]

    baris = []
    for kode, (dasar, vol, musim, sens, drift) in PARAM.items():
        if kode not in kom_info:  # komoditas tidak ada di config/referensi.json (mis. cabai pada konfigurasi SIMPANG)
            continue
        info = kom_info[kode]
        lo, hi = info["min"], info["max"]
        # jalur harga kota: jalan acak ber-mean-reversion + musiman + hari besar + drift + kejutan
        x = 0.0
        jalur = {}
        for d in hari:
            x = 0.97 * x + rnd.gauss(0, vol)
            if rnd.random() < 0.004:  # kejutan pasokan
                x += rnd.choice([-1, 1]) * rnd.uniform(3, 6) * vol
            s = musim * math.sin(2 * math.pi * (d.timetuple().tm_yday / 365.0 - 0.15))
            t = (d - d0).days / 365.0
            jalur[d] = dasar * math.exp(x + s + sens * bump(d, hb) + drift * t)

        # tiap pasar = jalur kota x offset tetap x deviasi lokal AR(1) kecil
        offs = {p["nama"]: rnd.uniform(-0.04, 0.04) for p in pasar}
        dev = {p["nama"]: 0.0 for p in pasar}
        harga_pasar = {p["nama"]: {} for p in pasar}
        for d in hari:
            for p in pasar:
                dev[p["nama"]] = 0.8 * dev[p["nama"]] + rnd.gauss(0, vol * 0.5)
                harga_pasar[p["nama"]][d] = jalur[d] * math.exp(offs[p["nama"]] + dev[p["nama"]])

        def bulat(v: float) -> int:
            return int(min(max(round(v / 100.0) * 100, lo), hi))

        for d in hari_kerja:
            if rnd.random() < a.bolong:
                continue
            for p in pasar:
                baris.append((d.isoformat(), p["kecamatan"], p["nama"], kode, bulat(harga_pasar[p["nama"]][d]), "DEV"))
        # level kota: rata-rata pasar (seperti PIHPS yang menyajikan harga rata-rata kota)
        for d in hari_kerja:
            if rnd.random() < a.bolong / 2:
                continue
            rata = sum(harga_pasar[p["nama"]][d] for p in pasar) / len(pasar)
            baris.append((d.isoformat(), kota["kecamatan"], kota["nama_pasar"], kode, bulat(rata), "DEV"))

    baris.sort()
    out = Path(a.keluar)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tanggal", "kecamatan", "nama_pasar", "komoditas", "harga", "sumber"])
        w.writerows(baris)
    print(f"{len(baris)} baris ditulis ke {out} ({a.dari} s.d. {a.sampai}, sumber=DEV)")


if __name__ == "__main__":
    main()
