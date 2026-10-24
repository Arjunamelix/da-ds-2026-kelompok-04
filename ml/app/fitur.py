"""Pembangunan deret harian dan fitur (Project.md 6.4).

Target: log(harga[t+h] / harga[t]) untuk h = 7 dan 14 hari.
Fitur pada hari t hanya memakai data sampai hari t (tanpa kebocoran masa depan), kecuali fitur
kalender untuk tanggal target t+h yang memang diketahui sebelumnya.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, kalender

LAG_RETURN = (1, 3, 7, 14, 28)


def deret_harian(g: pd.DataFrame) -> pd.DataFrame:
    """Ubah baris harga (tanggal, harga, interpolasi) satu deret menjadi deret harian kalender.

    Hari tanpa baris (akhir pekan, libur) diisi interpolasi linear hanya untuk membangun fitur,
    maksimal CELAH_MAKS hari. Kolom `asli` menandai hari yang benar-benar punya data asli.
    """
    g = g.sort_values("tanggal").drop_duplicates("tanggal", keep="last")
    s = g.set_index("tanggal")["harga"].astype(float)
    idx = pd.date_range(s.index.min(), s.index.max(), freq="D")
    penuh = s.reindex(idx).interpolate(method="time", limit=config.CELAH_MAKS, limit_area="inside")
    asli = pd.Series(False, index=idx)
    tanggal_asli = g.loc[g["interpolasi"] == 0, "tanggal"]
    asli.loc[tanggal_asli.values] = True
    return pd.DataFrame({"harga": penuh, "asli": asli})


def fitur_dasar(d: pd.DataFrame) -> pd.DataFrame:
    """Fitur yang tidak bergantung pada horizon."""
    lp = np.log(d["harga"])
    x = pd.DataFrame(index=d.index)
    for k in LAG_RETURN:
        x[f"ret_{k}"] = lp - lp.shift(k)
    x["rasio_ma30"] = lp - np.log(d["harga"].rolling(30, min_periods=20).mean())
    x["rasio_ma90"] = lp - np.log(d["harga"].rolling(90, min_periods=45).mean())
    x["vol14"] = lp.diff().rolling(14, min_periods=10).std()
    x["hb_menjelang"] = kalender.menjelang(d.index, 14)
    return x


def bangun(d: pd.DataFrame, h: int) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Matriks fitur X untuk semua hari, target y (NaN untuk h hari terakhir), dan penanda target asli.

    Mengembalikan (X, y, target_asli). `target_asli` benar bila hari t dan t+h keduanya data asli
    (dipakai agar metrik evaluasi tidak dihitung dari nilai interpolasi).
    """
    x = fitur_dasar(d)
    tgt = d.index + pd.Timedelta(h, unit="D")
    x["hb_target"] = (kalender.jarak_terdekat(pd.DatetimeIndex(tgt)) <= 3).astype(float)
    bulan = pd.DatetimeIndex(tgt).month.values
    x["bulan_sin"] = np.sin(2 * np.pi * bulan / 12)
    x["bulan_cos"] = np.cos(2 * np.pi * bulan / 12)

    lp = np.log(d["harga"])
    y = lp.shift(-h) - lp
    asli = d["asli"] & d["asli"].shift(-h, fill_value=False)
    return x, y, asli


def perubahan_pct(d: pd.DataFrame, h: int = 7) -> pd.Series:
    """Perubahan persen harga t -> t+h pada pasangan hari yang keduanya data asli."""
    p = d["harga"]
    pct = (p.shift(-h) / p - 1.0) * 100.0
    asli = d["asli"] & d["asli"].shift(-h, fill_value=False)
    return pct[asli].dropna()