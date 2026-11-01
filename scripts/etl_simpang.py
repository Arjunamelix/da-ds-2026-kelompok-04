#!/usr/bin/env python3
"""ETL SIMPANG: data_harian_simpang_medan.csv (mentah) -> CSV 6 kolom format impor.

Mentah  : Bahan_Pokok, Kecamatan, Pasar, Harga, Rata_Rata_Kecamatan, Tanggal
Keluaran: tanggal, kecamatan, nama_pasar, komoditas, harga, sumber   (sumber = SIMPANG)

Aturan (Project.md 5.3 dan 5.4):
- Harga 0 berarti "tidak ada data" pada tanggal itu, bukan harga nol: baris DIBUANG (tidak ada angka buatan).
- Spasi di tepi nama dipangkas (mis. " Pasar Pendidikan"). Satu pasar, satu ejaan.
- Rata_Rata_Kecamatan tidak diimpor: turunan (terbukti sama dengan rata-rata harga>0 pasar sekecamatan).
- Harga di luar batas wajar komoditas (config/referensi.json) DITOLAK dan ditulis ke berkas terpisah untuk ditinjau.
- Harga yang menyimpang > 40% dari median pasar-pasar lain pada hari yang sama (hanya dinilai bila >= 5 pasar
  melapor hari itu) dianggap dugaan salah input: DITOLAK dan ditulis ke berkas yang sama dengan alasannya.
  Ambang dapat diubah (--ambang-menyimpang) atau dimatikan (--ambang-menyimpang 0).

Pemakaian:
  python scripts/etl_simpang.py data/raw/simpang/data_harian_simpang_medan.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ASUMSI yang harus dikonfirmasi tim (jenis beras dan minyak goreng tidak tertulis di data).
PETA_KOMODITAS = {
    "beras": "beras_medium",
    "minyak goreng": "minyak_goreng_curah",
    "bawang merah": "bawang_merah",
    "bawang putih": "bawang_putih",
    "daging sapi": "daging_sapi",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mentah")
    ap.add_argument("--keluar", default=str(ROOT / "data" / "processed" / "harga_harian_simpang.csv"))
    ap.add_argument("--ditolak", default=str(ROOT / "data" / "processed" / "simpang_ditolak.csv"))
    ap.add_argument("--ambang-menyimpang", type=float, default=0.40, help="0 = matikan penolakan")
    ap.add_argument("--min-pasar", type=int, default=5, help="minimal pasar melapor agar median hari itu dipercaya")
    a = ap.parse_args()

    ref = json.loads((ROOT / "config" / "referensi.json").read_text(encoding="utf-8"))
    batas = {k["kode"]: (k["min"], k["max"]) for k in ref["komoditas"]}
    kecamatan_sah = set(ref["kecamatan"])

    df = pd.read_csv(a.mentah, dtype={"Harga": "int64"})
    n_mentah = len(df)
    for k in ("Bahan_Pokok", "Kecamatan", "Pasar"):
        df[k] = df[k].str.strip()
    df["Bahan_Pokok"] = df["Bahan_Pokok"].str.lower()

    tak_dikenal = sorted(set(df["Bahan_Pokok"]) - set(PETA_KOMODITAS))
    if tak_dikenal:
        raise SystemExit(f"Komoditas tanpa pemetaan: {tak_dikenal}")
    tak_sah = sorted(set(df["Kecamatan"]) - kecamatan_sah)
    if tak_sah:
        raise SystemExit(f"Kecamatan di luar 21 kecamatan baku: {tak_sah}")
    if df.duplicated(["Tanggal", "Pasar", "Bahan_Pokok"]).any():
        raise SystemExit("Ada duplikat (tanggal, pasar, komoditas) di data mentah.")

    df["komoditas"] = df["Bahan_Pokok"].map(PETA_KOMODITAS)

    ada = df[df["Harga"] > 0].copy()
    n_nol = n_mentah - len(ada)

    lo = ada["komoditas"].map(lambda k: batas[k][0])
    hi = ada["komoditas"].map(lambda k: batas[k][1])
    luar = (ada["Harga"] < lo) | (ada["Harga"] > hi)
    ditolak = ada[luar].copy()
    ditolak["alasan"] = "di luar batas wajar"
    ok = ada[~luar].copy()

    # Dugaan salah input: menyimpang jauh dari median pasar lain pada hari yang sama.
    grp = ok.groupby(["Tanggal", "komoditas"])["Harga"]
    med = grp.transform("median")
    n_lapor = grp.transform("size")
    if a.ambang_menyimpang > 0:
        sim = ((ok["Harga"] / med - 1).abs() > a.ambang_menyimpang) & (n_lapor >= a.min_pasar)
    else:
        sim = pd.Series(False, index=ok.index)
    d2 = ok[sim].copy()
    d2["alasan"] = f"menyimpang > {a.ambang_menyimpang:.0%} dari median pasar lain hari itu (dugaan salah input)"
    n_sim = len(d2)
    ditolak = pd.concat([ditolak, d2])
    ok = ok[~sim].copy()

    out = ok.rename(columns={"Tanggal": "tanggal", "Kecamatan": "kecamatan", "Pasar": "nama_pasar", "Harga": "harga"})
    out["sumber"] = "SIMPANG"
    out = out[["tanggal", "kecamatan", "nama_pasar", "komoditas", "harga", "sumber"]].sort_values(
        ["tanggal", "kecamatan", "nama_pasar", "komoditas"]
    )
    Path(a.keluar).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.keluar, index=False)
    ditolak[["Tanggal", "Kecamatan", "Pasar", "komoditas", "Harga", "alasan"]].sort_values(["Tanggal", "Pasar"]).to_csv(a.ditolak, index=False)

    print(f"mentah               : {n_mentah:>7}")
    print(f"dibuang (harga = 0)  : {n_nol:>7}  ({n_nol / n_mentah:.1%}) -> tidak ada data pada hari itu")
    print(f"ditolak              : {len(ditolak):>7}  -> {a.ditolak}")
    print(f"diimpor              : {len(out):>7}  -> {a.keluar}")
    print(f"  (dari ditolak: {n_sim} dugaan salah input, menyimpang > {a.ambang_menyimpang:.0%} dari median hari itu)")
    print("\nDitolak per komoditas:")
    print(ditolak["komoditas"].value_counts().to_string() if len(ditolak) else "  (tidak ada)")
    print("\nDiimpor per komoditas:")
    print(out["komoditas"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
