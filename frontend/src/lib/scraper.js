// Pembantu tampilan untuk status layanan scraper (GET /api/scraper/status).
// Satu "catatan" = satu tarikan: { mulai, selesai, pemicu, status, baris_baru, sumber: { simpang: {...} } }.

export const LABEL_PEMICU = {
  mulai: 'Saat layanan menyala',
  jadwal: 'Terjadwal',
  manual: 'Manual (tombol)',
  cli: 'Terminal',
}

export const LABEL_STATUS = {
  sukses: { teks: 'Sukses', kelas: 'tag-aqua' },
  sebagian: { teks: 'Sebagian', kelas: 'tag-oranye' },
  galat: { teks: 'Gagal', kelas: 'tag-merah' },
  dilewati: { teks: 'Dilewati', kelas: 'tag-abu' },
}

const daftarSumber = (c) => Object.entries(c?.sumber || {})

// Tanggal data terbaru yang berhasil dibaca pada tarikan ini (hari kerja dengan harga lengkap).
export function dataSampai(c) {
  let akhir = null
  for (const [, s] of daftarSumber(c)) {
    const t = s.tanggal_berdata?.[s.tanggal_berdata.length - 1]
    if (t && (!akhir || t > akhir)) akhir = t
  }
  return akhir
}

// Rentang tanggal yang diminta ke sumber, mis. { dari: '2026-10-27', sampai: '2026-11-05' }.
export function rentangDiambil(c) {
  const a = daftarSumber(c).map(([, s]) => s.ambil).filter(Boolean)
  if (!a.length) return null
  return { dari: a.map((x) => x.dari).sort()[0], sampai: a.map((x) => x.sampai).sort().at(-1) }
}

// Pesan singkat dari sumber yang gagal atau dilewati.
export function pesanSumber(c) {
  return daftarSumber(c)
    .filter(([, s]) => s.status !== 'sukses' && s.pesan)
    .map(([kode, s]) => `${kode}: ${s.pesan}`)
}

// Tanggal yang ditahan karena pasar yang melapor belum cukup (diimpor pada tarikan berikutnya).
export function tanggalDitahan(c) {
  return daftarSumber(c).flatMap(([, s]) => s.ditahan || [])
}