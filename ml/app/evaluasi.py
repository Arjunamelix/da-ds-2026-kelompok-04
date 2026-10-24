"""Evaluasi walk-forward (Project.md 6.4): MAE, RMSE, MAPE model vs baseline naif."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config, model


@dataclass
class HasilUji:
    """Prediksi walk-forward pada hari uji (hanya hari yang target-nya data asli)."""
    harga_t: np.ndarray      # harga pada hari t
    pred_log: np.ndarray     # prediksi model (perubahan log)
    aktual_log: np.ndarray   # perubahan log sebenarnya
    sisa_log: np.ndarray     # aktual - prediksi, dipakai untuk rentang prediksi


def walk_forward(x: pd.DataFrame, y: pd.Series, asli: pd.Series, harga: pd.Series, h: int) -> HasilUji | None:
    """Uji maju: tiap lipatan dilatih hanya dengan baris yang labelnya sudah diketahui sebelum lipatan mulai.

    x, y, asli, harga harus sudah dibersihkan dari NaN dan sejajar indeks tanggalnya.
    Mengembalikan None bila data terlalu sedikit untuk evaluasi yang berarti.
    """
    n = len(x)
    n_uji = min(config.UJI_MAKS, int(n * config.UJI_PORSI))
    if n_uji < config.UJI_MIN:
        return None

    awal_uji = n - n_uji
    potongan = np.array_split(np.arange(awal_uji, n), config.LIPATAN)
    ph, pa, pt, ps = [], [], [], []
    for pos in potongan:
        if len(pos) == 0:
            continue
        t0 = x.index[pos[0]]
        # label baris t baru diketahui pada t+h, jadi latih hanya baris dengan t+h <= t0 (tanpa kebocoran)
        latih_mask = x.index <= (t0 - pd.Timedelta(h, unit="D"))
        if latih_mask.sum() < config.LATIH_MIN:
            return None
        m = model.latih(x[latih_mask], y[latih_mask])
        p = model.prediksi_log(m, x.iloc[pos])
        a = y.iloc[pos].values
        ok = asli.iloc[pos].values
        ph.append(harga.iloc[pos].values[ok])
        pa.append(a[ok])
        pt.append(p[ok])
        ps.append((a - p)[ok])

    if not ph:
        return None
    hasil = HasilUji(np.concatenate(ph), np.concatenate(pt), np.concatenate(pa), np.concatenate(ps))
    if len(hasil.harga_t) < config.UJI_MIN:
        return None
    return hasil


def metrik(harga_t: np.ndarray, pred_log: np.ndarray, aktual_log: np.ndarray) -> dict[str, float]:
    """MAE, RMSE (satuan rupiah) dan MAPE (persen) pada skala harga."""
    aktual = harga_t * np.exp(aktual_log)
    pred = harga_t * np.exp(pred_log)
    galat = pred - aktual
    return {
        "mae": float(np.mean(np.abs(galat))),
        "rmse": float(np.sqrt(np.mean(galat ** 2))),
        "mape": float(np.mean(np.abs(galat) / aktual) * 100.0),
    }


def bandingkan(hasil: HasilUji) -> dict:
    """Metrik model dan baseline pada hari uji yang sama; model dianggap berguna bila MAE-nya lebih kecil."""
    mm = metrik(hasil.harga_t, hasil.pred_log, hasil.aktual_log)
    mb = metrik(hasil.harga_t, model.baseline_log(len(hasil.harga_t)), hasil.aktual_log)
    return {
        "n_uji": int(len(hasil.harga_t)),
        "model": mm,
        "baseline": mb,
        "mengalahkan_baseline": bool(mm["mae"] < mb["mae"]),
    }