"""Model gabungan (S3): semua algoritma bisa dilatih dan memprediksi; praproses tanpa kebocoran; penyusutan."""
import numpy as np
import pandas as pd
import pytest

from app import fitur_global as fg, model_global as mg, validasi_global as vg
from test_fitur_global import data_pasar


@pytest.fixture(scope="module")
def tabel():
    seri, _ = fg.bangun_deret(fg.agregat_harian(data_pasar(n_hari=700)), min_hari=90)
    kode = fg.kode_komoditas(["cabai_merah", "gula_pasir"])
    return fg.tabel_fitur(seri, 7, kode)


@pytest.mark.parametrize("nama", mg.ALGORITMA)
def test_semua_algoritma_latih_dan_prediksi(tabel, nama):
    if nama == "lightgbm":
        pytest.importorskip("lightgbm")     # paket notebook (pip install lightgbm); masuk requirements aplikasi di S6
    kecil = {"random_forest": {"n_estimators": 20}, "hist_gb": {"max_iter": 30}, "lightgbm": {"n_estimators": 30}}.get(nama)
    m = mg.buat_model(nama, kecil, fg.FITUR_TERPILIH).fit(tabel[fg.FITUR_TERPILIH], tabel["y"])
    p = m.predict(tabel[fg.FITUR_TERPILIH])
    assert p.shape == (len(tabel),) and np.isfinite(p).all()


def test_praproses_ridge_dari_data_latih_saja(tabel):
    """Statistik imputasi dan standardisasi berasal dari data yang di-fit, bukan dari data yang diprediksi."""
    K = fg.FITUR_TERPILIH
    a, b = tabel.iloc[: len(tabel) // 2], tabel.iloc[len(tabel) // 2:]
    m = mg.buat_model("ridge", None, K).fit(a[K], a["y"])
    skala = m.named_steps["pra"].named_transformers_["num"].named_steps["standardscaler"]
    imput = m.named_steps["pra"].named_transformers_["num"].named_steps["simpleimputer"]
    num = [c for c in K if c not in fg.KATEGORI]
    assert np.allclose(imput.statistics_, a[num].median().values, equal_nan=True)
    m.predict(b[K])                                  # prediksi tidak mengubah statistik
    assert np.allclose(imput.statistics_, a[num].median().values, equal_nan=True) and skala.n_samples_seen_ is not None


def test_susut():
    p = np.array([-0.05, -0.01, 0.0, 0.004, 0.03])
    assert np.allclose(mg.susut(p, 0.01), [-0.04, 0.0, 0.0, 0.0, 0.02])
    assert np.allclose(mg.susut(p, 0.0), p)


def test_lipatan_tanpa_tumpang_tindih(tabel):
    for i, L, V in vg.potong_lipatan(tabel, 7):
        if len(V):
            assert (L["t"] + pd.Timedelta(days=7)).max() < V["t"].min()


def test_per_kelompok_dan_skor(tabel):
    oof = vg.prediksi_lipatan(tabel, 7, "ridge", None, fg.FITUR_TERPILIH, per_kelompok=True)
    assert oof["pred"].notna().all() and set(oof["kelompok"]) <= set(vg.KELOMPOK)
    naif = oof.assign(pred=0.0)
    assert vg.skor(naif) == pytest.approx(1.0)