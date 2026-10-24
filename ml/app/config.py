"""Pengaturan layanan ML (dari variabel lingkungan)."""
import os


def _int(nama: str, bawaan: int) -> int:
    try:
        return int(os.getenv(nama, bawaan))
    except ValueError:
        return bawaan


def _float(nama: str, bawaan: float) -> float:
    try:
        return float(os.getenv(nama, bawaan))
    except ValueError:
        return bawaan


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "postgresql://pangan:pangan@localhost:5432/harga_pangan")
    # Go memakai skema postgres://, SQLAlchemy butuh driver eksplisit.
    for awal in ("postgres://", "postgresql://"):
        if url.startswith(awal):
            return "postgresql+psycopg2://" + url[len(awal):]
    return url


# Tingkat deret yang dimodelkan (dari view harga_agregat): pasar, kecamatan, kota.
TINGKAT = tuple(t.strip() for t in os.getenv("ML_TINGKAT", "kecamatan,kota").split(",") if t.strip())

# Horizon prediksi (hari)
HORIZON = (7, 14)

# Jumlah hari yang punya data asli minimal agar sebuah deret dimodelkan.
# Project.md 6.3: "batas minimal ditentukan nanti, misalnya 90 hari".
MIN_HARI = _int("ML_MIN_HARI", 90)

# Walk-forward: porsi data uji terakhir, jumlah lipatan, dan minimal baris uji.
UJI_MAKS = _int("ML_UJI_MAKS", 90)
UJI_PORSI = _float("ML_UJI_PORSI", 0.3)
LIPATAN = _int("ML_LIPATAN", 3)
UJI_MIN = _int("ML_UJI_MIN", 20)
LATIH_MIN = _int("ML_LATIH_MIN", 30)

# Jumlah proses paralel saat melatih banyak deret (1 = serial). Bawaan: jumlah core, maksimal 4.
PEKERJA = _int("ML_PEKERJA", min(4, os.cpu_count() or 1))

# Celah maksimal (hari) yang diisi interpolasi saat membangun fitur.
CELAH_MAKS = 14

# Rentang prediksi 80% (kuantil 10% dan 90% galat holdout).
KUANTIL_BAWAH = 0.10
KUANTIL_ATAS = 0.90

# Ambang status per komoditas (usulan; Project.md 2.2 no. 6 menunda keputusan final).
PERSENTIL_WASPADA = _float("ML_PERSENTIL_WASPADA", 80.0)
PERSENTIL_LONJAKAN = _float("ML_PERSENTIL_LONJAKAN", 95.0)
AMBANG_WASPADA_MIN_PCT = _float("ML_AMBANG_WASPADA_MIN_PCT", 2.0)

# Hiperparameter boosting (sengaja kecil: data per deret hanya ratusan baris).
BOOSTING = dict(n_estimators=120, max_depth=3, learning_rate=0.05, subsample=0.8, min_samples_leaf=10, random_state=42)