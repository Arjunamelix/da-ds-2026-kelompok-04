-- Dataset harga (satu tabel, terus bertambah). Lihat Project.md bagian 5 dan 6.1.
CREATE TABLE harga (
    id              BIGSERIAL PRIMARY KEY,
    tanggal         DATE      NOT NULL,
    kecamatan       TEXT      NOT NULL,
    nama_pasar      TEXT      NOT NULL,
    komoditas       TEXT      NOT NULL,
    harga           INTEGER   NOT NULL CHECK (harga > 0),
    sumber          TEXT      NOT NULL,
    satuan          TEXT      NOT NULL,
    tingkat_wilayah TEXT      GENERATED ALWAYS AS (CASE WHEN nama_pasar = 'SEMUA' THEN 'kota' ELSE 'pasar' END) STORED,
    interpolasi     SMALLINT  NOT NULL DEFAULT 0 CHECK (interpolasi IN (0, 1)),
    dibuat_pada     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT harga_kunci_unik UNIQUE (tanggal, kecamatan, nama_pasar, komoditas, sumber)
);

CREATE INDEX idx_harga_deret ON harga (komoditas, kecamatan, nama_pasar, sumber, tanggal);
CREATE INDEX idx_harga_tanggal ON harga (tanggal);

-- Metadata kecil: versi_data (kunci cache), versi_model, status pelatihan ulang.
CREATE TABLE meta (
    kunci TEXT PRIMARY KEY,
    nilai TEXT NOT NULL
);

INSERT INTO meta (kunci, nilai) VALUES
    ('versi_data', '0'),
    ('versi_model', '0'),
    ('status_hitung', 'idle'),
    ('pesan_hitung', ''),
    ('hitung_mulai', ''),
    ('hitung_selesai', '');

-- Tabel hasil model (data turunan, ditulis layanan Python; bukan bagian dari dataset harga).
CREATE TABLE prediksi (
    kecamatan      TEXT NOT NULL,
    nama_pasar     TEXT NOT NULL,
    komoditas      TEXT NOT NULL,
    sumber         TEXT NOT NULL,
    horizon        SMALLINT NOT NULL,
    tanggal_dasar  DATE NOT NULL,
    harga_dasar    DOUBLE PRECISION NOT NULL,
    harga_prediksi DOUBLE PRECISION NOT NULL,
    batas_bawah    DOUBLE PRECISION NOT NULL,
    batas_atas     DOUBLE PRECISION NOT NULL,
    versi_data     BIGINT NOT NULL,
    dibuat_pada    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (kecamatan, nama_pasar, komoditas, sumber, horizon)
);

CREATE TABLE status_harga (
    kecamatan        TEXT NOT NULL,
    nama_pasar       TEXT NOT NULL,
    komoditas        TEXT NOT NULL,
    sumber           TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('Normal', 'Waspada', 'Lonjakan')),
    perubahan_prediksi_pct DOUBLE PRECISION NOT NULL,
    ambang_waspada_pct     DOUBLE PRECISION NOT NULL,
    ambang_lonjakan_pct    DOUBLE PRECISION NOT NULL,
    tanggal_dasar    DATE NOT NULL,
    versi_data       BIGINT NOT NULL,
    dibuat_pada      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (kecamatan, nama_pasar, komoditas, sumber)
);

CREATE TABLE evaluasi_model (
    kecamatan      TEXT NOT NULL,
    nama_pasar     TEXT NOT NULL,
    komoditas      TEXT NOT NULL,
    sumber         TEXT NOT NULL,
    horizon        SMALLINT NOT NULL,
    n_uji          INTEGER NOT NULL,
    mae_model      DOUBLE PRECISION NOT NULL,
    rmse_model     DOUBLE PRECISION NOT NULL,
    mape_model     DOUBLE PRECISION NOT NULL,
    mae_baseline   DOUBLE PRECISION NOT NULL,
    rmse_baseline  DOUBLE PRECISION NOT NULL,
    mape_baseline  DOUBLE PRECISION NOT NULL,
    mengalahkan_baseline BOOLEAN NOT NULL,
    versi_data     BIGINT NOT NULL,
    dibuat_pada    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (kecamatan, nama_pasar, komoditas, sumber, horizon)
);

-- Evaluasi klasifikasi status (kelas berisiko = Waspada + Lonjakan), per komoditas.
CREATE TABLE evaluasi_status (
    komoditas   TEXT PRIMARY KEY,
    n_uji       INTEGER NOT NULL,
    n_berisiko  INTEGER NOT NULL,
    recall_berisiko  DOUBLE PRECISION,
    presisi_berisiko DOUBLE PRECISION,
    ambang_waspada_pct  DOUBLE PRECISION NOT NULL,
    ambang_lonjakan_pct DOUBLE PRECISION NOT NULL,
    versi_data  BIGINT NOT NULL,
    dibuat_pada TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Deret yang dilewati (data belum cukup dan sebagainya), supaya antarmuka bisa menjelaskannya.
CREATE TABLE deret_dilewati (
    kecamatan  TEXT NOT NULL,
    nama_pasar TEXT NOT NULL,
    komoditas  TEXT NOT NULL,
    sumber     TEXT NOT NULL,
    alasan     TEXT NOT NULL,
    n_hari     INTEGER NOT NULL,
    versi_data BIGINT NOT NULL,
    PRIMARY KEY (kecamatan, nama_pasar, komoditas, sumber)
);