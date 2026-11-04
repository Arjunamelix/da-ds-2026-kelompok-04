"""Alur pelatihan ulang: baca tabel harga -> fitur -> baseline dan boosting -> evaluasi -> tulis hasil.

`proses_deret` murni (tanpa database) supaya mudah diuji.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config, evaluasi, fitur, model, status

log = logging.getLogger("ml.pipeline")

KUNCI = ("kecamatan", "nama_pasar", "komoditas", "sumber")


@dataclass
class HasilDeret:
    prediksi: list[dict] = field(default_factory=list)      # satu per horizon
    evaluasi: list[dict] = field(default_factory=list)      # satu per horizon
    status: dict | None = None
    uji7: tuple | None = None                               # (pred_pct, aktual_pct) hari uji horizon 7
    alasan_lewat: str | None = None


def proses_deret(d: pd.DataFrame, ambang: status.Ambang | None) -> HasilDeret:
    """Latih dan evaluasi satu deret harian `d` (kolom harga, asli) untuk semua horizon."""
    hasil = HasilDeret()
    tanggal_dasar = d.index[-1]
    harga_dasar = float(d["harga"].iloc[-1])
    if not np.isfinite(harga_dasar):
        hasil.alasan_lewat = "harga terakhir tidak terbaca"
        return hasil

    for h in config.HORIZON:
        x, y, asli = fitur.bangun(d, h)
        lengkap = x.notna().all(axis=1)
        berlabel = lengkap & y.notna()
        if berlabel.sum() < config.LATIH_MIN + config.UJI_MIN:
            hasil.alasan_lewat = f"baris berlabel terlalu sedikit untuk horizon {h} hari ({int(berlabel.sum())})"
            return hasil
        xb, yb, ab, hb = x[berlabel], y[berlabel], asli[berlabel], d["harga"][berlabel]

        uji = evaluasi.walk_forward(xb, yb, ab, hb, h)
        if uji is None:
            hasil.alasan_lewat = f"data terlalu sedikit untuk evaluasi walk-forward horizon {h} hari"
            return hasil
        banding = evaluasi.bandingkan(uji)

        # Model akhir dilatih dengan semua baris berlabel, lalu memprediksi dari hari terakhir.
        m = model.latih(xb, yb)
        if not lengkap.iloc[-1]:
            hasil.alasan_lewat = "fitur hari terakhir tidak lengkap"
            return hasil
        pred_log = float(model.prediksi_log(m, x.iloc[[-1]])[0])
        q_lo, q_hi = np.quantile(uji.sisa_log, [config.KUANTIL_BAWAH, config.KUANTIL_ATAS])
        pred = harga_dasar * np.exp(pred_log)
        lo = min(harga_dasar * np.exp(pred_log + q_lo), pred)
        hi = max(harga_dasar * np.exp(pred_log + q_hi), pred)

        hasil.prediksi.append({
            "horizon": h, "tanggal_dasar": tanggal_dasar.date(), "harga_dasar": harga_dasar,
            "harga_prediksi": float(pred), "batas_bawah": float(lo), "batas_atas": float(hi),
        })
        hasil.evaluasi.append({
            "horizon": h, "n_uji": banding["n_uji"],
            "mae_model": banding["model"]["mae"], "rmse_model": banding["model"]["rmse"], "mape_model": banding["model"]["mape"],
            "mae_baseline": banding["baseline"]["mae"], "rmse_baseline": banding["baseline"]["rmse"],
            "mape_baseline": banding["baseline"]["mape"],
            "mengalahkan_baseline": banding["mengalahkan_baseline"],
        })

        if h == 7:
            pct_pred = (pred / harga_dasar - 1.0) * 100.0
            if ambang is not None:
                hasil.status = {
                    "status": status.kelas(pct_pred, ambang), "perubahan_prediksi_pct": float(pct_pred),
                    "ambang_waspada_pct": ambang.waspada_pct, "ambang_lonjakan_pct": ambang.lonjakan_pct,
                    "tanggal_dasar": tanggal_dasar.date(),
                }
            hasil.uji7 = ((np.exp(uji.pred_log) - 1.0) * 100.0, (np.exp(uji.aktual_log) - 1.0) * 100.0)
    return hasil


def _kerja(args):
    """Satu unit kerja untuk proses pekerja: (kunci, deret, ambang) -> (kunci, hasil, galat)."""
    kunci, d, ambang = args
    try:
        return kunci, proses_deret(d, ambang), None
    except Exception as e:  # satu deret bermasalah tidak boleh menggagalkan seluruh pelatihan
        log.exception("deret %s gagal diproses", kunci)
        return kunci, None, f"{type(e).__name__}: {e}"


def _proses_semua(tugas: list[tuple]) -> list[tuple]:
    """Proses semua deret; paralel antar proses bila ML_PEKERJA > 1 (pelatihan ulang jadi jauh lebih cepat)."""
    if config.PEKERJA <= 1 or len(tugas) <= 1:
        return [_kerja(t) for t in tugas]
    ctx = multiprocessing.get_context("spawn")  # aman dipanggil dari thread latar belakang FastAPI
    with ProcessPoolExecutor(max_workers=config.PEKERJA, mp_context=ctx) as pool:
        return list(pool.map(_kerja, tugas, chunksize=2))


def jalankan(df: pd.DataFrame, versi_data: int) -> dict:
    """Latih semua deret pada `df` (tabel harga) dan kembalikan baris hasil siap tulis ke database."""
    deret: dict[tuple, pd.DataFrame] = {}
    dilewati: list[dict] = []
    for kunci, g in df.groupby(list(KUNCI), sort=True):
        n_asli = int((g["interpolasi"] == 0).sum())
        if n_asli < config.MIN_HARI:
            dilewati.append(dict(zip(KUNCI, kunci)) | {"alasan": f"data belum cukup (butuh minimal {config.MIN_HARI} hari data asli)", "n_hari": n_asli, "versi_data": versi_data})
            continue
        deret[kunci] = fitur.deret_harian(g)

    # Ambang status per komoditas dari perubahan 7 hari gabungan semua deret komoditas itu.
    kumpul: dict[str, list[np.ndarray]] = defaultdict(list)
    for kunci, d in deret.items():
        kumpul[kunci[2]].append(fitur.perubahan_pct(d, 7).values)
    ambang = {k: status.hitung_ambang(np.concatenate(v)) for k, v in kumpul.items() if v}

    out = {"prediksi": [], "status": [], "evaluasi": [], "evaluasi_status": [], "dilewati": dilewati}
    uji_status: dict[str, list[tuple]] = defaultdict(list)

    tugas = [(kunci, d, ambang.get(kunci[2])) for kunci, d in deret.items()]
    for kunci, r, galat in _proses_semua(tugas):
        kec, pasar, kom, sumber = kunci
        d = deret[kunci]
        base = {"kecamatan": kec, "nama_pasar": pasar, "komoditas": kom, "sumber": sumber, "versi_data": versi_data}
        if galat is not None:
            out["dilewati"].append(base | {"alasan": "galat saat pemrosesan: " + galat[:200], "n_hari": int(d["asli"].sum())})
            continue
        if r.alasan_lewat:
            out["dilewati"].append(base | {"alasan": r.alasan_lewat, "n_hari": int(d["asli"].sum())})
            continue
        out["prediksi"] += [base | p for p in r.prediksi]
        out["evaluasi"] += [base | e for e in r.evaluasi]
        if r.status:
            out["status"].append(base | r.status)
        if r.uji7 is not None:
            uji_status[kom].append(r.uji7)

    for kom, daftar in uji_status.items():
        a = ambang.get(kom)
        if a is None:
            continue
        pr = np.concatenate([p for p, _ in daftar])
        ak = np.concatenate([q for _, q in daftar])
        ev = status.evaluasi_berisiko(pr, ak, a)
        out["evaluasi_status"].append({
            "komoditas": kom, "n_uji": ev["n_uji"], "n_berisiko": ev["n_berisiko"],
            "recall_berisiko": ev["recall"], "presisi_berisiko": ev["presisi"],
            "ambang_waspada_pct": a.waspada_pct, "ambang_lonjakan_pct": a.lonjakan_pct, "versi_data": versi_data,
        })
    log.info("selesai: %d prediksi, %d status, %d dilewati", len(out["prediksi"]), len(out["status"]), len(out["dilewati"]))
    return out