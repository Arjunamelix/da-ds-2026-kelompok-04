// Utilitas bersama untuk visual analitik (halaman Analisis, Cerita, kartu KPI).

// Palet proyek (Project.md 6.6), divalidasi untuk buta warna. Aqua kontrasnya rendah terhadap latar putih,
// jadi setiap mark beraqua diberi label angka.
export const WARNA = {
  biru: '#2a78d6',
  oranye: '#eb6834',
  aqua: '#1baf7a',
  netral: '#e7e9ee',
  abu: '#9aa3b2',
}

export const fmtRp = (v) => (v == null || Number.isNaN(v) ? '-' : 'Rp ' + Math.round(v).toLocaleString('id-ID'))

export const fmtAngka = (v, digit = 0) =>
  v == null || Number.isNaN(v) ? '-' : Number(v).toLocaleString('id-ID', { minimumFractionDigits: digit, maximumFractionDigits: digit })

export const fmtPct = (v, { tanda = true, digit = 1 } = {}) => {
  if (v == null || Number.isNaN(v)) return '-'
  const r = Math.round(v * 10 ** digit) / 10 ** digit || 0 // hindari "-0,0%"
  return (tanda && r > 0 ? '+' : '') + fmtAngka(r, digit) + '%'
}

// Domain sumbu untuk grafik batang berlabel: beri ruang di kedua ujung agar label angka tidak menabrak sumbu.
export const domainBerlabel = (ruang = 0.3) => [
  (min) => (min < 0 ? min * (1 + ruang) : 0),
  (max) => (max > 0 ? max * (1 + ruang) : 0),
]

const BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

// '2026-03' -> 'Mar 2026'
export const labelBulan = (tb) => {
  if (!tb) return ''
  const [y, m] = tb.split('-')
  return `${BULAN[Number(m) - 1]} ${y}`
}

// '2026-03' -> "Mar '26"
export const labelBulanPendek = (tb) => {
  if (!tb) return ''
  const [y, m] = tb.split('-')
  return `${BULAN[Number(m) - 1]} '${y.slice(2)}`
}

// '2026-10-15' -> '15 Okt 2026'
export const labelTanggal = (s) => {
  if (!s) return ''
  const [y, m, d] = s.slice(0, 10).split('-')
  return `${Number(d)} ${BULAN[Number(m) - 1]} ${y}`
}

export const keMs = (s) => Date.UTC(Number(s.slice(0, 4)), Number(s.slice(5, 7)) - 1, Number(s.slice(8, 10)))
export const dariMs = (ms) => new Date(ms).toISOString().slice(0, 10)

// Rentang tanggal dari pilihan preset, relatif terhadap tanggal data terakhir.
export const RENTANG = [
  { kode: '3b', label: '3 bulan', bulan: 3 },
  { kode: '6b', label: '6 bulan', bulan: 6 },
  { kode: '12b', label: '1 tahun', bulan: 12 },
  { kode: 'semua', label: 'Semua', bulan: 0 },
]

export function hitungRentang(kode, tanggalAkhir) {
  const r = RENTANG.find((x) => x.kode === kode)
  if (!r || !r.bulan || !tanggalAkhir) return { dari: '', sampai: '' }
  const d = new Date(keMs(tanggalAkhir))
  d.setUTCMonth(d.getUTCMonth() - r.bulan)
  d.setUTCDate(1)
  return { dari: dariMs(d.getTime()), sampai: '' }
}

// Awal dan akhir satu bulan: '2026-03' -> {dari:'2026-03-01', sampai:'2026-03-31'}
export function rentangBulan(tb) {
  const [y, m] = tb.split('-').map(Number)
  const akhir = new Date(Date.UTC(y, m, 0))
  return { dari: `${tb}-01`, sampai: dariMs(akhir.getTime()) }
}

// ---------------------------------------------------------------------------
// warna divergen: biru (di bawah) - abu netral - oranye (di atas)
// ---------------------------------------------------------------------------
const hexKeRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16))
const rgbKeHex = (c) => '#' + c.map((x) => Math.round(x).toString(16).padStart(2, '0')).join('')
const campur = (a, b, t) => {
  const A = hexKeRgb(a)
  const B = hexKeRgb(b)
  return rgbKeHex(A.map((x, i) => x + (B[i] - x) * t))
}

// v = nilai bertanda (mis. selisih %), batas = nilai yang dianggap warna penuh.
export function warnaDivergen(v, batas, { positif = WARNA.oranye, negatif = WARNA.biru } = {}) {
  if (v == null || Number.isNaN(v)) return '#f3f4f6'
  const t = Math.max(-1, Math.min(1, v / batas))
  return t >= 0 ? campur(WARNA.netral, positif, t) : campur(WARNA.netral, negatif, -t)
}

// Warna teks yang terbaca di atas latar tertentu.
export function teksDiAtas(hex) {
  const [r, g, b] = hexKeRgb(hex).map((x) => {
    const c = x / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  const L = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return L > 0.36 ? '#1f2937' : '#ffffff'
}

// Komoditas dengan catatan kualitas data (dipakai di judul temuan dan tooltip).
export const CATATAN_DATA = {
  jagung: 'beberapa pasar kemungkinan melaporkan jenis jagung yang berbeda, sehingga selisih antarpasar tampak besar',
  kedelai: 'selisih antarpasar konsisten per pasar (mis. Pasar Sambas sekitar Rp19.000, Pasar Medan Deli sekitar Rp12.000), kemungkinan jenis atau mutu berbeda',
  telur_ayam_ras: 'harga per butir sebelum pertengahan Januari 2025 tidak dipakai',
}
