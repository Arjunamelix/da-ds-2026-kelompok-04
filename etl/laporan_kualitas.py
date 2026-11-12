"""Laporan kualitas data sebelum dan sesudah pembersihan (panduan 4.1: completeness, validity, consistency, uniqueness).

Membaca data mentah dan hasil etl/etl_master.py, lalu menulis docs/kualitas_data.md.
Jalankan setelah etl_master.py:
  python etl/laporan_kualitas.py
"""
from pathlib import Path

import pandas as pd

AKAR = Path(__file__).resolve().parent.parent
MENTAH = AKAR / "data" / "raw" / "master_data_harian.csv"
OLAH = AKAR / "data" / "processed"
KELUAR = AKAR / "docs" / "kualitas_data.md"
KUNCI = ["tanggal", "kecamatan", "nama_pasar", "komoditas", "sumber"]


def pct(a, b):
    return f"{100 * a / b:.1f}%".replace(".", ",") if b else "-"


def angka(x):
    return f"{x:,}".replace(",", ".")


def main():
    raw = pd.read_csv(MENTAH)
    bersih = pd.concat([pd.read_csv(OLAH / "harga_harian_simpang.csv"), pd.read_csv(OLAH / "harga_harian_sp2kp.csv")])
    tolak = pd.read_csv(OLAH / "master_ditolak.csv")
    n_raw, n_bersih = len(raw), len(bersih)

    # completeness
    nol = int((raw["harga"] == 0).sum())
    # validity: baris berharga > 0 yang lolos semua aturan
    terisi = n_raw - nol
    tidak_valid = int(tolak[~tolak["alasan"].str.startswith("salinan")].shape[0])
    salinan = int(tolak[tolak["alasan"].str.startswith("salinan")].shape[0])
    # consistency
    pasar_raw = raw["nama_pasar"].nunique()
    pasar_spasi = int((raw["nama_pasar"] != raw["nama_pasar"].str.strip()).sum())
    pasar_bersih = bersih["nama_pasar"].nunique()
    # uniqueness
    dup_raw = int(raw.duplicated(KUNCI).sum())
    dup_bersih = int(bersih.duplicated(KUNCI).sum())

    alasan = tolak["alasan"].value_counts()
    per_kom = (bersih.groupby(["sumber", "komoditas"])
               .agg(baris=("harga", "size"), hari=("tanggal", "nunique"), pasar=("nama_pasar", "nunique"),
                    mulai=("tanggal", "min"), akhir=("tanggal", "max"), median=("harga", "median"))
               .reset_index())
    raw_kom = raw.assign(terisi=raw["harga"] > 0).groupby(["sumber", "komoditas"]).agg(
        baris_mentah=("harga", "size"), terisi=("terisi", "sum")).reset_index()

    L = []
    L.append("# Laporan kualitas data\n")
    L.append("Dibuat otomatis oleh `etl/laporan_kualitas.py` dari `data/raw/master_data_harian.csv` "
             "dan hasil `etl/etl_master.py`. Jangan diedit manual; jalankan ulang skripnya bila data berubah.\n")
    L.append("## Ringkasan sebelum dan sesudah\n")
    L.append("| Dimensi | Ukuran | Sebelum (mentah) | Sesudah (bersih) |")
    L.append("|---|---|---|---|")
    L.append(f"| Jumlah baris | baris | {angka(n_raw)} | {angka(n_bersih)} |")
    L.append(f"| **Completeness** | baris dengan harga terisi (bukan 0) | {angka(terisi)} dari {angka(n_raw)} ({pct(terisi, n_raw)}) | {angka(n_bersih)} dari {angka(n_bersih)} (100%) |")
    L.append(f"| **Validity** | baris terisi yang lolos semua aturan validasi | {angka(terisi - tidak_valid - salinan)} dari {angka(terisi)} ({pct(terisi - tidak_valid - salinan, terisi)}) | 100% |")
    L.append(f"| **Consistency** | ejaan nama pasar | {pasar_raw} ejaan, {angka(pasar_spasi)} baris berspasi di tepi, ejaan SP2KP berbeda dari SIMPANG | {pasar_bersih} nama baku |")
    L.append(f"| | nama komoditas dan sumber | nama bebas (`gula pasir`, `simpang_medan`) | kode baku (`gula_pasir`, `SIMPANG`) |")
    L.append(f"| | komoditas salinan komoditas lain | {angka(salinan)} baris | 0 |")
    L.append(f"| | satuan telur (per butir dan per kg bercampur) | {angka(int(alasan.get('satuan per butir, bukan per kg', 0)))} baris per butir | hanya per kg |")
    L.append(f"| **Uniqueness** | duplikat kunci (tanggal, kecamatan, pasar, komoditas, sumber) | {dup_raw} | {dup_bersih} (dijaga constraint `harga_kunci_unik`) |")
    L.append("")
    L.append("## Baris yang dibuang dan alasannya\n")
    L.append("| Alasan | Baris |")
    L.append("|---|---|")
    L.append(f"| Harga 0 (tidak ada laporan pada hari itu) | {angka(nol)} |")
    for a, n in alasan.items():
        L.append(f"| {a} | {angka(int(n))} |")
    L.append(f"| **Total dibuang** | **{angka(n_raw - n_bersih)}** |")
    L.append("")
    L.append("Rincian per baris ada di `data/processed/master_ditolak.csv`.\n")
    L.append("## Per sumber dan komoditas\n")
    L.append("| Sumber | Komoditas | Baris mentah | Terisi | Baris bersih | Hari berdata | Pasar | Periode | Median (Rp) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    peta = {"simpang_medan": "SIMPANG", "sp2kp": "SP2KP"}
    raw_kom["sumber"] = raw_kom["sumber"].str.lower().map(peta)
    raw_kom["kom"] = raw_kom["komoditas"].str.lower()
    nama = {"beras": "beras_medium", "minyak goreng": "minyak_goreng_curah", "telur ayam": "telur_ayam_ras"}
    raw_kom["komoditas"] = raw_kom["kom"].map(lambda k: nama.get(k, k.replace(" ", "_")))
    gab = raw_kom.merge(per_kom, on=["sumber", "komoditas"], how="left")
    for r in gab.sort_values(["sumber", "komoditas"]).itertuples():
        if pd.isna(r.baris):
            L.append(f"| {r.sumber} | {r.kom} | {angka(r.baris_mentah)} | {angka(int(r.terisi))} | 0 (dibuang) | - | - | - | - |")
        else:
            L.append(f"| {r.sumber} | {r.komoditas} | {angka(r.baris_mentah)} | {angka(int(r.terisi))} | {angka(int(r.baris))} | "
                     f"{int(r.hari)} | {int(r.pasar)} | {r.mulai} s.d. {r.akhir} | {angka(int(r.median))} |")
    L.append("")
    L.append("## Catatan\n")
    L.append("- Hari tanpa laporan **tidak diisi** di database; celah diinterpolasi (maksimal 14 hari) hanya di memori layanan ML saat membuat fitur.")
    L.append("- Telur per butir ditolak, tidak dikonversi, karena faktor butir per kg tidak tersedia dari sumber.")
    L.append("- Kejadian serentak di banyak pasar (mis. bawang merah 6 September 2024) tidak tertangkap aturan penyimpangan karena median hari itu ikut berubah; perlu pemeriksaan manual.")
    KELUAR.parent.mkdir(parents=True, exist_ok=True)
    KELUAR.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {KELUAR}")


if __name__ == "__main__":
    main()