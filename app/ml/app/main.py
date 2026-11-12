"""Layanan ML (FastAPI): POST /retrain (asinkron) dan GET /health. Lihat Project.md 6.8."""
from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from . import db, pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ml")

_kunci = threading.Lock()
_berjalan = False


class PermintaanRetrain(BaseModel):
    versi_data: int | None = None


def _putaran() -> None:
    """Latih ulang sampai versi_data stabil: tulis data yang masuk saat pelatihan akan memicu putaran lagi."""
    global _berjalan
    eng = db.engine()
    while True:
        try:
            v = db.versi_data(eng)
            db.set_meta(eng, status_hitung="running", pesan_hitung="")
            t0 = time.time()
            hasil = pipeline.jalankan(db.baca_harga(eng), v)
            db.tulis_hasil(eng, hasil, v)
            log.info("pelatihan versi_data=%s selesai dalam %.1f detik", v, time.time() - t0)
        except Exception as e:  # noqa: BLE001 - status galat harus sampai ke antarmuka
            log.exception("pelatihan gagal")
            try:
                db.set_meta(eng, status_hitung="error", pesan_hitung=f"{type(e).__name__}: {e}"[:500])
            except Exception:  # noqa: BLE001 - database mungkin yang bermasalah
                log.exception("gagal menulis status error")
            finally:
                with _kunci:
                    _berjalan = False
            return
        with _kunci:
            if db.versi_data(eng) == v:
                db.set_meta(eng, status_hitung="idle", pesan_hitung="")
                _berjalan = False
                return
        log.info("versi_data berubah saat pelatihan, mengulang")


def _mulai_bila_perlu() -> bool:
    global _berjalan
    with _kunci:
        if _berjalan:
            return False
        _berjalan = True
    return True


def _pulihkan_saat_start() -> None:
    """Bila layanan baru hidup dan model tertinggal dari data (atau pelatihan terputus), lanjutkan."""
    for _ in range(30):
        try:
            m = db.baca_meta(db.engine())
            break
        except Exception:  # database atau tabel belum siap (migrasi dijalankan backend Go)
            time.sleep(2)
    else:
        return
    vd, vm = int(m.get("versi_data", "0")), int(m.get("versi_model", "0"))
    if vd > 0 and (vm != vd or m.get("status_hitung") == "running") and _mulai_bila_perlu():
        log.info("memulihkan pelatihan (versi_data=%s, versi_model=%s)", vd, vm)
        _putaran()


@asynccontextmanager
async def lifespan(_: FastAPI):
    threading.Thread(target=_pulihkan_saat_start, daemon=True).start()
    yield


app = FastAPI(title="Layanan ML Harga Pangan Medan", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "berjalan": _berjalan}


@app.post("/retrain", status_code=202)
def retrain(_: PermintaanRetrain, tugas: BackgroundTasks) -> dict:
    """Mulai pelatihan ulang di latar belakang dan langsung membalas 202 (Go tidak menunggu)."""
    if _mulai_bila_perlu():
        tugas.add_task(_putaran)
        return {"status": "dimulai"}
    # Sudah berjalan: putaran aktif akan memeriksa versi_data lagi di akhir dan mengulang bila perlu.
    return {"status": "sudah_berjalan"}