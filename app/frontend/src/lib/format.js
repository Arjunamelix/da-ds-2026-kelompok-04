const rupiahFmt = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 })

export function rupiah(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '-'
  return 'Rp ' + rupiahFmt.format(Math.round(n))
}

export function angka(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '-'
  return rupiahFmt.format(Math.round(n))
}

export function persen(n, { tanda = true, digit = 1 } = {}) {
  if (n === null || n === undefined || Number.isNaN(n)) return '-'
  const s = Math.abs(n).toFixed(digit).replace('.', ',')
  if (!tanda) return s + '%'
  if (n > 0) return '+' + s + '%'
  if (n < 0) return '-' + s + '%'
  return s + '%'
}

const BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

export function tanggalID(iso) {
  if (!iso) return '-'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  if (!y || !m || !d) return iso
  return `${d} ${BULAN[m - 1]} ${y}`
}

// Waktu ISO dengan zona (mis. "2026-11-05T14:15:25+07:00") -> "5 Nov 2026, 14.15".
// Jam dibaca apa adanya dari teks (WIB dari layanan scraper), tidak dikonversi ke zona browser.
export function waktuID(iso) {
  if (!iso) return '-'
  const jam = /T(\d{2}):(\d{2})/.exec(iso)
  return jam ? `${tanggalID(iso)}, ${jam[1]}.${jam[2]}` : tanggalID(iso)
}

// Versi ringkas tanpa tahun untuk chip di header: "5 Nov, 14.15".
export function waktuSingkat(iso) {
  const jam = iso && /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso)
  return jam ? `${Number(jam[3])} ${BULAN[Number(jam[2]) - 1]}, ${jam[4]}.${jam[5]}` : '-'
}

// Jam saja dari waktu ISO: "2026-11-05T16:00+07:00" -> "16.00".
export function jamID(iso) {
  const jam = iso && /T(\d{2}):(\d{2})/.exec(iso)
  return jam ? `${jam[1]}.${jam[2]}` : '-'
}

export function keMs(iso) {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return Date.UTC(y, m - 1, d)
}

export function dariMs(ms) {
  return new Date(ms).toISOString().slice(0, 10)
}

export function tambahHari(iso, n) {
  return dariMs(keMs(iso) + n * 86400000)
}

export function labelTick(ms) {
  const iso = dariMs(ms)
  const [y, m, d] = iso.split('-').map(Number)
  return `${d} ${BULAN[m - 1]} ${String(y).slice(2)}`
}

export const STATUS_IKON = { Normal: '🟢', Waspada: '🟡', Lonjakan: '🔴' }


export function gabungSeri(seri) {
  const peta = new Map()
  seri.forEach((s, i) => {
    for (const p of s.titik) {
      const t = keMs(p.tanggal)
      if (!peta.has(t)) peta.set(t, { t })
      peta.get(t)['s' + i] = p.harga
    }
  })
  return [...peta.values()].sort((a, b) => a.t - b.t)
}

export function potongTerakhir(baris, hari) {
  if (!hari || baris.length === 0) return baris
  const akhir = baris[baris.length - 1].t
  const awal = akhir - hari * 86400000
  return baris.filter((b) => b.t >= awal)
}