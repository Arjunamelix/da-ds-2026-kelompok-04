import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def buat_df(n_hari_kerja: int = 220, seed: int = 0, kunci=("Medan Area", "Pasar A", "beras_medium", "DEV"), awal="2025-01-06") -> pd.DataFrame:
    """Tabel harga sintetis untuk satu deret (hanya hari kerja, seperti survei harga)."""
    rng = np.random.default_rng(seed)
    tgl = pd.bdate_range(awal, periods=n_hari_kerja)
    x = np.zeros(len(tgl))
    for i in range(1, len(tgl)):
        x[i] = 0.9 * x[i - 1] + rng.normal(0, 0.01)
    harga = (20000 * np.exp(x)).round(-2)
    kec, pasar, kom, sumber = kunci
    return pd.DataFrame({
        "tanggal": tgl, "kecamatan": kec, "nama_pasar": pasar, "komoditas": kom, "sumber": sumber,
        "harga": harga.astype(int), "interpolasi": 0,
    })


@pytest.fixture
def df_satu_deret():
    return buat_df()