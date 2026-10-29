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