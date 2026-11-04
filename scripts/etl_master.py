"""ETL untuk data/raw/master_data_harian.csv (SIMPANG Medan + SP2KP).

Masukan : CSV 6 kolom: tanggal,kecamatan,nama_pasar,komoditas,harga,sumber
          (komoditas berupa nama, sumber berupa simpang_medan / sp2kp, harga 0 = tidak ada data)
Keluaran: satu CSV per sumber, siap impor ke POST /api/harga/import:
            <out>/harga_harian_simpang.csv
            <out>/harga_harian_sp2kp.csv
          dan <out>/master_ditolak.csv (baris yang dibuang beserta alasannya).

Aturan pembersihan ada di scripts/aturan_bersih.py (dipakai juga oleh pengumpul data otomatis):
  1. Nama komoditas, sumber, dan pasar dibakukan; spasi di tepi dibuang.
  2. Komoditas yang isinya salinan persis komoditas lain dibuang (kesalahan scraping).
  3. Harga 0 dibuang (tidak ada data hari itu).
  4. Harga yang dilaporkan per butir (telur sebelum Feb 2025) ditolak, lalu
     harga di luar batas wajar komoditas ditolak.
  5. Harga yang menyimpang > ambang dari median semua pasar pada hari, komoditas,
     dan sumber yang sama ditolak, hanya bila minimal --min-pasar pasar melapor.
Deret tidak pernah dicampur antar-sumber: aturan 5 dihitung per sumber.

Pemakaian:
  python scripts/etl_master.py            (atau tombol Run di VS Code; memakai berkas bawaan)
  python scripts/etl_master.py data/raw/master_data_harian.csv
  python scripts/etl_master.py data/raw/master_data_harian.csv --out-dir data/processed --ambang-menyimpang 0.4 --min-pasar 5
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aturan_bersih import BERKAS_KELUAR, KOLOM, bersihkan  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    akar = Path(__file__).resolve().parent.parent  # folder induk repo
    ap.add_argument("input", nargs="?", default=str(akar / "data" / "raw" / "master_data_harian.csv"),
                    help="CSV mentah (bawaan: data/raw/master_data_harian.csv)")
    ap.add_argument("--out-dir", default=str(akar / "data" / "processed"))
    ap.add_argument("--ambang-menyimpang", type=float, default=0.4)
    ap.add_argument("--min-pasar", type=int, default=5)
    a = ap.parse_args()

    df = pd.read_csv(a.input, dtype={"harga": "int64"})
    try:
        h = bersihkan(df, ambang_menyimpang=a.ambang_menyimpang, min_pasar=a.min_pasar)
    except ValueError as e:
        sys.exit(str(e))
    for p in h.peringatan:
        print("PERINGATAN:", p)

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for sumber, d in h.bersih.groupby("sumber"):
        d[KOLOM].to_csv(out / BERKAS_KELUAR[sumber], index=False)
    h.ditolak.to_csv(out / "master_ditolak.csv", index=False)

    dt, df_ok = h.ditolak, h.bersih
    print(f"\nBaris mentah            : {h.n_mentah:>7,}")
    print(f"Harga 0 (dibuang)       : {h.n_nol:>7,}")
    for alasan, n in dt["alasan"].value_counts().items():
        print(f"Ditolak - {alasan:<40}: {n:>7,}")
    print(f"Baris valid             : {len(df_ok):>7,}")
    print(f"Cek: {h.n_mentah:,} - {h.n_nol:,} - {len(dt):,} = {h.n_mentah - h.n_nol - len(dt):,}\n")
    ring = df_ok.groupby(["sumber", "komoditas"]).agg(baris=("harga", "size"), hari=("tanggal", "nunique"),
                                                      pasar=("nama_pasar", "nunique"),
                                                      median=("harga", "median"))
    print(ring.to_string())
    for sumber, f in BERKAS_KELUAR.items():
        if sumber in set(df_ok["sumber"]):
            print(f"-> {out / f}")
    print(f"-> {out / 'master_ditolak.csv'}")


if __name__ == "__main__":
    main()