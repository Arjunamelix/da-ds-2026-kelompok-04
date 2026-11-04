"""Cek sekali: apakah ?menu=peta SIMPANG masih bisa diakses tanpa alat penembus."""
import json
import re

import requests

UA = {"User-Agent": "HargaPanganMedan/0.1 (proyek mahasiswa IT Del; kontak: <isi email tim>)"}

r = requests.post(
    "https://simpang.medan.go.id/?menu=peta",
    data={"drtanggal": "2026-11-03", "sptanggal": "2026-11-03", "id_komoditi": "1"},
    headers=UA,
    timeout=20,
)
teks = r.text
print("status HTTP :", r.status_code, "| panjang halaman:", len(teks))
for k in ("cf-turnstile", "challenge-platform", "just a moment"):
    print(f"  kata '{k}':", k in teks.lower())

m = re.search(r"const\s+datahargakecamatan\s*=\s*({.*?});", teks, re.S | re.I)
if m:
    d = json.loads(m.group(1))
    pasar = [p for v in d.values() for p in (v.get("pasar") or [])]
    berharga = [p for p in pasar if str(p.get("harga", "0")).strip() not in ("", "0")]
    print("kecamatan:", len(d), "| pasar:", len(pasar), "| pasar berisi harga:", len(berharga))
    print("contoh:", berharga[:3])
else:
    print("data per pasar TIDAK ditemukan")

rb = requests.get("https://simpang.medan.go.id/robots.txt", headers=UA, timeout=20)
print("\nrobots.txt (status", rb.status_code, "):")
print(rb.text[:800] if rb.status_code == 200 else "(tidak ada)")