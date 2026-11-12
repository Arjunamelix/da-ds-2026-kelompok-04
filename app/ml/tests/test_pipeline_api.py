import pandas as pd
from fastapi.testclient import TestClient

from app import db, main, pipeline
from conftest import buat_df


def _df_dua_deret():
    panjang = buat_df(260, seed=1)
    pendek = buat_df(30, seed=2, kunci=("Medan Barat", "Pasar B", "beras_medium", "DEV"))
    return pd.concat([panjang, pendek], ignore_index=True)


def test_jalankan_menghasilkan_struktur_utuh():
    out = pipeline.jalankan(_df_dua_deret(), versi_data=5)
    # deret pendek dilewati dengan alasan, deret panjang dimodelkan untuk 2 horizon
    assert {d["nama_pasar"] for d in out["dilewati"]} == {"Pasar B"}
    assert "belum cukup" in out["dilewati"][0]["alasan"]
    assert sorted(p["horizon"] for p in out["prediksi"]) == [7, 14]
    assert sorted(e["horizon"] for e in out["evaluasi"]) == [7, 14]
    for p in out["prediksi"]:
        assert p["batas_bawah"] <= p["harga_prediksi"] <= p["batas_atas"]
        assert p["harga_prediksi"] > 0 and p["versi_data"] == 5
    for e in out["evaluasi"]:
        assert e["n_uji"] >= 20 and e["mae_baseline"] > 0
    assert len(out["status"]) == 1 and out["status"][0]["status"] in {"Normal", "Waspada", "Lonjakan"}
    assert out["evaluasi_status"][0]["komoditas"] == "beras_medium"


def test_data_baru_mengubah_prediksi():
    """Inti demo: menambah data mengubah hasil prediksi (Project.md 6.3)."""
    df = buat_df(260, seed=3)
    a = pipeline.jalankan(df, 1)["prediksi"]
    tambahan = df.tail(1).copy()
    tambahan["tanggal"] = tambahan["tanggal"] + pd.Timedelta(1, unit="D")
    tambahan["harga"] = int(tambahan["harga"].iloc[0] * 1.3)
    b = pipeline.jalankan(pd.concat([df, tambahan], ignore_index=True), 2)["prediksi"]
    p7a = next(p for p in a if p["horizon"] == 7)["harga_prediksi"]
    p7b = next(p for p in b if p["horizon"] == 7)["harga_prediksi"]
    assert p7a != p7b
    assert next(p for p in b if p["horizon"] == 7)["tanggal_dasar"] > next(p for p in a if p["horizon"] == 7)["tanggal_dasar"]


def test_api_health_dan_retrain_asinkron(monkeypatch):
    catatan = {"jalan": 0}

    def palsu_putaran():
        catatan["jalan"] += 1
        main._berjalan = False

    monkeypatch.setattr(main, "_putaran", palsu_putaran)
    monkeypatch.setattr(main, "_pulihkan_saat_start", lambda: None)
    main._berjalan = False
    with TestClient(main.app) as c:
        assert c.get("/health").json()["status"] == "ok"
        r = c.post("/retrain", json={"versi_data": 3})
        assert r.status_code == 202 and r.json()["status"] == "dimulai"
        assert catatan["jalan"] == 1  # tugas latar belakang sudah dijalankan oleh TestClient
        main._berjalan = True
        r2 = c.post("/retrain", json={})
        assert r2.status_code == 202 and r2.json()["status"] == "sudah_berjalan"
    main._berjalan = False


def test_putaran_mengulang_bila_versi_berubah(monkeypatch):
    versi = iter([1, 2, 2, 2])  # baca awal=1; setelah latih berubah jadi 2 -> ulang; lalu stabil
    meta = []
    monkeypatch.setattr(db, "engine", lambda: object())
    monkeypatch.setattr(db, "versi_data", lambda e: next(versi))
    monkeypatch.setattr(db, "set_meta", lambda e, **kv: meta.append(kv))
    monkeypatch.setattr(db, "baca_harga", lambda e: pd.DataFrame())
    monkeypatch.setattr(pipeline, "jalankan", lambda df, v: {"v": v})
    ditulis = []
    monkeypatch.setattr(db, "tulis_hasil", lambda e, h, v: ditulis.append(v))
    main._berjalan = True
    main._putaran()
    assert ditulis == [1, 2]
    assert meta[-1]["status_hitung"] == "idle" and main._berjalan is False