"""Kalender hari besar sebagai input model (Project.md 1.2: dipakai di belakang layar).

Tanggal memakai ketetapan pemerintah (SKB 3 Menteri dan sidang isbat Kemenag), disepakati di S1.
Isi tiap tahun: tahun baru, Imlek, awal Ramadan, Idulfitri (2 hari), Iduladha, Natal.
Koreksi S1: awal Ramadan 2024 = 12 Maret (sebelumnya 11 Maret, versi Muhammadiyah).
Tanggal 2027 masih perkiraan; perbarui setelah SKB 2027 terbit.
"""
import numpy as np
import pandas as pd

HARI_BESAR = pd.to_datetime([
    # 2024
    "2024-01-01", "2024-02-10", "2024-03-12", "2024-04-10", "2024-04-11", "2024-06-17", "2024-12-25",
    # 2025
    "2025-01-01", "2025-01-29", "2025-03-01", "2025-03-31", "2025-04-01", "2025-06-06", "2025-12-25",
    # 2026
    "2026-01-01", "2026-02-17", "2026-02-19", "2026-03-20", "2026-03-21", "2026-05-27", "2026-12-25",
    # 2027
    "2027-01-01", "2027-02-06", "2027-02-08", "2027-03-10", "2027-03-11", "2027-05-17", "2027-12-25",
]).sort_values()


# Periode Ramadan sampai Idulfitri (ketetapan pemerintah), untuk fitur musim permintaan tinggi.
RAMADAN = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in [
    ("2024-03-12", "2024-04-10"),
    ("2025-03-01", "2025-03-31"),
    ("2026-02-19", "2026-03-21"),
    ("2027-02-08", "2027-03-10"),   # perkiraan
]]


def dalam_ramadan(tanggal: pd.DatetimeIndex, sebelum: int = 7) -> np.ndarray:
    """1 bila tanggal berada di periode Ramadan sampai Idulfitri, termasuk `sebelum` hari menjelang awal Ramadan."""
    t = pd.DatetimeIndex(tanggal)
    hasil = np.zeros(len(t))
    for a, b in RAMADAN:
        hasil[(t >= a - pd.Timedelta(days=sebelum)) & (t <= b)] = 1.0
    return hasil


def hari_ke_berikutnya(tanggal: pd.DatetimeIndex, batas: int = 60) -> np.ndarray:
    """Jumlah hari dari tiap tanggal ke hari besar berikutnya (tidak termasuk hari itu), dibatasi `batas`."""
    t = tanggal.values.astype("datetime64[D]").astype(np.int64)
    h = HARI_BESAR.values.astype("datetime64[D]").astype(np.int64)
    selisih = (h[None, :] - t[:, None]).astype(float)
    selisih[selisih <= 0] = np.inf
    return np.minimum(selisih.min(axis=1), batas)


def jarak_terdekat(tanggal: pd.DatetimeIndex) -> np.ndarray:
    """Jarak (hari, mutlak) tiap tanggal ke hari besar terdekat."""
    t = tanggal.values.astype("datetime64[D]").astype(np.int64)
    h = HARI_BESAR.values.astype("datetime64[D]").astype(np.int64)
    return np.abs(t[:, None] - h[None, :]).min(axis=1)


def menjelang(tanggal: pd.DatetimeIndex, dalam_hari: int = 14) -> np.ndarray:
    """1 bila ada hari besar dalam (t, t + dalam_hari]."""
    t = tanggal.values.astype("datetime64[D]").astype(np.int64)
    h = HARI_BESAR.values.astype("datetime64[D]").astype(np.int64)
    selisih = h[None, :] - t[:, None]
    return ((selisih > 0) & (selisih <= dalam_hari)).any(axis=1).astype(float)