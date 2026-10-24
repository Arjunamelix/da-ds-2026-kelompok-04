import numpy as np
import pandas as pd

from app import evaluasi, fitur, model, status


def _siap(df, h=7):
    d = fitur.deret_harian(df)
    x, y, asli = fitur.bangun(d, h)
    ok = x.notna().all(axis=1) & y.notna()
    return x[ok], y[ok], asli[ok], d["harga"][ok]


def test_walk_forward_none_bila_data_sedikit():
    from conftest import buat_df
    xb, yb, ab, hb = _siap(buat_df(60))
    assert evaluasi.walk_forward(xb, yb, ab, hb, 7) is None


def test_walk_forward_tanpa_kebocoran(df_satu_deret, monkeypatch):
    """Tiap model lipatan hanya boleh dilatih dengan baris yang labelnya (t+h) sudah diketahui sebelum lipatan."""
    xb, yb, ab, hb = _siap(df_satu_deret, 7)
    tercatat = []
    asli_latih = model.latih

    def spy(x, y):
        tercatat.append(x.index.max())
        return asli_latih(x, y)

    monkeypatch.setattr(model, "latih", spy)
    hasil = evaluasi.walk_forward(xb, yb, ab, hb, 7)
    assert hasil is not None and len(tercatat) == 3
    n_uji = min(90, int(len(xb) * 0.3))
    awal_uji = xb.index[len(xb) - n_uji]
    # latih lipatan pertama maksimal s.d. awal_uji - 7 hari
    assert tercatat[0] <= awal_uji - pd.Timedelta(7, unit="D")
    assert tercatat == sorted(tercatat)  # jendela latih bertambah (expanding)


def test_metrik_dan_baseline():
    h = np.array([100.0, 100.0])
    m = evaluasi.metrik(h, np.array([0.0, 0.0]), np.array([np.log(1.1), np.log(0.9)]))
    assert np.isclose(m["mae"], 10.0)
    assert np.isclose(m["rmse"], 10.0)
    assert m["mape"] > 0


def test_bandingkan_model_sempurna_mengalahkan_baseline():
    rng = np.random.default_rng(1)
    aktual = rng.normal(0, 0.05, 50)
    hu = evaluasi.HasilUji(np.full(50, 100.0), aktual.copy(), aktual, np.zeros(50))
    b = evaluasi.bandingkan(hu)
    assert b["mengalahkan_baseline"] is True
    assert b["model"]["mae"] < 1e-9 < b["baseline"]["mae"]


def test_ambang_dan_kelas():
    v = np.concatenate([np.random.default_rng(0).normal(0, 3, 500)])
    a = status.hitung_ambang(v)
    assert a is not None and a.waspada_pct >= 2.0 and a.lonjakan_pct > a.waspada_pct
    assert status.kelas(0.0, a) == "Normal"
    assert status.kelas(-50.0, a) == "Normal"  # penurunan bukan lonjakan
    assert status.kelas(a.waspada_pct + 0.01, a) == "Waspada"
    assert status.kelas(a.lonjakan_pct + 0.01, a) == "Lonjakan"
    assert status.hitung_ambang(np.array([1.0, 2.0])) is None


def test_evaluasi_berisiko():
    a = status.Ambang(waspada_pct=5, lonjakan_pct=10)
    pred = np.array([6, 6, 0, 0, 12.0])
    akt = np.array([7, 0, 8, 0, 11.0])
    e = status.evaluasi_berisiko(pred, akt, a)
    assert (e["tp"], e["fp"], e["fn"]) == (2, 1, 1)
    assert np.isclose(e["recall"], 2 / 3) and np.isclose(e["presisi"], 2 / 3)
    kosong = status.evaluasi_berisiko(np.zeros(3), np.zeros(3), a)
    assert kosong["recall"] is None and kosong["presisi"] is None