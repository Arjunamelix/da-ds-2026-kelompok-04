"""API kecil layanan scraper (dipanggil backend Go; tidak dibuka ke luar Docker).

  GET  /health    -> {"status": "ok"}
  GET  /status    -> sedang berjalan atau tidak, jadwal, tarikan terakhir, riwayat
  POST /jalankan  -> mulai tarikan sekarang (202), atau 409 bila tarikan lain masih berjalan
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import config, jadwal, riwayat, tarikan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("scraper")

_penjadwal: jadwal.Penjadwal | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _penjadwal
    log.info("scraper menyala: sumber=%s, jadwal=%s %s, aktif=%s", ",".join(config.SUMBER), ",".join(config.JADWAL),
             config.ZONA, config.AKTIF)
    if config.AKTIF:
        _penjadwal = jadwal.Penjadwal()
        _penjadwal.start()
    yield
    if _penjadwal:
        _penjadwal.henti()


app = FastAPI(title="Scraper data harga", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict:
    hist = riwayat.baca(10)
    return {
        **tarikan.keadaan(),
        "aktif": config.AKTIF,
        "sumber": list(config.SUMBER),
        "jadwal": list(config.JADWAL),
        "zona": config.ZONA,
        "berikutnya": _penjadwal.berikutnya.isoformat(timespec="minutes") if _penjadwal and _penjadwal.berikutnya else None,
        "terakhir": hist[-1] if hist else None,
        "terakhir_sukses": riwayat.terakhir_sukses(),
        "riwayat": list(reversed(hist)),
    }


def _latar():
    try:
        tarikan.jalankan("manual")
    except tarikan.SedangBerjalan:
        pass
    except Exception:
        log.exception("tarikan manual gagal")


@app.post("/jalankan", status_code=202)
def jalankan():
    if tarikan.keadaan()["sedang_berjalan"]:
        return JSONResponse(status_code=409, content={"error": "tarikan lain masih berjalan"})
    threading.Thread(target=_latar, daemon=True, name="tarikan-manual").start()
    return {"status": "running"}