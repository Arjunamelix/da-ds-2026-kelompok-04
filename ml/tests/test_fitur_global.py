"""Fitur model gabungan (S2): agregasi sama dengan view harga_agregat, tanpa kebocoran masa depan."""
import numpy as np
import pandas as pd
import pytest

from app import fitur_global as fg, kalender


def data_pasar(n_hari=320, seed=1):
    """Data per pasar sintetis: 4 pasar di 2 kecamatan, 2 komoditas, hanya hari kerja."""
    rng = np.random.default_rng(seed)
    tgl = pd.bdate_range("2025-01-06", periods=n_hari)
    baris = []
    for kom, dasar in (("cabai_merah", 50000), ("gula_pasir", 18000)):
        acak = np.cumsum(rng.normal(0, 0.02 if kom == "cabai_merah" else 0.002, len(tgl)))
        for kec, pasar in (("Medan Area", "Pasar A"), ("Medan Area", "Pasar B"), ("Medan Kota", "Pasar C"), ("Medan Kota", "Pasar D")):
            harga = np.round(dasar * np.exp(acak + rng.normal(0, 0.01, len(tgl))), -2)
            baris.append(pd.DataFrame({"tanggal": tgl, "kecamatan": kec, "nama_pasar": pasar, "komoditas": kom,
                                       "harga": harga, "sumber": "SIMPANG"}))
    df = pd.concat(baris, ignore_index=True)
    return df.drop(df.sample(frac=0.05, random_state=seed).index)      # beberapa hari tidak melapor


@pytest.fixture(scope="module")
def seri():
    s, _ = fg.bangun_deret(fg.agregat_harian(data_pasar()), min_hari=90)
    return s


def test_agregat_sama_dengan_view(seri):
    raw = data_pasar()
    ag = fg.agregat_harian(raw)
    t = pd.Timestamp(raw["tanggal"].iloc[100])
    hari = raw[(pd.to_datetime(raw.tanggal) == t) & (raw.komoditas == "cabai_merah")]
    kota = ag[(ag.tanggal == t) & (ag.kecamatan == fg.KOTA) & (ag.komoditas == "cabai_merah")]
    assert kota["harga"].iloc[0] == np.floor(hari["harga"].median() + 0.5)
    assert kota["n_pasar"].iloc[0] == len(hari)
    kec = ag[(ag.tanggal == t) & (ag.kecamatan == "Medan Area") & (ag.komoditas == "cabai_merah")]
    assert kec["harga"].iloc[0] == np.floor(hari[hari.kecamatan == "Medan Area"]["harga"].mean() + 0.5)


def test_kota_butuh_minimal_3_pasar():
    raw = data_pasar()
    raw = raw[raw.nama_pasar.isin(["Pasar A", "Pasar B"])]
    ag = fg.agregat_harian(raw)
    assert (ag.kecamatan == fg.KOTA).sum() == 0


def test_kolom_fitur_lengkap(seri):
    kode = fg.kode_komoditas(["cabai_merah", "gula_pasir"])
    T = fg.tabel_fitur(seri, 7, kode)
    assert set(fg.SEMUA_FITUR) <= set(T.columns)
    assert len(fg.SEMUA_FITUR) == len(set(fg.SEMUA_FITUR))
    assert set(fg.FITUR_TERPILIH) <= set(fg.SEMUA_FITUR) and len(fg.FITUR_TERPILIH) == 13
    assert T["tingkat_kota"].isin([0.0, 1.0]).all() and set(T["komoditas_kode"]) == {0, 1}
    # target hanya dari pasangan hari yang keduanya data asli
    for k, d in seri.items():
        sub = T[T.kunci == k]
        assert d.loc[sub.t, "asli"].all()
        assert d.loc[sub.t + pd.Timedelta(days=7), "asli"].all()


@pytest.mark.parametrize("h", [7, 14])
def test_tanpa_kebocoran_masa_depan(seri, h):
    """Fitur pada hari t harus sama persis bila semua data sesudah t dihapus."""
    kode = fg.kode_komoditas(["cabai_merah", "gula_pasir"])
    penuh = fg.tabel_fitur(seri, h, kode, hanya_target_asli=False)
    rng = np.random.default_rng(0)
    for _ in range(25):
        r = penuh.iloc[rng.integers(len(penuh))]
        potong = {k: d.loc[: r.t] for k, d in seri.items()}
        potong = {k: d for k, d in potong.items() if len(d)}
        sub = fg.tabel_fitur(potong, h, kode, hanya_target_asli=False)
        s = sub[(sub.kunci == r.kunci) & (sub.t == r.t)].iloc[0]
        a = pd.to_numeric(r[fg.SEMUA_FITUR]).astype(float).values
        b = pd.to_numeric(s[fg.SEMUA_FITUR]).astype(float).values
        np.testing.assert_allclose(a, b, rtol=1e-12, atol=1e-12, equal_nan=True)


def test_hari_sejak_berubah_dan_frac():
    idx = pd.bdate_range("2025-01-06", periods=40)
    g = pd.DataFrame({"tanggal": idx, "harga": [100.0] * 20 + [110.0] * 20, "n_pasar": 3, "dispersi": 0.0})
    d = fg.deret_harian(g)
    x = fg.fitur_deret(d)
    assert x.loc[idx[19], "hari_sejak_berubah"] == 120           # belum pernah berubah: dibatasi 120
    assert x.loc[idx[20], "hari_sejak_berubah"] == 0
    assert x.loc[idx[25], "hari_sejak_berubah"] == (idx[25] - idx[20]).days
    assert x.loc[idx[19], "frac_berubah_28"] == 0


def test_kalender_ramadan_dan_hari_besar():
    t = pd.DatetimeIndex(["2024-03-04", "2024-03-05", "2024-03-20", "2024-04-11", "2024-05-01"])
    assert kalender.dalam_ramadan(t, 7).tolist() == [0.0, 1.0, 1.0, 0.0, 0.0]
    assert kalender.hari_ke_berikutnya(pd.DatetimeIndex(["2024-04-09"]), 60)[0] == 1
    assert kalender.hari_ke_berikutnya(pd.DatetimeIndex(["2024-04-10"]), 60)[0] == 1     # hari besar berikutnya 11 Apr