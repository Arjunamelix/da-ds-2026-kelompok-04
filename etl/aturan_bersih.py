"""Aturan pembersihan dan penggabungan data harga (dipakai bersama).

Dipakai oleh:
  - etl/etl_master.py      (manual: master_data_harian.csv -> data/processed/)
  - pengumpul data otomatis    (tarikan terjadwal dari SIMPANG dan SP2KP)

Dengan satu modul, data historis dan data baru dibersihkan dengan aturan yang persis sama.

Format mentah (6 kolom, sama dengan data/raw/master_data_harian.csv):
  tanggal, kecamatan, nama_pasar, komoditas, harga, sumber
  komoditas berupa nama ("bawang merah", "Garam Halus"), sumber "simpang_medan" / "sp2kp", harga 0 = tidak ada data.

Aturan pembersihan, berurutan:
  1. Nama komoditas, sumber, dan pasar dibakukan; spasi di tepi dibuang.
  2. Komoditas yang isinya salinan persis komoditas lain dibuang (kesalahan scraping).
  3. Harga 0 dibuang (tidak ada data hari itu).
  4. Harga yang dilaporkan per butir (telur) ditolak, lalu harga di luar batas wajar ditolak.
  5. Harga yang menyimpang > ambang dari median pasar lain pada hari, komoditas, dan sumber yang sama
     ditolak, hanya bila minimal `min_pasar` pasar melapor.
Deret tidak pernah dicampur antar-sumber: aturan 2 dan 5 dihitung per sumber.

Batas dan kode di bawah harus sama dengan config/referensi.json.
"""
from __future__ import annotations

from dataclasses import dataclass, field

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
KUNCI = ["tanggal", "kecamatan", "nama_pasar", "komoditas", "sumber"]
BERKAS_KELUAR = {"SIMPANG": "harga_harian_simpang.csv", "SP2KP": "harga_harian_sp2kp.csv"}


@dataclass
class HasilBersih:
    bersih: pd.DataFrame                 # baris valid, kode baku, siap impor (kolom KOLOM)
    ditolak: pd.DataFrame                # baris yang dibuang (kolom KOLOM + alasan), di luar harga 0
    n_mentah: int
    n_nol: int
    peringatan: list[str] = field(default_factory=list)


def _tolak(df: pd.DataFrame, mask: pd.Series, alasan: str, ditolak: list) -> pd.DataFrame:
    if mask.any():
        ditolak.append(df[mask].assign(alasan=alasan))
    return df[~mask].copy()


def cari_salinan(df: pd.DataFrame, min_baris: int = 1) -> dict:
    """{(sumber, komoditas_salinan): komoditas_asli} untuk komoditas yang identik pada semua baris.

    `min_baris`: jumlah pasangan harga (> 0) minimal sebelum dua komoditas boleh dianggap salinan.
    Untuk master 2 tahun cukup 1; untuk tarikan harian yang kecil dipakai angka lebih besar agar dua komoditas
    stabil yang kebetulan berharga sama beberapa hari tidak salah dibuang.
    """
    hasil = {}
    for sumber, d in df.groupby("sumber"):
        p = d.pivot_table(index=["tanggal", "nama_pasar"], columns="komoditas_mentah",
                          values="harga", aggfunc="first")
        urutan = [k for k in KOMODITAS if k in p.columns]
        for i, a in enumerate(urutan):
            for b in urutan[i + 1:]:
                sah = p[a].notna() & p[b].notna() & (p[a] > 0)
                if sah.sum() >= max(1, min_baris) and (p.loc[sah, a] == p.loc[sah, b]).all():
                    hasil[(sumber, b)] = a
    return hasil


def bersihkan(df: pd.DataFrame, ambang_menyimpang: float = 0.4, min_pasar: int = 5,
              min_baris_salinan: int = 1) -> HasilBersih:
    """Terapkan aturan 1-5 pada data mentah 6 kolom."""
    if list(df.columns) != KOLOM:
        raise ValueError(f"Header tidak sesuai. Diharapkan {KOLOM}, didapat {list(df.columns)}")
    df = df.copy()
    df["harga"] = df["harga"].astype("int64")
    n_mentah = len(df)
    ditolak: list = []
    peringatan: list[str] = []

    # 1. pembakuan nama
    for c in ["kecamatan", "nama_pasar", "komoditas", "sumber"]:
        df[c] = df[c].astype(str).str.strip()
    df["komoditas_mentah"] = df["komoditas"].str.lower()
    df["sumber"] = df["sumber"].str.lower()
    df["nama_pasar"] = df["nama_pasar"].map(lambda x: PASAR.get(x.lower(), x))

    df = _tolak(df, ~df["sumber"].isin(SUMBER), "sumber tidak dikenal", ditolak)
    df = _tolak(df, ~df["komoditas_mentah"].isin(KOMODITAS), "komoditas tidak dikenal", ditolak)
    df["sumber"] = df["sumber"].map(SUMBER)

    # 2. komoditas salinan
    for (sumber, salinan), asli in cari_salinan(df, min_baris_salinan).items():
        m = (df["sumber"] == sumber) & (df["komoditas_mentah"] == salinan)
        peringatan.append(f"{sumber} '{salinan}' identik dengan '{asli}' di semua baris; dibuang.")
        df = _tolak(df, m, f"salinan dari {asli} (kesalahan scraping)", ditolak)

    # 3. harga 0
    n_nol = int((df["harga"] == 0).sum())
    df = df[df["harga"] != 0].copy()

    # 4a. satuan per butir
    for k, ambang in AMBANG_PER_BUTIR.items():
        m = (df["komoditas_mentah"] == k) & (df["harga"] < ambang)
        df = _tolak(df, m, "satuan per butir, bukan per kg", ditolak)

    # 4b. batas wajar
    lo = df["komoditas_mentah"].map(lambda k: KOMODITAS[k][1])
    hi = df["komoditas_mentah"].map(lambda k: KOMODITAS[k][2])
    df = _tolak(df, (df["harga"] < lo) | (df["harga"] > hi), "di luar batas wajar", ditolak)

    # 5. menyimpang dari median pasar pada hari, komoditas, dan sumber yang sama
    g = df.groupby(["tanggal", "komoditas_mentah", "sumber"])["harga"]
    med = g.transform("median")
    jml = g.transform("size")
    simpang = (jml >= min_pasar) & ((df["harga"] - med).abs() / med > ambang_menyimpang)
    df = _tolak(df, simpang, f"menyimpang > {ambang_menyimpang:.0%} dari median pasar", ditolak)

    df["komoditas"] = df["komoditas_mentah"].map(lambda k: KOMODITAS[k][0])
    bersih = df.sort_values(["tanggal", "kecamatan", "nama_pasar", "komoditas"])[KOLOM].reset_index(drop=True)
    dt = pd.concat(ditolak) if ditolak else pd.DataFrame(columns=KOLOM + ["komoditas_mentah", "alasan"])
    dt = dt.drop(columns="komoditas_mentah", errors="ignore")
    return HasilBersih(bersih=bersih, ditolak=dt, n_mentah=n_mentah, n_nol=n_nol, peringatan=peringatan)


# ---------------------------------------------------------------------------
# Penggabungan ke master tanpa duplikat
# ---------------------------------------------------------------------------

def _kunci_normal(df: pd.DataFrame) -> pd.Series:
    """Kunci pembanding: tanggal | kecamatan | pasar | komoditas | sumber (spasi tepi dibuang, huruf kecil)."""
    bagian = [df["tanggal"].astype(str).str.strip()]
    for c in ["kecamatan", "nama_pasar", "komoditas", "sumber"]:
        bagian.append(df[c].astype(str).str.strip().str.lower())
    return bagian[0].str.cat(bagian[1:], sep="|")


def gabung_ke_master(master: pd.DataFrame, baru: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Gabungkan baris mentah `baru` ke `master` (keduanya 6 kolom mentah) tanpa menggandakan baris.

    Satu kunci (tanggal, kecamatan, pasar, komoditas, sumber) hanya punya satu baris:
      - kunci belum ada di master          -> ditambahkan
      - master berharga 0, baru berharga > 0 -> harga master diisi (sumber baru mengunggah harga hari itu)
      - selain itu                         -> master dibiarkan (revisi harga lama diabaikan, sama dengan impor database)
    Hasil diurutkan per kunci seperti master, sehingga perubahan di git hanya berupa baris baru.
    """
    for nama, d in (("master", master), ("baru", baru)):
        if list(d.columns) != KOLOM:
            raise ValueError(f"Header {nama} tidak sesuai. Diharapkan {KOLOM}, didapat {list(d.columns)}")
    baru = baru.copy()
    baru["harga"] = baru["harga"].astype("int64")
    kb = _kunci_normal(baru)
    baru = baru[~kb.duplicated(keep="last")]          # di dalam tarikan yang sama: ambil yang terakhir
    kb = _kunci_normal(baru)

    km = _kunci_normal(master)
    posisi = pd.Series(range(len(master)), index=km.values)
    harga_master = pd.Series(master["harga"].values, index=km.values)

    ada = kb.isin(posisi.index).values
    tambah = baru[~ada]
    lama = baru[ada]
    k_lama = kb[ada].values
    h_lama = harga_master.loc[k_lama].values
    isi = (h_lama == 0) & (lama["harga"].values > 0)
    revisi = (h_lama > 0) & (lama["harga"].values > 0) & (h_lama != lama["harga"].values)

    hasil = master.copy()
    if isi.any():
        idx = posisi.loc[k_lama[isi]].values
        hasil.iloc[idx, hasil.columns.get_loc("harga")] = lama["harga"].values[isi]
    if len(tambah):
        hasil = pd.concat([hasil, tambah[KOLOM]], ignore_index=True)
        hasil = hasil.sort_values(KUNCI, kind="stable").reset_index(drop=True)

    info = {"ditambahkan": int(len(tambah)), "diisi_dari_0": int(isi.sum()),
            "revisi_diabaikan": int(revisi.sum()), "sudah_ada": int(len(lama) - isi.sum())}
    return hasil, info