-- Deret agregat dihitung dari data asli per pasar, tidak disimpan sebagai baris (tidak ada angka buatan di tabel harga).
-- Setiap tambah/ubah/hapus/impor pada tabel harga otomatis ikut mengubah view ini (sifat dinamis, Project.md 6.3).
--
--   tingkat 'pasar'     : baris asli apa adanya
--   tingkat 'kecamatan' : RATA-RATA harga pasar di kecamatan itu pada hari itu (kecamatan, 'SEMUA')
--   tingkat 'kota'      : MEDIAN harga semua pasar pada hari itu, minimal 3 pasar melapor ('KOTA MEDAN', 'SEMUA')
--
-- Sumber DEV (data sintetis) tidak diagregasi.
CREATE VIEW harga_agregat AS
SELECT tanggal, kecamatan, nama_pasar, komoditas, harga, sumber, satuan, tingkat_wilayah, interpolasi
FROM harga
UNION ALL
SELECT tanggal, kecamatan, 'SEMUA'::text, komoditas, round(avg(harga))::integer, sumber, min(satuan),
       'kecamatan'::text, 0::smallint
FROM harga
WHERE nama_pasar <> 'SEMUA' AND sumber <> 'DEV'
GROUP BY tanggal, kecamatan, komoditas, sumber
UNION ALL
SELECT tanggal, 'KOTA MEDAN'::text, 'SEMUA'::text, komoditas,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY harga))::integer, sumber, min(satuan),
       'kota'::text, 0::smallint
FROM harga
WHERE nama_pasar <> 'SEMUA' AND sumber <> 'DEV'
GROUP BY tanggal, komoditas, sumber

