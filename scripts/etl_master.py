"""ETL untuk data/raw/master_data_harian.csv (SIMPANG Medan + SP2KP).

Masukan : CSV 6 kolom: tanggal,kecamatan,nama_pasar,komoditas,harga,sumber
          (komoditas berupa nama, sumber berupa simpang_medan / sp2kp, harga 0 = tidak ada data)
Keluaran: satu CSV per sumber, siap impor ke POST /api/harga/import:
            <out>/harga_harian_simpang.csv
            <out>/harga_harian_sp2kp.csv
          dan <out>/master_ditolak.csv (baris yang dibuang beserta alasannya).

Aturan (sama dengan etl_simpang.py, diperluas untuk sumber kedua):
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

Batas dan kode di bawah harus sama dengan config/referensi.json.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

SUMBER = {"simpang_medan": "SIMPANG", "sp2kp": "SP2KP"}

# nama di CSV mentah (huruf kecil) -> (kode baku, batas_min, batas_max)
KOMODITAS = {
    "beras": ("beras_medium", 8_000, 30_000),
    "bawang merah": ("bawang_merah", 10_000, 100_000),
    "bawang putih": ("bawang_putih", 10_000, 80_000),
    "minyak goreng": ("minyak_goreng_curah", 8_000, 40_000),
    "daging sapi": ("daging_sapi", 80_000, 200_000),
    "gula pasir": ("gula_pasir", 10_000, 30_000),
    "telur ayam": ("telur_ayam_ras", 15_000, 50_000),        # SIMPANG id 27 (Telur Ras)
    "cabai merah": ("cabai_merah", 10_000, 150_000),
    "cabai rawit": ("cabai_rawit", 10_000, 150_000),
    "daging ayam ras": ("daging_ayam_ras", 20_000, 60_000),
    "jagung": ("jagung", 4_000, 20_000),
    "kedelai": ("kedelai", 8_000, 30_000),
    "garam halus": ("garam_halus", 3_000, 20_000),
    "susu bubuk": ("susu_bubuk", 30_000, 100_000),           # satuan: kemasan 400 g (asumsi)
}

# Komoditas yang pada periode tertentu dilaporkan per butir, bukan per kg.
# Harga di bawah ambang ini dianggap per butir dan ditolak (tidak dikonversi).
AMBANG_PER_BUTIR = {"telur ayam": 5_000}

# ejaan pasar SP2KP -> ejaan baku yang sama dengan SIMPANG
PASAR = {
    "pasar sukaramai medan": "Pasar Sukaramai",
    "pusat pasar": "Pusat Pasar",
}

KOLOM = ["tanggal", "kecamatan", "nama_pasar", "komoditas", "harga", "sumber"]
BERKAS_KELUAR = {"SIMPANG": "harga_harian_simpang.csv", "SP2KP": "harga_harian_sp2kp.csv"}


def tolak(df, mask, alasan, ditolak):
    if mask.any():
        ditolak.append(df[mask].assign(alasan=alasan))
    return df[~mask].copy()


def cari_salinan(df):
    """Kembalikan {komoditas_salinan: komoditas_asli} untuk komoditas yang identik pada semua baris."""
    hasil = {}
    for sumber, d in df.groupby("sumber"):
        p = d.pivot_table(index=["tanggal", "nama_pasar"], columns="komoditas_mentah",
                          values="harga", aggfunc="first")
        urutan = [k for k in KOMODITAS if k in p.columns]
        for i, a in enumerate(urutan):
            for b in urutan[i + 1:]:
                sah = p[a].notna() & p[b].notna() & (p[a] > 0)
                if sah.sum() > 0 and (p.loc[sah, a] == p.loc[sah, b]).all():
                    hasil[(sumber, b)] = a
    return hasil


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
    if list(df.columns) != KOLOM:
        sys.exit(f"Header tidak sesuai. Diharapkan {KOLOM}, didapat {list(df.columns)}")
    n_mentah = len(df)
    ditolak = []

    for c in ["kecamatan", "nama_pasar", "komoditas", "sumber"]:
        df[c] = df[c].astype(str).str.strip()
    df["komoditas_mentah"] = df["komoditas"].str.lower()
    df["sumber"] = df["sumber"].str.lower()
    df["nama_pasar"] = df["nama_pasar"].map(lambda x: PASAR.get(x.lower(), x))

    df = tolak(df, ~df["sumber"].isin(SUMBER), "sumber tidak dikenal", ditolak)
    df = tolak(df, ~df["komoditas_mentah"].isin(KOMODITAS), "komoditas tidak dikenal", ditolak)
    df["sumber"] = df["sumber"].map(SUMBER)

    # 2. komoditas salinan
    for (sumber, salinan), asli in cari_salinan(df).items():
        m = (df["sumber"] == sumber) & (df["komoditas_mentah"] == salinan)
        print(f"PERINGATAN: {sumber} '{salinan}' identik dengan '{asli}' di semua baris; dibuang.")
        df = tolak(df, m, f"salinan dari {asli} (kesalahan scraping)", ditolak)

    # 3. harga 0
    n_nol = int((df["harga"] == 0).sum())
    df = df[df["harga"] != 0].copy()

    # 4a. satuan per butir (telur Jan 2024 - Jan 2025 di SIMPANG)
    for k, ambang in AMBANG_PER_BUTIR.items():
        m = (df["komoditas_mentah"] == k) & (df["harga"] < ambang)
        df = tolak(df, m, "satuan per butir, bukan per kg", ditolak)

    # 4b. batas wajar
    lo =df["komoditas_mentah"].map(lambda k: KOMODITAS[k][1])
    hi = df["komoditas_mentah"].map(lambda k: KOMODITAS[k][2])
    df = tolak(df, (df["harga"] < lo) | (df["harga"] > hi), "di luar batas wajar", ditolak)

    # 5. menyimpang dari median pasar pada hari, komoditas, dan sumber yang sama
    g = df.groupby(["tanggal", "komoditas_mentah", "sumber"])["harga"]
    med = g.transform("median")
    jml = g.transform("size")
    simpang = (jml >= a.min_pasar) & ((df["harga"] - med).abs() / med > a.ambang_menyimpang)
    df = tolak(df, simpang, f"menyimpang > {a.ambang_menyimpang:.0%} dari median pasar", ditolak)

    df["komoditas"] = df["komoditas_mentah"].map(lambda k: KOMODITAS[k][0])
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for sumber, d in df.groupby("sumber"):
        d.sort_values(["tanggal", "kecamatan", "nama_pasar", "komoditas"])[KOLOM].to_csv(
            out / BERKAS_KELUAR[sumber], index=False)
    dt = pd.concat(ditolak) if ditolak else pd.DataFrame(columns=KOLOM + ["alasan"])
    dt.drop(columns="komoditas_mentah", errors="ignore").to_csv(out / "master_ditolak.csv", index=False)

    print(f"\nBaris mentah            : {n_mentah:>7,}")
    print(f"Harga 0 (dibuang)       : {n_nol:>7,}")
    for alasan, n in dt["alasan"].value_counts().items():
        print(f"Ditolak - {alasan:<40}: {n:>7,}")
    print(f"Baris valid             : {len(df):>7,}")
    print(f"Cek: {n_mentah:,} - {n_nol:,} - {len(dt):,} = {n_mentah - n_nol - len(dt):,}\n")
    ring = df.groupby(["sumber", "komoditas"]).agg(baris=("harga", "size"), hari=("tanggal", "nunique"),
                                                   pasar=("nama_pasar", "nunique"),
                                                   median=("harga", "median"))
    print(ring.to_string())
    for sumber, f in BERKAS_KELUAR.items():
        if sumber in set(df["sumber"]):
            print(f"-> {out / f}")
    print(f"-> {out / 'master_ditolak.csv'}")


if __name__ == "__main__":
    main()