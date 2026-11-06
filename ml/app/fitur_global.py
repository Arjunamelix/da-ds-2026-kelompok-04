"""Fitur untuk model gabungan (satu model untuk semua deret per horizon), disusun di S2.

Masukan: data bersih per pasar (kolom tanggal, kecamatan, nama_pasar, komoditas, harga, sumber), sama dengan
tabel `harga`. Dari situ dibangun deret harian per (wilayah, komoditas, sumber) dengan aturan yang sama dengan
view `harga_agregat`: kecamatan = rata-rata pasar, Kota Medan = median pasar (minimal 3 pasar).

Aturan tanpa kebocoran:
- Fitur pada hari asal t hanya memakai data sampai hari t. Satu-satunya informasi masa depan adalah kalender
  tanggal target t + h (hari besar, bulan), yang memang sudah diketahui sebelumnya.
- Baris hanya dibuat untuk hari asal yang data asli. Hari tanpa data diisi interpolasi linear (paling lama
  `celah` hari) hanya agar jendela bergulir terisi; karena t selalu data asli, interpolasi di jendela tidak
  pernah memakai harga sesudah t. Ini diuji di tests/test_fitur_global.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import kalender

KUNCI = ["kecamatan", "nama_pasar", "komoditas", "sumber"]
KOTA = "KOTA MEDAN"
BERGEJOLAK = ("cabai_merah", "cabai_rawit", "bawang_merah", "daging_ayam_ras", "bawang_putih")

FITUR_GRUP: dict[str, list[str]] = {
    # siapa deretnya
    "identitas": ["komoditas_kode", "bergejolak", "tingkat_kota"],
    # ke mana harga bergerak akhir-akhir ini dan seberapa jauh dari rata-ratanya
    "momentum": ["ret_1", "ret_3", "ret_7", "ret_14", "ret_28", "rasio_ma30", "rasio_ma90", "rasio_ma365"],
    # seberapa sering dan seberapa besar harga berubah (harga bahan pokok "lengket")
    "volatilitas": ["vol14", "vol56", "frac_berubah_28", "hari_sejak_berubah"],
    # kondisi antarpasar dan posisi kecamatan terhadap kota pada hari t
    "pasar_wilayah": ["n_pasar", "dispersi", "selisih_kota", "ret_7_kota"],
    # kalender tanggal target t + h (diketahui sebelumnya)
    "kalender": ["hb_menjelang", "hb_target", "hari_ke_hb", "ramadan_target", "bulan_sin", "bulan_cos"],
}
SEMUA_FITUR = [f for g in FITUR_GRUP.values() for f in g]

# Set fitur final S2 (set "K"): hasil ablation dan permutation importance di notebooks/pemodelan.ipynb bagian S2.
# Kalender dan momentum jangka pendek dikeluarkan karena tidak menurunkan galat di validasi silang.
FITUR_TERPILIH = [
    "komoditas_kode", "bergejolak", "tingkat_kota",
    "ret_3", "ret_14", "rasio_ma30", "rasio_ma365",
    "frac_berubah_28", "hari_sejak_berubah",
    "n_pasar", "dispersi", "selisih_kota", "ret_7_kota",
]
KATEGORI = ["komoditas_kode"]


def _bulat(x):
    return np.floor(x + 0.5)        # pembulatan sama dengan round() PostgreSQL


def agregat_harian(raw: pd.DataFrame, min_pasar_kota: int = 3) -> pd.DataFrame:
    """Harga harian per kecamatan (rata-rata pasar) dan Kota Medan (median pasar), beserta jumlah pasar dan sebarannya."""
    raw = raw.assign(tanggal=pd.to_datetime(raw["tanggal"]))
    cv = lambda v: v.std(ddof=0) / v.mean() if len(v) > 1 else np.nan

    g = raw.groupby(["tanggal", "kecamatan", "komoditas", "sumber"])["harga"]
    kec = g.agg(harga="mean", n_pasar="size", dispersi=cv).reset_index()
    kec["harga"], kec["nama_pasar"], kec["tingkat"] = _bulat(kec["harga"]), "SEMUA", "kecamatan"

    g = raw.groupby(["tanggal", "komoditas", "sumber"])["harga"]
    kota = g.agg(harga="median", n_pasar="size", dispersi=cv).reset_index()
    kota = kota[kota["n_pasar"] >= min_pasar_kota]
    kota["harga"], kota["kecamatan"], kota["nama_pasar"], kota["tingkat"] = _bulat(kota["harga"]), KOTA, "SEMUA", "kota"
    return pd.concat([kec, kota], ignore_index=True)


def deret_harian(g: pd.DataFrame, celah: int = 14) -> pd.DataFrame:
    """Satu deret: indeks harian, harga (interpolasi <= celah hari), penanda data asli, n_pasar dan dispersi hari itu."""
    g = g.sort_values("tanggal").set_index("tanggal")
    idx = pd.date_range(g.index.min(), g.index.max(), freq="D")
    d = pd.DataFrame(index=idx)
    d["harga"] = g["harga"].astype(float).reindex(idx).interpolate(method="time", limit=celah, limit_area="inside")
    d["asli"] = pd.Series(True, index=g.index).reindex(idx, fill_value=False).astype(bool)
    d["n_pasar"] = g["n_pasar"].reindex(idx)
    d["dispersi"] = g["dispersi"].reindex(idx)
    return d


def bangun_deret(agregat: pd.DataFrame, min_hari: int = 90, celah: int = 14) -> tuple[dict, list[dict]]:
    """Semua deret yang punya minimal `min_hari` hari data asli. Mengembalikan (deret, dilewati)."""
    seri, dilewati = {}, []
    for k, g in agregat.groupby(KUNCI):
        if len(g) < min_hari:
            dilewati.append({"kunci": k, "hari_data": len(g)})
            continue
        seri[k] = deret_harian(g, celah)
    return seri, dilewati


def _hari_sejak_berubah(harga_asli: pd.Series, batas: int = 120) -> pd.Series:
    berubah = harga_asli.diff().abs() > 0
    tgl = pd.Series(harga_asli.index, index=harga_asli.index).where(berubah).ffill()
    hari = (harga_asli.index.to_series() - tgl).dt.days
    return hari.fillna(batas).clip(upper=batas)


def fitur_deret(d: pd.DataFrame, kota: pd.DataFrame | None = None) -> pd.DataFrame:
    """Fitur yang tidak bergantung pada horizon untuk setiap hari deret (dipakai pada hari asal yang data asli)."""
    lp = np.log(d["harga"])
    x = pd.DataFrame(index=d.index)
    for k in (1, 3, 7, 14, 28):
        x[f"ret_{k}"] = lp - lp.shift(k)
    for w, mp in ((30, 20), (90, 45), (365, 180)):
        x[f"rasio_ma{w}"] = lp - np.log(d["harga"].rolling(w, min_periods=mp).mean())

    dl = lp.diff()
    x["vol14"] = dl.rolling(14, min_periods=10).std()
    x["vol56"] = dl.rolling(56, min_periods=40).std()
    pa = d.loc[d["asli"], "harga"]                       # hanya hari data asli
    berubah = (pa.diff().abs() > 0).astype(float).where(pa.diff().notna())
    x["frac_berubah_28"] = berubah.rolling("28D", min_periods=5).mean().reindex(d.index)
    x["hari_sejak_berubah"] = _hari_sejak_berubah(pa).reindex(d.index)

    x["n_pasar"] = d["n_pasar"]
    x["dispersi"] = d["dispersi"]
    if kota is None:                                     # deret level kota
        x["selisih_kota"] = 0.0
        x["ret_7_kota"] = x["ret_7"]
    else:
        lk = np.log(kota["harga"]).reindex(d.index)
        x["selisih_kota"] = lp - lk
        x["ret_7_kota"] = lk - np.log(kota["harga"]).shift(7).reindex(d.index)
    return x


def fitur_kalender(t: pd.DatetimeIndex, h: int) -> pd.DataFrame:
    """Fitur kalender yang bergantung pada horizon: dihitung dari hari asal t dan tanggal target t + h."""
    t = pd.DatetimeIndex(t)
    tgt = t + pd.Timedelta(days=h)
    bulan = tgt.month.values
    return pd.DataFrame({
        "hb_menjelang": kalender.menjelang(t, 14),
        "hb_target": (kalender.jarak_terdekat(tgt) <= 3).astype(float),
        "hari_ke_hb": kalender.hari_ke_berikutnya(t, 60),
        "ramadan_target": kalender.dalam_ramadan(tgt, 7),
        "bulan_sin": np.sin(2 * np.pi * bulan / 12),
        "bulan_cos": np.cos(2 * np.pi * bulan / 12),
    }, index=t)


def kode_komoditas(daftar_kode) -> dict[str, int]:
    """Kode bilangan tetap per komoditas (urut abjad), untuk fitur kategori."""
    return {k: i for i, k in enumerate(sorted(daftar_kode))}


def tabel_fitur(seri: dict, horizon: int, kode: dict[str, int], hanya_target_asli: bool = True) -> pd.DataFrame:
    """Satu baris per (deret, hari asal t yang data asli): fitur, target y = ln P[t+h] - ln P[t], dan harga_t.

    Bila `hanya_target_asli`, hanya baris yang hari target-nya juga data asli (untuk latih dan evaluasi).
    Bila False, baris tanpa target ikut (untuk prediksi hari-hari terakhir).
    """
    kota_per = {(k[2], k[3]): d for k, d in seri.items() if k[0] == KOTA}
    keluar = []
    for k, d in seri.items():
        kec, _, kom, sumber = k
        x = fitur_deret(d, None if kec == KOTA else kota_per.get((kom, sumber)))
        lp = np.log(d["harga"])
        y = lp.shift(-horizon) - lp
        asli_t = d["asli"].values
        asli_tgt = d["asli"].shift(-horizon, fill_value=False).values
        pilih = asli_t & (asli_tgt if hanya_target_asli else True)
        x = x[pilih]
        if x.empty:
            continue
        x = pd.concat([x, fitur_kalender(x.index, horizon)], axis=1)
        x["komoditas_kode"] = kode[kom]
        x["bergejolak"] = float(kom in BERGEJOLAK)
        x["tingkat_kota"] = float(kec == KOTA)
        x.insert(0, "t", x.index)
        x.insert(0, "kunci", [k] * len(x))
        x["komoditas"] = kom
        x["h"] = horizon
        x["harga_t"] = d["harga"][pilih].values
        x["y"] = y[pilih].values
        keluar.append(x.reset_index(drop=True))
    return pd.concat(keluar, ignore_index=True)