"""Akses PostgreSQL untuk layanan ML: baca tabel harga, tulis tabel hasil model."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine

from . import config

_engine: Engine | None = None


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(config.database_url(), pool_pre_ping=True, pool_size=3)
    return _engine


def baca_harga(eng: Engine) -> pd.DataFrame:
    """Baca deret yang dimodelkan dari view harga_agregat.

    Bawaan hanya tingkat 'kecamatan' (rata-rata pasar) dan 'kota' (median pasar), karena itu yang ditampilkan
    dashboard; deret per pasar tidak dimodelkan (hemat waktu pelatihan). Ubah lewat ML_TINGKAT.
    """
    tingkat = [t for t in config.TINGKAT if t in ("pasar", "kecamatan", "kota")]
    sql = text(
        "SELECT tanggal, kecamatan, nama_pasar, komoditas, sumber, harga, interpolasi "
        "FROM harga_agregat WHERE tingkat_wilayah IN :tingkat"
    ).bindparams(bindparam("tingkat", expanding=True))
    with eng.connect() as c:
        df = pd.read_sql(sql, c, params={"tingkat": tingkat}, parse_dates=["tanggal"])
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df


def baca_meta(eng: Engine) -> dict[str, str]:
    with eng.connect() as c:
        return {k: v for k, v in c.execute(text("SELECT kunci, nilai FROM meta")).all()}


def versi_data(eng: Engine) -> int:
    return int(baca_meta(eng).get("versi_data", "0"))


def set_meta(eng: Engine, **kv: str) -> None:
    with eng.begin() as c:
        for k, v in kv.items():
            c.execute(
                text("INSERT INTO meta (kunci, nilai) VALUES (:k, :v) ON CONFLICT (kunci) DO UPDATE SET nilai = EXCLUDED.nilai"),
                {"k": k, "v": str(v)},
            )


def _seragam(baris: list[dict], versi_data: int, **bawaan) -> list[dict]:
    """Samakan kunci setiap baris sebelum INSERT banyak baris sekaligus.

    SQLAlchemy mewajibkan semua baris punya parameter yang sama. Baris dari jalur berbeda di pipeline
    bisa kehilangan kunci (mis. versi_data), jadi versi_data selalu diisi dari pemanggil dan kunci
    opsional diberi nilai bawaan.
    """
    return [{**bawaan, **b, "versi_data": versi_data} for b in baris]


def tulis_hasil(eng: Engine, hasil: dict, versi_data: int) -> None:
    """Ganti seluruh tabel hasil dalam satu transaksi, supaya pembaca selalu melihat satu versi yang utuh."""
    hasil = {
        "prediksi": _seragam(hasil.get("prediksi") or [], versi_data),
        "status": _seragam(hasil.get("status") or [], versi_data),
        "evaluasi": _seragam(hasil.get("evaluasi") or [], versi_data),
        "evaluasi_status": _seragam(hasil.get("evaluasi_status") or [], versi_data),
        "dilewati": _seragam(hasil.get("dilewati") or [], versi_data, n_hari=None, alasan=""),
    }
    with eng.begin() as c:
        for t in ("prediksi", "status_harga", "evaluasi_model", "evaluasi_status", "deret_dilewati"):
            c.execute(text(f"DELETE FROM {t}"))

        if hasil["prediksi"]:
            c.execute(text("""INSERT INTO prediksi (kecamatan, nama_pasar, komoditas, sumber, horizon, tanggal_dasar,
                harga_dasar, harga_prediksi, batas_bawah, batas_atas, versi_data)
                VALUES (:kecamatan, :nama_pasar, :komoditas, :sumber, :horizon, :tanggal_dasar,
                :harga_dasar, :harga_prediksi, :batas_bawah, :batas_atas, :versi_data)"""), hasil["prediksi"])
        if hasil["status"]:
            c.execute(text("""INSERT INTO status_harga (kecamatan, nama_pasar, komoditas, sumber, status,
                perubahan_prediksi_pct, ambang_waspada_pct, ambang_lonjakan_pct, tanggal_dasar, versi_data)
                VALUES (:kecamatan, :nama_pasar, :komoditas, :sumber, :status,
                :perubahan_prediksi_pct, :ambang_waspada_pct, :ambang_lonjakan_pct, :tanggal_dasar, :versi_data)"""), hasil["status"])
        if hasil["evaluasi"]:
            c.execute(text("""INSERT INTO evaluasi_model (kecamatan, nama_pasar, komoditas, sumber, horizon, n_uji,
                mae_model, rmse_model, mape_model, mae_baseline, rmse_baseline, mape_baseline, mengalahkan_baseline, versi_data)
                VALUES (:kecamatan, :nama_pasar, :komoditas, :sumber, :horizon, :n_uji,
                :mae_model, :rmse_model, :mape_model, :mae_baseline, :rmse_baseline, :mape_baseline, :mengalahkan_baseline, :versi_data)"""),
                hasil["evaluasi"])
        if hasil["evaluasi_status"]:
            c.execute(text("""INSERT INTO evaluasi_status (komoditas, n_uji, n_berisiko, recall_berisiko, presisi_berisiko,
                ambang_waspada_pct, ambang_lonjakan_pct, versi_data)
                VALUES (:komoditas, :n_uji, :n_berisiko, :recall_berisiko, :presisi_berisiko,
                :ambang_waspada_pct, :ambang_lonjakan_pct, :versi_data)"""), hasil["evaluasi_status"])
        if hasil["dilewati"]:
            c.execute(text("""INSERT INTO deret_dilewati (kecamatan, nama_pasar, komoditas, sumber, alasan, n_hari, versi_data)
                VALUES (:kecamatan, :nama_pasar, :komoditas, :sumber, :alasan, :n_hari, :versi_data)
                ON CONFLICT DO NOTHING"""), hasil["dilewati"])

        for k, v in (("versi_model", str(versi_data)), ("hitung_selesai", datetime.now(timezone.utc).isoformat(timespec="seconds"))):
            c.execute(text("INSERT INTO meta (kunci, nilai) VALUES (:k, :v) ON CONFLICT (kunci) DO UPDATE SET nilai = EXCLUDED.nilai"),
                      {"k": k, "v": v})