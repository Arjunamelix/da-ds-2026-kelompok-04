CREATE TABLE ref_hari_besar (
    tanggal DATE PRIMARY KEY,
    nama    TEXT NOT NULL
);

INSERT INTO ref_hari_besar (tanggal, nama) VALUES
    ('2024-01-01', 'Tahun Baru Masehi'), ('2024-02-10', 'Tahun Baru Imlek'), ('2024-03-12', 'Awal Ramadan'),
    ('2024-04-10', 'Idulfitri'),          ('2024-04-11', 'Idulfitri'),         ('2024-06-17', 'Iduladha'),
    ('2024-12-25', 'Natal'),
    ('2025-01-01', 'Tahun Baru Masehi'), ('2025-01-29', 'Tahun Baru Imlek'), ('2025-03-01', 'Awal Ramadan'),
    ('2025-03-31', 'Idulfitri'),          ('2025-04-01', 'Idulfitri'),         ('2025-06-06', 'Iduladha'),
    ('2025-12-25', 'Natal'),
    ('2026-01-01', 'Tahun Baru Masehi'), ('2026-02-17', 'Tahun Baru Imlek'), ('2026-02-19', 'Awal Ramadan'),
    ('2026-03-20', 'Idulfitri'),          ('2026-03-21', 'Idulfitri'),         ('2026-05-27', 'Iduladha'),
    ('2026-12-25', 'Natal');

CREATE TABLE dim_waktu (
    kunci_waktu          INTEGER PRIMARY KEY,           -- YYYYMMDD
    tanggal              DATE    NOT NULL UNIQUE,
    tahun                SMALLINT NOT NULL,
    kuartal              SMALLINT NOT NULL,
    bulan                SMALLINT NOT NULL,
    nama_bulan           TEXT    NOT NULL,
    tahun_bulan          TEXT    NOT NULL,              -- '2025-03', untuk sumbu grafik dan peta panas
    minggu_iso           SMALLINT NOT NULL,
    hari_dalam_minggu    SMALLINT NOT NULL,              -- 1 = Senin ... 7 = Minggu
    nama_hari            TEXT    NOT NULL,
    akhir_pekan          BOOLEAN NOT NULL,
    hari_besar           TEXT,                            -- nama hari besar pada tanggal itu, NULL bila bukan
    menjelang_hari_besar BOOLEAN NOT NULL                 -- 1 sampai 7 hari sebelum hari besar
);

CREATE TABLE dim_wilayah (
    kunci_wilayah   SERIAL PRIMARY KEY,
    kota            TEXT NOT NULL DEFAULT 'Kota Medan',
    kecamatan       TEXT NOT NULL,
    nama_pasar      TEXT NOT NULL,
    tingkat_wilayah TEXT NOT NULL CHECK (tingkat_wilayah IN ('pasar', 'kota')),
    UNIQUE (kecamatan, nama_pasar)
);

CREATE TABLE dim_komoditas (
    kunci_komoditas SERIAL PRIMARY KEY,
    kode            TEXT NOT NULL UNIQUE,
    nama            TEXT NOT NULL,
    kategori        TEXT NOT NULL,
    kelompok        TEXT NOT NULL,                       -- inti / tambahan (sama dengan config/referensi.json)
    satuan          TEXT NOT NULL
);

INSERT INTO dim_komoditas (kode, nama, kategori, kelompok, satuan) VALUES
    ('beras_medium',        'Beras Medium',        'Serealia',          'inti',     'kg'),
    ('jagung',              'Jagung',              'Serealia',          'tambahan', 'kg'),
    ('kedelai',             'Kedelai',             'Kacang-kacangan',   'tambahan', 'kg'),
    ('bawang_merah',        'Bawang Merah',        'Bumbu dan sayur',   'inti',     'kg'),
    ('bawang_putih',        'Bawang Putih',        'Bumbu dan sayur',   'inti',     'kg'),
    ('cabai_merah',         'Cabai Merah',         'Bumbu dan sayur',   'inti',     'kg'),
    ('cabai_rawit',         'Cabai Rawit',         'Bumbu dan sayur',   'inti',     'kg'),
    ('garam_halus',         'Garam Halus',         'Bumbu dan sayur',   'tambahan', 'kg'),
    ('daging_sapi',         'Daging Sapi',         'Protein hewani',    'tambahan', 'kg'),
    ('daging_ayam_ras',     'Daging Ayam Ras',     'Protein hewani',    'tambahan', 'kg'),
    ('telur_ayam_ras',      'Telur Ayam Ras',      'Protein hewani',    'tambahan', 'kg'),
    ('susu_bubuk',          'Susu Bubuk',          'Protein hewani',    'tambahan', '400 g'),
    ('minyak_goreng_curah', 'Minyak Goreng Curah', 'Minyak dan pemanis','inti',     'liter'),
    ('gula_pasir',          'Gula Pasir',          'Minyak dan pemanis','tambahan', 'kg');

CREATE TABLE dim_sumber (
    kunci_sumber SERIAL PRIMARY KEY,
    kode         TEXT NOT NULL UNIQUE,
    nama         TEXT NOT NULL,
    instansi     TEXT NOT NULL,
    cara_ambil   TEXT NOT NULL
);

INSERT INTO dim_sumber (kode, nama, instansi, cara_ambil) VALUES
    ('SIMPANG',     'SIMPANG Pemko Medan',      'Pemerintah Kota Medan',        'scraping situs'),
    ('SP2KP',       'SP2KP Kemendag',           'Kementerian Perdagangan',      'scraping API'),
    ('PIHPS',       'PIHPS Bank Indonesia',     'Bank Indonesia',               'unduh berkas'),
    ('BADANPANGAN', 'Panel Harga Badan Pangan', 'Badan Pangan Nasional',        'unduh berkas');


CREATE TABLE fakta_harga (
    harga_id                BIGINT   PRIMARY KEY,         -- id baris di tabel harga (dimensi degenerasi)
    kunci_waktu             INTEGER  NOT NULL REFERENCES dim_waktu (kunci_waktu),
    kunci_wilayah           INTEGER  NOT NULL REFERENCES dim_wilayah (kunci_wilayah),
    kunci_komoditas         INTEGER  NOT NULL REFERENCES dim_komoditas (kunci_komoditas),
    kunci_sumber            INTEGER  NOT NULL REFERENCES dim_sumber (kunci_sumber),
    harga                   INTEGER  NOT NULL,
    harga_sebelumnya        INTEGER,                      -- harga laporan sebelumnya pada deret yang sama
    perubahan_harian_pct    DOUBLE PRECISION,
    harga_7h_lalu           INTEGER,                      -- harga terakhir dalam rentang 7 sampai 14 hari sebelumnya
    perubahan_7h_pct        DOUBLE PRECISION,
    rata2_7h                DOUBLE PRECISION,             -- rata-rata bergerak 7 hari kalender (deret yang sama)
    rata2_30h               DOUBLE PRECISION,             -- rata-rata bergerak 30 hari kalender
    median_kota             DOUBLE PRECISION,             -- median harga semua pasar pada hari, komoditas, sumber yang sama
    selisih_median_kota_pct DOUBLE PRECISION,
    jumlah_pasar_melapor    SMALLINT NOT NULL,            -- banyak pasar yang melapor pada hari, komoditas, sumber yang sama
    interpolasi             BOOLEAN  NOT NULL
);

CREATE INDEX idx_fakta_waktu     ON fakta_harga (kunci_waktu);
CREATE INDEX idx_fakta_wilayah   ON fakta_harga (kunci_wilayah);
CREATE INDEX idx_fakta_komoditas ON fakta_harga (kunci_komoditas, kunci_waktu);
CREATE INDEX idx_fakta_sumber    ON fakta_harga (kunci_sumber);

CREATE FUNCTION isi_dim_waktu(dari DATE, sampai DATE) RETURNS void LANGUAGE sql AS $$
    INSERT INTO dim_waktu
    SELECT to_char(d, 'YYYYMMDD')::int,
           d,
           extract(year FROM d), extract(quarter FROM d), extract(month FROM d),
           (ARRAY['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'])[extract(month FROM d)],
           to_char(d, 'YYYY-MM'),
           extract(week FROM d),
           extract(isodow FROM d),
           (ARRAY['Senin','Selasa','Rabu','Kamis','Jumat','Sabtu','Minggu'])[extract(isodow FROM d)],
           extract(isodow FROM d) >= 6,
           (SELECT string_agg(nama, ', ') FROM ref_hari_besar r WHERE r.tanggal = d),
           EXISTS (SELECT 1 FROM ref_hari_besar r WHERE r.tanggal > d AND r.tanggal <= d + 7)
    FROM generate_series(dari, sampai, interval '1 day') AS g(t), LATERAL (SELECT g.t::date AS d) x
    ON CONFLICT (tanggal) DO NOTHING;
$$;


CREATE FUNCTION muat_warehouse(komoditas_dipilih TEXT[] DEFAULT NULL) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    t_min DATE;
    t_max DATE;
BEGIN
    IF komoditas_dipilih IS NOT NULL AND cardinality(komoditas_dipilih) = 0 THEN
        RETURN;   -- mis. impor ulang yang semua barisnya sudah ada
    END IF;

    CREATE TEMP TABLE IF NOT EXISTS _wh_harga (LIKE harga) ON COMMIT DROP;
    TRUNCATE _wh_harga;
    INSERT INTO _wh_harga SELECT * FROM harga
    WHERE sumber <> 'DEV' AND (komoditas_dipilih IS NULL OR komoditas = ANY (komoditas_dipilih));

    SELECT min(tanggal), max(tanggal) INTO t_min, t_max FROM _wh_harga;
    IF t_min IS NOT NULL THEN
        PERFORM isi_dim_waktu(t_min, t_max);
    END IF;

    INSERT INTO dim_wilayah (kecamatan, nama_pasar, tingkat_wilayah)
    SELECT DISTINCT kecamatan, nama_pasar, tingkat_wilayah FROM _wh_harga
    ON CONFLICT (kecamatan, nama_pasar) DO NOTHING;

    -- komoditas atau sumber baru yang belum ada di daftar: tetap dimuat dengan nama bawaan
    INSERT INTO dim_komoditas (kode, nama, kategori, kelompok, satuan)
    SELECT DISTINCT ON (komoditas) komoditas, initcap(replace(komoditas, '_', ' ')), 'Lainnya', 'tambahan', satuan
    FROM _wh_harga
    ON CONFLICT (kode) DO NOTHING;

    INSERT INTO dim_sumber (kode, nama, instansi, cara_ambil)
    SELECT DISTINCT sumber, sumber, '-', '-' FROM _wh_harga
    ON CONFLICT (kode) DO NOTHING;

    IF komoditas_dipilih IS NULL THEN
        TRUNCATE fakta_harga;
    ELSE
        DELETE FROM fakta_harga f USING dim_komoditas k
        WHERE k.kunci_komoditas = f.kunci_komoditas AND k.kode = ANY (komoditas_dipilih);
    END IF;

    INSERT INTO fakta_harga
    WITH h AS (
        SELECT * FROM _wh_harga
    ),
    harian AS (   -- median dan jumlah pasar per hari, komoditas, sumber (hanya baris tingkat pasar)
        SELECT tanggal, komoditas, sumber,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY harga) AS median_kota,
               count(*) AS jumlah_pasar
        FROM h WHERE tingkat_wilayah = 'pasar'
        GROUP BY tanggal, komoditas, sumber
    ),
    w AS (
        SELECT h.*,
               lag(h.harga) OVER deret AS harga_sebelumnya,
               last_value(h.harga) OVER (deret RANGE BETWEEN interval '14 days' PRECEDING AND interval '7 days' PRECEDING) AS harga_7h_lalu,
               avg(h.harga) OVER (deret RANGE BETWEEN interval '6 days' PRECEDING AND CURRENT ROW)  AS rata2_7h,
               avg(h.harga) OVER (deret RANGE BETWEEN interval '29 days' PRECEDING AND CURRENT ROW) AS rata2_30h
        FROM h
        WINDOW deret AS (PARTITION BY h.komoditas, h.kecamatan, h.nama_pasar, h.sumber ORDER BY h.tanggal)
    )
    SELECT w.id,
           to_char(w.tanggal, 'YYYYMMDD')::int,
           dw.kunci_wilayah, dk.kunci_komoditas, ds.kunci_sumber,
           w.harga,
           w.harga_sebelumnya,
           round((100.0 * (w.harga - w.harga_sebelumnya) / w.harga_sebelumnya)::numeric, 2),
           w.harga_7h_lalu,
           round((100.0 * (w.harga - w.harga_7h_lalu) / w.harga_7h_lalu)::numeric, 2),
           round(w.rata2_7h::numeric, 2),
           round(w.rata2_30h::numeric, 2),
           hr.median_kota,
           round((100.0 * (w.harga - hr.median_kota) / hr.median_kota)::numeric, 2),
           coalesce(hr.jumlah_pasar, 0),
           w.interpolasi = 1
    FROM w
    JOIN dim_wilayah   dw ON dw.kecamatan = w.kecamatan AND dw.nama_pasar = w.nama_pasar
    JOIN dim_komoditas dk ON dk.kode = w.komoditas
    JOIN dim_sumber    ds ON ds.kode = w.sumber
    LEFT JOIN harian   hr ON hr.tanggal = w.tanggal AND hr.komoditas = w.komoditas AND hr.sumber = w.sumber;

    INSERT INTO meta (kunci, nilai) VALUES ('warehouse_dimuat', to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
    ON CONFLICT (kunci) DO UPDATE SET nilai = EXCLUDED.nilai;
END;
$$;

-- Trigger tingkat pernyataan: satu kali per pernyataan (impor ribuan baris = satu kali muat), bukan per baris.
-- Tabel transisi memberi tahu komoditas mana yang berubah, sehingga CRUD satu baris hanya menghitung ulang satu komoditas.
CREATE FUNCTION trg_warehouse_tambah() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM muat_warehouse(ARRAY(SELECT DISTINCT komoditas FROM baru));
    RETURN NULL;
END;
$$;

CREATE FUNCTION trg_warehouse_ubah() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM muat_warehouse(ARRAY(SELECT komoditas FROM baru UNION SELECT komoditas FROM lama));
    RETURN NULL;
END;
$$;

CREATE FUNCTION trg_warehouse_hapus() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM muat_warehouse(ARRAY(SELECT DISTINCT komoditas FROM lama));
    RETURN NULL;
END;
$$;

CREATE FUNCTION trg_warehouse_kosongkan() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM muat_warehouse();
    RETURN NULL;
END;
$$;

CREATE TRIGGER harga_ke_warehouse_tambah AFTER INSERT ON harga
    REFERENCING NEW TABLE AS baru FOR EACH STATEMENT EXECUTE FUNCTION trg_warehouse_tambah();
CREATE TRIGGER harga_ke_warehouse_ubah AFTER UPDATE ON harga
    REFERENCING OLD TABLE AS lama NEW TABLE AS baru FOR EACH STATEMENT EXECUTE FUNCTION trg_warehouse_ubah();
CREATE TRIGGER harga_ke_warehouse_hapus AFTER DELETE ON harga
    REFERENCING OLD TABLE AS lama FOR EACH STATEMENT EXECUTE FUNCTION trg_warehouse_hapus();
CREATE TRIGGER harga_ke_warehouse_kosongkan AFTER TRUNCATE ON harga
    FOR EACH STATEMENT EXECUTE FUNCTION trg_warehouse_kosongkan();

CREATE VIEW v_dataset_harga AS
SELECT t.tanggal, t.tahun, t.kuartal, t.bulan, t.nama_bulan, t.nama_hari, t.akhir_pekan, t.hari_besar, t.menjelang_hari_besar,
       w.kota, w.kecamatan, w.nama_pasar, w.tingkat_wilayah,
       k.kode AS komoditas, k.nama AS nama_komoditas, k.kategori, k.kelompok, k.satuan,
       s.kode AS sumber,
       f.harga, f.harga_sebelumnya, f.perubahan_harian_pct, f.harga_7h_lalu, f.perubahan_7h_pct,
       f.rata2_7h, f.rata2_30h, f.median_kota, f.selisih_median_kota_pct, f.jumlah_pasar_melapor, f.interpolasi
FROM fakta_harga f
JOIN dim_waktu     t ON t.kunci_waktu = f.kunci_waktu
JOIN dim_wilayah   w ON w.kunci_wilayah = f.kunci_wilayah
JOIN dim_komoditas k ON k.kunci_komoditas = f.kunci_komoditas
JOIN dim_sumber    s ON s.kunci_sumber = f.kunci_sumber;

-- Muat pertama dari data yang sudah ada.
SELECT isi_dim_waktu('2024-01-01', '2026-12-31');
SELECT muat_warehouse();