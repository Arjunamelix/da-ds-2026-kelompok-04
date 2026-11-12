"""Satu tarikan data: tentukan rentang -> ambil dari sumber -> simpan mentah -> perbarui master (tanpa duplikat)
-> bersihkan (aturan_bersih.py) -> tahan tanggal yang tidak lengkap -> impor ke backend -> catat riwayat.

Data tidak pernah tergandakan:
  - master_data_harian.csv: satu baris per (tanggal, kecamatan, pasar, komoditas, sumber) (aturan_bersih.gabung_ke_master)
  - database: kunci unik yang sama; impor ulang menghasilkan "baru disimpan 0"
Menjalankan tarikan berkali-kali pada hari yang sama aman: yang bertambah hanya data yang memang baru.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from . import backend, config, riwayat, sumber_simpang, sumber_sp2kp
from aturan_bersih import KOLOM, bersihkan, gabung_ke_master  # noqa: E402  (path dari config.SCRIPTS_DIR)

log = logging.getLogger("scraper.tarikan")

ADAPTER = {"simpang": sumber_simpang, "sp2kp": sumber_sp2kp}

_kunci = threading.Lock()
_keadaan = {"sedang_berjalan": False, "mulai": None, "pemicu": None}


class SedangBerjalan(RuntimeError):
    """Tarikan lain masih berjalan."""


def sekarang() -> datetime:
    return datetime.now(ZoneInfo(config.ZONA))


def keadaan() -> dict:
    return dict(_keadaan)


def rentang(terakhir: date, hari_ini: date) -> list[date]:
    """Tanggal yang diambil: dari (terakhir - HARI_MUNDUR) sampai hari ini, paling panjang MAKS_HARI hari."""
    mulai = max(terakhir - timedelta(days=config.HARI_MUNDUR), hari_ini - timedelta(days=config.MAKS_HARI - 1))
    return [mulai + timedelta(days=i) for i in range((hari_ini - mulai).days + 1)]


def sesi_http() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept": "text/html,application/json"})
    return s


def _simpan_mentah(kode: str, cap: str, mentah: list[dict]) -> str:
    d = config.DIR_OTOMATIS / kode
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{cap}.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for m in mentah:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return str(p)


def _perbarui_master(baru: pd.DataFrame) -> dict:
    p = config.MASTER
    if p.exists():
        master = pd.read_csv(p, dtype={"tanggal": str, "kecamatan": str, "nama_pasar": str, "komoditas": str, "sumber": str},
                             keep_default_na=False)
        master["harga"] = master["harga"].astype("int64")
    else:
        master = pd.DataFrame(columns=KOLOM).astype({"harga": "int64"})
    hasil, info = gabung_ke_master(master, baru)
    if info["ditambahkan"] or info["diisi_dari_0"]:
        sementara = p.with_suffix(".csv.tmp")
        hasil.to_csv(sementara, index=False)
        os.replace(sementara, p)                     # tulis atomik: master tidak pernah setengah tertulis
    info["baris_master"] = int(len(hasil))
    return info


def _tahan_tidak_lengkap(bersih: pd.DataFrame, min_pasar: int) -> tuple[pd.DataFrame, list[dict]]:
    """Tanggal dengan pasar berharga kurang dari min_pasar tidak diimpor (data hari itu belum lengkap)."""
    if bersih.empty:
        return bersih, []
    n = bersih.groupby("tanggal")["nama_pasar"].nunique()
    kurang = n[n < min_pasar]
    ditahan = [{"tanggal": t, "pasar": int(v)} for t, v in kurang.items()]
    return bersih[~bersih["tanggal"].isin(kurang.index)], ditahan


def tarik_sumber(kode: str, hari_ini: date, cap: str, dry_run: bool = False,
                 dari: date | None = None, sampai: date | None = None) -> dict:
    mod = ADAPTER[kode]
    hasil: dict = {"status": "sukses"}
    try:
        if kode == "sp2kp" and not config.SP2KP_PASAR:
            return {"status": "dilewati", "pesan": "SCRAPER_SP2KP_PASAR belum diisi (ID pasar SP2KP)"}

        if dari is None:
            terakhir = backend.tanggal_terakhir(mod.SUMBER_BACKEND)
            if terakhir is None:
                return {"status": "dilewati", "pesan": "database belum berisi data sumber ini; impor master lebih dulu"}
            tanggal = rentang(terakhir, hari_ini)
            hasil["tanggal_terakhir_db"] = terakhir.isoformat()
        else:
            akhir = sampai or hari_ini
            tanggal = [dari + timedelta(days=i) for i in range((akhir - dari).days + 1)]
        if not tanggal:
            return {"status": "dilewati", "pesan": "tidak ada tanggal untuk diambil"}

        sesi = sesi_http()
        if kode == "simpang":
            rows, mentah, ringkas = mod.ambil(tanggal, sesi, jeda=config.JEDA_DETIK, batas_waktu=config.BATAS_WAKTU)
        else:
            rows, mentah, ringkas = mod.ambil(tanggal[0], tanggal[-1], sesi, config.SP2KP_PASAR,
                                              jeda=config.JEDA_DETIK, batas_waktu=config.BATAS_WAKTU)
        hasil["ambil"] = ringkas
        baru = pd.DataFrame(rows, columns=KOLOM)
        baru["harga"] = baru["harga"].astype("int64")

        if not dry_run:
            hasil["mentah"] = _simpan_mentah(kode, cap, mentah)
            if config.TULIS_MASTER and len(baru):
                hasil["master"] = _perbarui_master(baru)

        if baru.empty:
            hasil["impor"] = {"disisipkan": 0, "pesan": "sumber belum punya data untuk rentang ini"}
            return hasil

        hb = bersihkan(baru, min_baris_salinan=50)
        hasil["bersih"] = {"valid": int(len(hb.bersih)), "harga_0": hb.n_nol,
                           "ditolak": {k: int(v) for k, v in hb.ditolak["alasan"].value_counts().items()},
                           "peringatan": hb.peringatan}
        lolos, ditahan = _tahan_tidak_lengkap(hb.bersih, config.MIN_PASAR[kode])
        hasil["ditahan"] = ditahan
        hasil["tanggal_berdata"] = sorted(lolos["tanggal"].unique().tolist())

        if dry_run:
            hasil["impor"] = {"disisipkan": 0, "pesan": f"dry-run: {len(lolos)} baris akan dikirim"}
        elif len(lolos):
            hasil["impor"] = backend.impor(lolos, f"scraper_{kode}_{cap}.csv")
        else:
            hasil["impor"] = {"disisipkan": 0, "pesan": "tidak ada tanggal lengkap untuk diimpor"}
        return hasil

    except (sumber_simpang.SumberDitolak, sumber_sp2kp.SumberDitolak) as e:
        log.error("%s: %s", kode, e)
        return hasil | {"status": "galat", "jenis": "ditolak", "pesan": str(e)}
    except backend.BackendTakTerjangkau as e:
        log.error("%s: %s", kode, e)
        return hasil | {"status": "galat", "jenis": "backend", "pesan": str(e)}
    except sumber_simpang.StrukturBerubah as e:
        log.error("%s: %s", kode, e)
        return hasil | {"status": "galat", "jenis": "struktur", "pesan": str(e)}
    except Exception as e:  # satu sumber gagal tidak boleh menghentikan sumber lain
        log.exception("%s gagal", kode)
        return hasil | {"status": "galat", "jenis": type(e).__name__, "pesan": str(e)[:500]}


def jalankan(pemicu: str = "manual", dry_run: bool = False, dari: date | None = None, sampai: date | None = None,
             sumber: tuple[str, ...] | None = None) -> dict:
    """Jalankan satu tarikan untuk semua sumber aktif. SedangBerjalan bila ada tarikan lain."""
    if not _kunci.acquire(blocking=False):
        raise SedangBerjalan("tarikan lain masih berjalan")
    mulai = sekarang()
    _keadaan.update(sedang_berjalan=True, mulai=mulai.isoformat(timespec="seconds"), pemicu=pemicu)
    try:
        cap = mulai.strftime("%Y-%m-%dT%H-%M-%S")
        per = {}
        for kode in sumber or config.SUMBER:
            if kode not in ADAPTER:
                per[kode] = {"status": "galat", "pesan": f"sumber '{kode}' tidak dikenal"}
                continue
            per[kode] = tarik_sumber(kode, mulai.date(), cap, dry_run=dry_run, dari=dari, sampai=sampai)

        status = [p["status"] for p in per.values()]
        if all(s == "dilewati" for s in status):
            ringkas = "dilewati"
        elif all(s in ("sukses", "dilewati") for s in status):
            ringkas = "sukses"
        elif any(s == "sukses" for s in status):
            ringkas = "sebagian"
        else:
            ringkas = "galat"
        catatan = {
            "mulai": mulai.isoformat(timespec="seconds"), "selesai": sekarang().isoformat(timespec="seconds"),
            "pemicu": pemicu, "dry_run": dry_run, "status": ringkas,
            "baris_baru": sum(int((p.get("impor") or {}).get("disisipkan") or 0) for p in per.values()),
            "sumber": per,
        }
        if not dry_run:
            riwayat.tambah(catatan)
        log.info("tarikan %s selesai: %s, %d baris baru", pemicu, ringkas, catatan["baris_baru"])
        return catatan
    finally:
        _keadaan.update(sedang_berjalan=False)
        _kunci.release()