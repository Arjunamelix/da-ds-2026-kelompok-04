"""Riwayat tarikan: satu baris JSON per tarikan di data/raw/otomatis/riwayat_tarikan.jsonl."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from . import config

_kunci = threading.Lock()


def _berkas() -> Path:
    return config.DIR_OTOMATIS / "riwayat_tarikan.jsonl"


def tambah(catatan: dict) -> None:
    with _kunci:
        p = _berkas()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(catatan, ensure_ascii=False, default=str) + "\n")


def baca(n: int = 20) -> list[dict]:
    p = _berkas()
    if not p.exists():
        return []
    with _kunci, p.open(encoding="utf-8") as f:
        baris = f.readlines()[-n:]
    out = []
    for b in baris:
        try:
            out.append(json.loads(b))
        except json.JSONDecodeError:
            continue
    return out


def terakhir_sukses() -> dict | None:
    for c in reversed(baca(200)):
        if c.get("status") in ("sukses", "sebagian"):
            return c
    return None