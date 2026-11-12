import numpy as np
import pandas as pd

from app import fitur


def test_deret_harian_mengisi_akhir_pekan_dan_menandai_asli(df_satu_deret):
    d = fitur.deret_harian(df_satu_deret)
    assert d.index.is_monotonic_increasing
    assert d["harga"].notna().all()
    # akhir pekan bukan data asli, hari kerja ya
    sabtu = d.index[d.index.weekday == 5]
    assert not d.loc[sabtu, "asli"].any()
    assert d["asli"].sum() == len(df_satu_deret)


def test_target_selaras_dengan_horizon(df_satu_deret):
    d = fitur.deret_harian(df_satu_deret)
    h = 7
    x, y, asli = fitur.bangun(d, h)
    t = d.index[40]
    esperado = np.log(d["harga"].loc[t + pd.Timedelta(h, unit="D")] / d["harga"].loc[t])
    assert np.isclose(y.loc[t], esperado)
    assert y.iloc[-h:].isna().all()        # h hari terakhir belum punya label
    assert len(x) == len(d)


def test_fitur_tidak_bocor_dari_masa_depan(df_satu_deret):
    """Mengubah harga setelah hari t tidak boleh mengubah fitur hari t."""
    d = fitur.deret_harian(df_satu_deret)
    t = d.index[100]
    x1, _, _ = fitur.bangun(d, 7)
    d2 = d.copy()
    d2.loc[d2.index > t, "harga"] *= 3.0
    x2, _, _ = fitur.bangun(d2, 7)
    pd.testing.assert_series_equal(x1.loc[t], x2.loc[t], check_names=False)


def test_target_asli_hanya_bila_kedua_hari_asli(df_satu_deret):
    d = fitur.deret_harian(df_satu_deret)
    _, _, asli = fitur.bangun(d, 7)
    # Sabtu (bukan data asli) tidak boleh dihitung sebagai hari uji
    assert not asli[d.index.weekday == 5].any()


def test_perubahan_pct(df_satu_deret):
    d = fitur.deret_harian(df_satu_deret)
    p = fitur.perubahan_pct(d, 7)
    assert len(p) > 0 and np.isfinite(p.values).all()


def test_celah_panjang_tidak_diinterpolasi(df_satu_deret):
    df = df_satu_deret.copy()
    df = df[(df["tanggal"] < "2025-03-01") | (df["tanggal"] > "2025-05-01")]  # celah ~2 bulan
    d = fitur.deret_harian(df)
    assert d["harga"].isna().any()