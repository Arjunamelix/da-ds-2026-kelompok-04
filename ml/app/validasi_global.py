"""Validasi silang waktu untuk model gabungan (S2–S4).

Lipatan expanding window: model dilatih dengan semua baris yang hari targetnya sebelum awal lipatan,
lalu dinilai pada baris yang hari asal dan hari targetnya berada di dalam lipatan. Data uji (hari asal
mulai 1 Juli 2026) tidak pernah dipakai di sini.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import model_global

LIPATAN = [("2025-07-01", "2025-09-30"), ("2025-10-01", "2025-12-31"),
           ("2026-01-01", "2026-03-31"), ("2026-04-01", "2026-06-30")]
KELOMPOK = ("bergejolak", "stabil")


def mae_rp(harga_t, y, pred) -> float:
    """MAE dalam rupiah dari target dan prediksi skala log."""
    return float(np.abs(harga_t * (np.exp(pred) - np.exp(y))).mean())


def potong_lipatan(T: pd.DataFrame, h: int, lipatan=LIPATAN):
    """Hasilkan (nomor, data latih, data nilai) untuk tiap lipatan."""
    tt = T["t"] + pd.Timedelta(days=h)
    for i, (a, b) in enumerate(lipatan, 1):
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        yield i, T[tt < a], T[(T["t"] >= a) & (tt <= b)]


def prediksi_lipatan(T: pd.DataFrame, h: int, nama: str, param: dict | None, kolom: list[str],
                     per_kelompok: bool = False, seed: int = 42) -> pd.DataFrame:
    """Prediksi out-of-fold untuk semua lipatan: kolom lipatan, kelompok, harga_t, y, pred (indeks = indeks T).

    `per_kelompok=True` melatih model terpisah untuk komoditas bergejolak dan stabil.
    """
    keluar = []
    for i, L, V in potong_lipatan(T, h):
        pred = pd.Series(np.nan, index=V.index)
        grup_l = np.where(L["bergejolak"] == 1, "bergejolak", "stabil")
        grup_v = np.where(V["bergejolak"] == 1, "bergejolak", "stabil")
        bagian = [(KELOMPOK, None)] if not per_kelompok else [((g,), g) for g in KELOMPOK]
        for grup, _ in bagian:
            ml_, mv_ = np.isin(grup_l, grup), np.isin(grup_v, grup)
            m = model_global.buat_model(nama, param, kolom, seed).fit(L.loc[ml_, kolom], L.loc[ml_, "y"])
            pred[V.index[mv_]] = m.predict(V.loc[mv_, kolom])
        keluar.append(pd.DataFrame({"lipatan": i, "kelompok": grup_v, "harga_t": V["harga_t"].values,
                                    "y": V["y"].values, "pred": pred.values}, index=V.index))
    return pd.concat(keluar)


def ringkas(oof: pd.DataFrame, pred_kolom: str = "pred") -> pd.DataFrame:
    """MAE model dan naif per (lipatan, kelompok), beserta rasio terhadap naif."""
    baris = []
    for (i, g), d in oof.groupby(["lipatan", "kelompok"]):
        m = mae_rp(d.harga_t.values, d.y.values, d[pred_kolom].values)
        n = mae_rp(d.harga_t.values, d.y.values, np.zeros(len(d)))
        baris.append({"lipatan": i, "kelompok": g, "MAE": m, "MAE naif": n, "rasio": m / n})
    return pd.DataFrame(baris)


def skor(oof: pd.DataFrame, pred_kolom: str = "pred") -> float:
    """Skor tuning: rata-rata rasio MAE terhadap naif atas lipatan dan kedua kelompok (makin kecil makin baik)."""
    return float(ringkas(oof, pred_kolom)["rasio"].mean())