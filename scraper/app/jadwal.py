"""Penjadwal tarikan: sekali saat layanan menyala, lalu setiap hari pada jam di SCRAPER_JADWAL (waktu SCRAPER_ZONA)."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from . import backend, config, riwayat, tarikan

log = logging.getLogger("scraper.jadwal")


def berikutnya(sekarang: datetime, jadwal: tuple[str, ...]) -> datetime:
    """Waktu tarikan terjadwal berikutnya setelah `sekarang` (zona waktu mengikuti `sekarang`)."""
    jam = sorted(time.fromisoformat(j) for j in jadwal)
    for hari in (0, 1):
        tgl = sekarang.date() + timedelta(days=hari)
        for j in jam:
            kandidat = datetime.combine(tgl, j, tzinfo=sekarang.tzinfo)
            if kandidat > sekarang:
                return kandidat
    return datetime.combine(sekarang.date() + timedelta(days=1), jam[0], tzinfo=sekarang.tzinfo)


def perlu_tarik_saat_mulai(sekarang: datetime) -> bool:
    """Lewati tarikan saat menyala bila tarikan sukses terakhir belum lama (mis. layanan sering dinyalakan ulang)."""
    c = riwayat.terakhir_sukses()
    if not c:
        return True
    try:
        terakhir = datetime.fromisoformat(c["mulai"])
    except (KeyError, ValueError):
        return True
    return sekarang - terakhir >= timedelta(hours=config.JEDA_MIN_JAM)


class Penjadwal(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="penjadwal")
        self._henti = threading.Event()
        self.berikutnya: datetime | None = None

    def henti(self):
        self._henti.set()

    def _tarik(self, pemicu: str):
        try:
            tarikan.jalankan(pemicu)
        except tarikan.SedangBerjalan:
            log.info("tarikan %s dilewati: tarikan lain masih berjalan", pemicu)
        except Exception:
            log.exception("tarikan %s gagal", pemicu)

    def run(self):
        zona = ZoneInfo(config.ZONA)
        if not backend.siap():
            log.warning("backend belum menjawab; penjadwal tetap berjalan dan mencoba pada jadwal berikutnya")
        elif perlu_tarik_saat_mulai(datetime.now(zona)):
            self._tarik("mulai")
        else:
            log.info("tarikan saat menyala dilewati: tarikan sukses terakhir kurang dari %.0f jam lalu", config.JEDA_MIN_JAM)
        while not self._henti.is_set():
            self.berikutnya = berikutnya(datetime.now(zona), config.JADWAL)
            log.info("tarikan berikutnya: %s", self.berikutnya.isoformat(timespec="minutes"))
            while not self._henti.is_set():
                sisa = (self.berikutnya - datetime.now(zona)).total_seconds()
                if sisa <= 0:
                    break
                self._henti.wait(min(sisa, 60))
            if not self._henti.is_set():
                self._tarik("jadwal")