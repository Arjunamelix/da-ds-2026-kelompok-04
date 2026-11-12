import test from 'node:test'
import assert from 'node:assert/strict'
import { rupiah, persen, tanggalID, waktuID, waktuSingkat, jamID, keMs, tambahHari, gabungSeri, potongTerakhir, STATUS_IKON } from './format.js'

test('rupiah memakai pemisah titik', () => {
  assert.equal(rupiah(52000).replace(/\s/g, ' '), 'Rp 52.000')
  assert.equal(rupiah(null), '-')
})

test('persen memberi tanda dan koma desimal', () => {
  assert.equal(persen(3.456), '+3,5%')
  assert.equal(persen(-0.04), '-0,0%')
  assert.equal(persen(0), '0,0%')
  assert.equal(persen(2, { tanda: false }), '2,0%')
})

test('tanggalID dan tambahHari bebas zona waktu', () => {
  assert.equal(tanggalID('2026-10-05'), '5 Okt 2026')
  assert.equal(tambahHari('2026-10-21', 7), '2026-10-28')
  assert.equal(tambahHari('2026-12-30', 3), '2027-01-02')
  assert.equal(keMs('2024-01-01'), Date.UTC(2024, 0, 1))
})

test('gabungSeri menyatukan tanggal dan mengurutkan', () => {
  const baris = gabungSeri([
    { titik: [{ tanggal: '2026-01-02', harga: 10 }, { tanggal: '2026-01-01', harga: 9 }] },
    { titik: [{ tanggal: '2026-01-02', harga: 20 }] },
  ])
  assert.equal(baris.length, 2)
  assert.deepEqual(baris[1], { t: keMs('2026-01-02'), s0: 10, s1: 20 })
  assert.equal(baris[0].s1, undefined)
})

test('potongTerakhir relatif ke data terakhir', () => {
  const b = gabungSeri([{ titik: ['2026-01-01', '2026-02-01', '2026-03-01'].map((t, i) => ({ tanggal: t, harga: i })) }])
  assert.equal(potongTerakhir(b, 20).length, 1)
  assert.equal(potongTerakhir(b, 0).length, 3)
})

test('ikon status', () => {
  assert.equal(STATUS_IKON.Lonjakan, '🔴')
})

test('waktuID dan jamID membaca jam apa adanya (WIB dari scraper)', () => {
  assert.equal(waktuID('2026-11-05T14:15:25+07:00'), '5 Nov 2026, 14.15')
  assert.equal(waktuID('2026-11-05'), '5 Nov 2026')
  assert.equal(waktuID(null), '-')
  assert.equal(waktuSingkat('2026-11-05T14:15:25+07:00'), '5 Nov, 14.15')
  assert.equal(jamID('2026-11-05T16:00+07:00'), '16.00')
  assert.equal(jamID(''), '-')
})