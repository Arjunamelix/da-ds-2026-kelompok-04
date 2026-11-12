"""Status harga Normal / Waspada / Lonjakan dan evaluasinya (Project.md 6.4).

Definisi (usulan, ambang final menunggu data terkumpul — Project.md 2.2 no. 6):
- Ambang dihitung PER KOMODITAS dari sebaran perubahan harga 7 hari historis (gabungan semua deret
  komoditas itu): Waspada = persentil 80, Lonjakan = persentil 95 (dapat diubah lewat env), dengan batas bawah
  Waspada 2% agar komoditas yang stabil tidak diberi status karena gerakan sepele.
- Hanya KENAIKAN harga yang berstatus; penurunan dianggap Normal.
- Status yang ditampilkan = kelas dari perubahan 7 hari yang DIPREDIKSI model.
- Evaluasi: kelas prediksi vs kelas sebenarnya pada hari uji walk-forward; "berisiko" = Waspada + Lonjakan.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config

NORMAL, WASPADA, LONJAKAN = "Normal", "Waspada", "Lonjakan"


@dataclass
class Ambang:
    waspada_pct: float
    lonjakan_pct: float


def hitung_ambang(perubahan_pct: np.ndarray) -> Ambang | None:
    """Ambang dari kumpulan perubahan 7 hari (persen). None bila data kosong."""
    v = np.asarray(perubahan_pct, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) < 30:
        return None
    w = max(float(np.percentile(v, config.PERSENTIL_WASPADA)), config.AMBANG_WASPADA_MIN_PCT)
    lj = float(np.percentile(v, config.PERSENTIL_LONJAKAN))
    if lj <= w:
        lj = w * 1.5
    return Ambang(waspada_pct=w, lonjakan_pct=lj)


def kelas(pct: float | np.ndarray, a: Ambang):
    """Kelas satu nilai (str) atau array (array str)."""
    p = np.asarray(pct, dtype=float)
    out = np.where(p >= a.lonjakan_pct, LONJAKAN, np.where(p >= a.waspada_pct, WASPADA, NORMAL))
    return str(out) if out.ndim == 0 else out


def evaluasi_berisiko(pred_pct: np.ndarray, aktual_pct: np.ndarray, a: Ambang) -> dict:
    """Recall dan presisi kelas berisiko. Nilai None bila penyebutnya nol."""
    pr = kelas(pred_pct, a) != NORMAL
    ak = kelas(aktual_pct, a) != NORMAL
    tp = int(np.sum(pr & ak))
    fn = int(np.sum(~pr & ak))
    fp = int(np.sum(pr & ~ak))
    return {
        "n_uji": int(len(ak)),
        "n_berisiko": int(ak.sum()),
        "tp": tp, "fn": fn, "fp": fp,
        "recall": tp / (tp + fn) if (tp + fn) else None,
        "presisi": tp / (tp + fp) if (tp + fp) else None,
    }